# Spec — `classificação`

Componente diferenciador. Recebe `itens` do parser e responde *"que categoria é esse produto?"* por uma cascata determinística-primeiro. **API-first** (JSON, não HTML). Faça o mais simples que passe no §6; pare nas fronteiras (§5).

Decisões travadas: seed da taxonomia final (§9 do `docs/historico/report_projeto_nfe.md`); bucket = **"Não Classificado"** (`slug=uncategorized`); mapa NCM→categoria **curado no MVP**; **base (memória+NCM+bucket) é o MVP e funciona sem LLM** — LLM é opt-in atrás de eval.

## 1. Escopo

Classifica cada **produto** (identidade), não cada linha solta — todo item do mesmo produto herda a categoria. Entrega: tabelas de taxonomia + identidade de produto + NCM âncora, a cascata de classificação, edição de taxonomia, e um **harness de eval** do LLM. Sem UI, sem budgets, sem gráficos, sem rede além do Ollama configurável.

## 2. Modelo de dados (DDL — idempotente)

`ALTER TABLE` roda uma vez na migração (não é idempotente em SQLite; controlar por versão de schema).

```sql
-- Taxonomia: 2 níveis via parent_id (NULL = categoria nível 1)
CREATE TABLE IF NOT EXISTS categorias (
  id INTEGER PRIMARY KEY,
  slug TEXT NOT NULL UNIQUE,                 -- estável; 'uncategorized' = bucket
  nome TEXT NOT NULL,
  parent_id INTEGER REFERENCES categorias(id),
  is_bucket INTEGER NOT NULL DEFAULT 0
);

-- Mapa curado NCM→categoria (piso determinístico, sem LLM)
CREATE TABLE IF NOT EXISTS ncm_ancora (
  prefixo TEXT PRIMARY KEY,                  -- 2, 4 ou 8 dígitos
  categoria_id INTEGER NOT NULL REFERENCES categorias(id)
);

-- Identidade de produto: por GTIN (global) OU (descrição normalizada + CNPJ da loja)
CREATE TABLE IF NOT EXISTS produtos (
  id INTEGER PRIMARY KEY,
  identidade_origem TEXT NOT NULL CHECK (identidade_origem IN ('gtin','texto')),
  gtin TEXT,
  descricao_normalizada TEXT, emit_cnpj TEXT,
  descricao_exemplo TEXT,                    -- um xProd cru observado, p/ UI
  categoria_id INTEGER REFERENCES categorias(id),   -- NULL até classificar
  origem TEXT CHECK (origem IN ('manual','memoria','ncm','llm')),
  confianca REAL,                            -- 0..1 quando origem='llm'
  criado_em TEXT NOT NULL, atualizado_em TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_produtos_gtin
  ON produtos(gtin) WHERE gtin IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS ux_produtos_texto
  ON produtos(descricao_normalizada, emit_cnpj) WHERE gtin IS NULL;

CREATE TABLE IF NOT EXISTS tags (id INTEGER PRIMARY KEY, nome TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS produto_tags (
  produto_id INTEGER NOT NULL REFERENCES produtos(id),
  tag_id INTEGER NOT NULL REFERENCES tags(id),
  PRIMARY KEY (produto_id, tag_id)
);

-- Liga cada item do parser ao seu produto (migração aditiva)
ALTER TABLE itens ADD COLUMN produto_id INTEGER REFERENCES produtos(id);
CREATE INDEX IF NOT EXISTS idx_itens_produto ON itens(produto_id);
```

Seed carregado por script de migração: `categorias` (taxonomia §9 + bucket) e `ncm_ancora` (mapa curado). `categoria_id` referencia qualquer nível da árvore — cada linha de `ncm_ancora` aponta pro **nível mais específico que o prefixo justifica** (subcategoria quando o NCM é específico — ex.: 0403 → Mercado›Laticínios; nível 1 quando o código é genérico). LLM/humano refina só o que o NCM não alcança.

## 3. Identidade de produto

Resolver o produto de cada item, nesta ordem:
- **GTIN presente** → identidade `gtin` (confiável, cross-loja). Casa/cria `produtos` por GTIN.
- **Sem GTIN** → identidade `texto`: `descricao_normalizada` (minúsculas, sem acento, pontuação fora, espaços colapsados; **não** mexe em números/unidades no MVP) **+ documento da loja** — o CNPJ, ou o CPF quando o emitente é pessoa física (spec 01 §2). Casa/cria por esse par.
- **Honestidade:** casar o mesmo produto **entre lojas diferentes** só é confiável por GTIN. Sem GTIN, é *best-effort* dentro da loja — `identidade_origem='texto'` sinaliza isso pros componentes consumidores (ex.: preço no tempo cross-loja é aproximado).

## 4. Cascata de classificação (prioridade)

Para cada produto ainda não resolvido:
1. **Memória por produto** — se o produto já tem categoria com `origem in (manual,memoria)`, **mantém** (nunca sobrescreve decisão humana).
2. **NCM âncora** — casa o `ncm` do item pelo **prefixo mais longo** em `ncm_ancora` → categoria no nível que o prefixo alcança (subcategoria se específico, ex. 0403→Laticínios; senão nível 1). `origem='ncm'`.
3. **LLM (opt-in)** — só pro que sobrou. Saída **restrita** à lista de categorias fornecida + `nao_sei`; resposta fora da lista, `nao_sei` ou confiança < limiar → bucket. `origem='llm'`, grava `confianca`.
4. **Bucket** — resto → `categoria_id` do `uncategorized`, `origem=NULL`.

- **Realimentação:** humano classifica um produto → `origem='manual'`; reaplica automático aos próximos itens do mesmo produto (resolvem pro mesmo `produtos`).
- **Produto do LLM é revisitado** (decisão do Gui de 2026-10-16): a varredura confere o NCM dos produtos `origem='llm'`; se uma âncora passou a cobri-lo (uma versão nova do seed), **o NCM vence** — `origem='ncm'`, sem confiança —, como se o produto chegasse hoje. ⛔ O LLM não é chamado de novo para eles.
- **Devolver à fila** (decisão do Gui de 2026-10-16): humano classifica no **bucket** → `origem='manual'` no bucket. O degrau 1 protege a decisão, então nem o NCM nem o LLM mexem mais nele; a fila de revisão o mostra até o humano escolher uma categoria. ⛔ Não é `origem` NULL: com NULL, a próxima varredura poria o produto de volta na categoria que o humano rejeitou.
- **LLM config:** só Ollama; `OLLAMA_URL` e modelo por **env var desde o dia 1**; limiar de confiança configurável. Base roda sem nada disso.
- **Edição de taxonomia:** apagar categoria com histórico → produtos vão pro bucket; renomear → mantém vínculos (id estável); mover subcategoria → vínculos seguem (reatribui); **criar** categoria nível 1 ou subcategoria (decisão do Gui de 2026-10-15).
- **A árvore tem no máximo 2 níveis.** Criar ou mover que produza um terceiro nível é recusado: o pai tem de ser nível 1, e categoria com subcategorias não vira subcategoria. O bucket nunca é pai. Terceiro nível = roadmap.

## 5. Fronteiras (não fazer aqui)

Parsing/ingestão (é do parser) · budgets · gráficos/visualização · UI/HTTP · download SEFAZ · **regras por padrão (regex xProd)** e **tags automáticas por LLM** (roadmap — tags são manuais no MVP).

## 6. Pronto = suíte verde no CI

Fixtures anonimizadas (sem CPF/CNPJ/nome real).

Invariantes:
- **Cascata respeitada:** memória > NCM > LLM > bucket; `manual` nunca é sobrescrito por LLM/NCM.
- **NCM âncora:** item com NCM do mapa → categoria certa **sem LLM**.
- **Identidade:** mesmo GTIN em lojas diferentes → um produto; sem GTIN, mesmo `norm+CNPJ` → um produto e CNPJ diferente → produtos distintos (marcado best-effort).
- **LLM:** com LLM off a base classifica sem erro; com on, saída fora da lista / `nao_sei` / baixa confiança → bucket (nunca inventa categoria).
- **Taxonomia:** apagar → bucket; renomear → vínculos intactos; mover → vínculos seguem.
- **Criar categoria:** `criar_categoria(conexao, nome, parent_slug=None)` devolve o slug. O slug nasce do nome (minúsculas, sem acento, não-alfanumérico vira `-`), prefixado pelo slug do pai — `Molhos` em `mercado` vira `mercado-molhos`. Depois de criado, o slug é dado: renomear não o muda. Recusa (`ValueError`): nome vazio ou sem nenhuma letra/dígito, slug que já existe, pai que é subcategoria, pai que é o bucket. Pai inexistente → `LookupError`.
- **Dois níveis no mover:** `mover_categoria` recusa (`ValueError`) pai que é subcategoria, e mover para dentro de outra uma categoria que tem subcategorias.
- **Eval harness** roda sobre um conjunto rotulado (gold humano) e emite acurácia por categoria, matriz de confusão e % que caiu no bucket — é o que decide se o LLM é ligado. Bar de aprovação: chamada do Gui após ver os números.
- Saídas serializam em JSON; nenhum dado pessoal real nas fixtures.

## 7. Decisões tomadas na implementação — ⚠️ RASCUNHO, a revisar

> **Rascunho de 2026-10-14, ainda NÃO aprovado.** Consolida o que as stories 007–013, e a
> refatoração de 2026-10-14, decidiram ao construir este componente — decisões que até aqui só
> existiam nas specs das stories e no código. Ao aprovar, esta seção vira contrato (e o texto das
> §1–§6 é ajustado onde a §7.1 aponta); as stories voltam a ser só registro.

### 7.1 Onde o texto acima diverge do que foi construído

| As §1–§6 dizem | O código faz | Proposta |
| -------------- | ------------ | -------- |
| §2: "Seed carregado por script de migração" | o seed ⛔ **não** é migração: é um carregador idempotente (`seed.carregar_seed_padrao`), que pode rodar quantas vezes for preciso, a partir de `src/nfe_parser/dados/taxonomia_seed.json` (story 010 D6). Migração roda uma vez só — e o mapa NCM só resgata o bucket se puder ser recarregado | trocar o texto |
| §2: o DDL | falta a tabela `categorias_apagadas (slug TEXT PRIMARY KEY, apagada_em TEXT NOT NULL)` — a "lápide" (migração v3, story 011) | acrescentar ao DDL |
| §2: "controlar por versão de schema" | `PRAGMA user_version`; hoje v3 (v1 = tabelas desta spec, v2 = `itens.produto_id`, v3 = lápide) | registrar |
| §4: "Para cada produto ainda não resolvido" | "não resolvido" = `origem IS NULL`, o que **inclui** quem está no bucket. Quem percorre é `classificar_produtos_pendentes`, separado da importação (story 013 D1/D5) | registrar |
| §4: "Realimentação: reaplica automático aos próximos itens" | não há cópia: todo item do mesmo produto aponta para a mesma linha de `produtos`, que já tem a categoria. `origem='memoria'` é respeitado, mas nunca escrito (story 009 D4) | registrar |
| §4 e specs 03/06: variáveis de ambiente do LLM | divergiam entre si — ver §7.3, item 1 | ✅ decidido: vale o código |

### 7.2 Regras decididas

**Taxonomia e seed** (stories 010 e 011)
- O `slug` é DADO, não derivado do nome. Por convenção do arquivo de dados, o slug do filho começa
  pelo do pai (`mercado-frutas`; `eletronicos-eletronicos` quando o nome se repete nos dois níveis).
- **O seed é uma base default, não o dono da tabela** (decisão do Gui de 15/09, abertura da 011):
  insere o que falta e ⛔ nunca altera nem apaga o que já existe. Corrigir um nome no arquivo não
  afeta banco que já rodou o seed — a correção é por `renomear_categoria`.
- Prefixo NCM só com 2, 4 ou 8 dígitos — os que a busca consulta. Outro tamanho é recusado na carga.
- Exatamente **um** bucket no banco, conferido depois de cada carga.

**Edição de taxonomia** (story 011) — sempre por `slug`, nunca por `id`
- **Renomear** muda só o `nome`; ⛔ nunca o `slug`. Nome vazio é recusado.
- **Apagar** é definitivo: a lápide impede o seed de trazer a categoria de volta. É recusado para o
  bucket e para categoria com subcategorias. Os produtos vão ao bucket com `origem` NULL —
  ⚠️ **inclusive os `manual`**, cuja decisão apontava para uma categoria que não existe mais — e sem
  `confianca`. As âncoras NCM da categoria são apagadas, não reapontadas.
- **Mover** recusa ciclo na árvore; mover para `None` sobe a categoria para o nível 1.
- **Criar** categoria: ver §4 e §6 (decidido em 2026-10-15; antes estava fora do escopo).

**Cascata** (stories 009 e 013)
- Item sem NCM vai para o bucket; não é erro.
- O NCM de um produto é o do seu item **mais recente**.
- Banco sem bucket só dá erro quando o bucket é de fato necessário.
- **A importação resolve a identidade do produto, mas ⛔ não classifica.** Classificar é passo
  separado (`classificar_produtos_pendentes`): banco sem seed tem de continuar importando.
- Categoria, origem e confiança são gravadas **juntas**; `confianca` só existe com `origem='llm'`
  (refatoração de 2026-10-14).

**Identidade de produto** (story 008)
- `descricao_normalizada` guarda só `a-z`, `0-9` e espaço; pontuação vira espaço; números e
  unidades atravessam sem interpretação (`1,5L` e `1.5 L` → `1 5l`). `ø`, `º`, `µ` viram espaço.
- GTIN vazio, ou texto sem documento da loja (nem CNPJ nem CPF), é erro — ⛔ nunca um produto fantasma com chave NULL.

**LLM** (story 012)
- Opt-in por parâmetro: sem um `llm`, a cascata é memória → NCM → bucket.
- Contrato: `llm(descricao, slugs) -> (slug, confianca) | None`. O LLM vê só a
  `descricao_exemplo` — nem NCM, nem emitente.
- A lista enviada são as categorias que existem, ⛔ sem o bucket, em ordem de slug.
- Resposta aceita só se: for objeto JSON, a categoria estiver na lista, a confiança for número
  (⛔ não booleano) entre 0 e 1 e **≥ limiar** (igual ao limiar é aceito). O slug é conferido no
  banco antes de gravar, e o LLM não pode escolher o bucket.
- Nenhum valor padrão para modelo nem limiar. Temperatura 0. Erro de rede sobe.
- `LLM_LIMIAR` tem de ser número entre 0 e 1 (inclusive); outro valor derruba a subida do app (§7.3 item 4).

**Eval** (story 012)
- Gold: CSV `descricao;esperado`, UTF-8 (BOM do Excel aceito). `esperado` vazio = "a taxonomia não
  tem lugar para isto": fica fora da acurácia e é contado à parte. Acerto é exato. O gold real ⛔
  não entra no repo.

**Saída JSON** (story 013, junto com a spec 01 §6)
- Cada item sai com `categoria_slug` (para agrupar e fazer conta) e `categoria` (o nome, para ler).
  Item no bucket sai com o nome do bucket; item sem produto ou sem categoria sai com `None` nas duas.
  ⛔ `origem` e `confianca` não saem.

### 7.3 Decisões pendentes — do Gui

1. ✅ **DECIDIDO (Gui, 2026-10-15): vale o código.** `OLLAMA_URL` presente liga o LLM, ausente o
   desliga; com ela, `OLLAMA_MODELO` e `LLM_LIMIAR` são obrigatórios, sem valor padrão. As specs
   03 e 06 e o `.env.example` foram alinhados a isso.
2. ✅ **DECIDIDO (Gui, 2026-10-16): o NCM vence.** Produto com `origem='llm'` não era revisitado:
   se uma âncora NCM chegasse depois, ele ficava com a resposta do LLM, embora o §4 ponha NCM acima
   do LLM. Agora a varredura o revisita (§4, "Produto do LLM é revisitado").
3. ✅ **DECIDIDO (Gui, 2026-10-15): criar categoria SIM, até 2 níveis; terceiro nível = roadmap.**
   Ver §4 e §6. (O gold de 19 produtos tinha mostrado 7 rótulos num terceiro nível — Sabonete,
   Iogurte, Frango… — e categorias ausentes, como molho.)
4. ✅ **DECIDIDO (Claude, 2026-10-16, por convenção — o Gui pode vetar em `docs/decisoes.md`):
   recusar.** Um limiar `2` deixava o LLM ligado sem nunca classificar nada, sem erro. Agora
   `LLM_LIMIAR` que não é número entre 0 e 1 derruba a subida do app com a mensagem, como as
   outras variáveis obrigatórias.

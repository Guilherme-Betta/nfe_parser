# Spec — `classificação`

Componente diferenciador. Recebe `itens` do parser e responde *"que categoria é esse produto?"* por uma cascata determinística-primeiro. **API-first** (JSON, não HTML). Faça o mais simples que passe no §6; pare nas fronteiras (§5).

Decisões travadas: seed da taxonomia final (§9 do report); bucket = **"Não Classificado"** (`slug=uncategorized`); mapa NCM→categoria **curado no MVP**; **base (memória+NCM+bucket) é o MVP e funciona sem LLM** — LLM é opt-in atrás de eval.

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
- **Sem GTIN** → identidade `texto`: `descricao_normalizada` (minúsculas, sem acento, pontuação fora, espaços colapsados; **não** mexe em números/unidades no MVP) **+ CNPJ da loja**. Casa/cria por esse par.
- **Honestidade:** casar o mesmo produto **entre lojas diferentes** só é confiável por GTIN. Sem GTIN, é *best-effort* dentro da loja — `identidade_origem='texto'` sinaliza isso pros componentes consumidores (ex.: preço no tempo cross-loja é aproximado).

## 4. Cascata de classificação (prioridade)

Para cada produto ainda não resolvido:
1. **Memória por produto** — se o produto já tem categoria com `origem in (manual,memoria)`, **mantém** (nunca sobrescreve decisão humana).
2. **NCM âncora** — casa o `ncm` do item pelo **prefixo mais longo** em `ncm_ancora` → categoria no nível que o prefixo alcança (subcategoria se específico, ex. 0403→Laticínios; senão nível 1). `origem='ncm'`.
3. **LLM (opt-in)** — só pro que sobrou. Saída **restrita** à lista de categorias fornecida + `nao_sei`; resposta fora da lista, `nao_sei` ou confiança < limiar → bucket. `origem='llm'`, grava `confianca`.
4. **Bucket** — resto → `categoria_id` do `uncategorized`, `origem=NULL`.

- **Realimentação:** humano classifica um produto → `origem='manual'`; reaplica automático aos próximos itens do mesmo produto (resolvem pro mesmo `produtos`).
- **LLM config:** só Ollama; `OLLAMA_URL` e modelo por **env var desde o dia 1**; limiar de confiança configurável. Base roda sem nada disso.
- **Edição de taxonomia:** apagar categoria com histórico → produtos vão pro bucket; renomear → mantém vínculos (id estável); mover subcategoria → vínculos seguem (reatribui).

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
- **Eval harness** roda sobre um conjunto rotulado (gold humano) e emite acurácia por categoria, matriz de confusão e % que caiu no bucket — é o que decide se o LLM é ligado. Bar de aprovação: chamada do Gui após ver os números.
- Saídas serializam em JSON; nenhum dado pessoal real nas fixtures.

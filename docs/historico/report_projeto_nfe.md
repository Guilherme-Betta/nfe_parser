# Report — Projeto NF-e Despesas (decisões de design)

> 📜 **Foto histórica de 2026-08-29 — não é mais atualizada.** É o report de design original,
> anterior às specs. Fica no repo porque as specs 01–06 citam suas seções (ex.: "§9 do report").
> ⚠️ O [`report_nfe_central.md`](report_nfe_central.md), ao lado, **renumerou as seções**: um "§N"
> numa spec 01–06 se refere a **este** arquivo, não àquele.
> Decisões marcadas aqui como abertas foram fechadas depois; o estado atual está nas specs
> (`specs/`) e no `git log`. Sem edições de conteúdo desde a data acima.

> Documento de **decisões de design** — base para o spec que será escrito depois.
> Ainda NÃO é o spec por componente (isso vem após ler a doc de prompting do Fable 5).
> Última atualização: **2026-08-29 (rev. 1 — decisões consolidadas)**
> ⚠️ Repo será **público**. Nada de dado pessoal (CPF, nome, CNPJ, paths, IPs) no código ou em fixtures.

---

## 0. Do que se trata

Ferramenta para **visualizar despesas a partir de notas fiscais eletrônicas** (XML), com
categorização automática (regras + NCM + LLM opcional) e orçamento inspirado no Cashew.
Nasce como projeto **público no GitHub** (útil pra outras pessoas), mas o **MVP é validado
no uso pessoal do Gui** primeiro; expansão vem depois.

**Motivação:** o portal/app da Nota Fiscal Paulista é ruim; o fluxo atual (app
NFe-visualizador → export zip de XMLs → olhar manualmente) é trabalhoso e não dá visão
de gasto. O diferencial do projeto é a **granularidade de item** (produto a produto), que
a NF-e carrega e nenhuma ferramenta pronta explora bem.

---

## 1. Alvo, licença e princípios

- **Alvo:** repositório **público**. MVP mira o **usuário técnico que self-hosta** (mais
  fácil de entregar já). Pessoa comum como alvo fica no **roadmap**.
- **Single-user** no MVP. Multiusuário / contas familiares no **roadmap**.
- **Licença:** indiferente. Se copiar código do **Cashew** (GPL-3.0) for vantajoso, tudo
  bem herdar GPL-3.0. Decisão de licença final fica pro momento de criar o repo.
- **Idioma:** UI e docs em **PT-BR** no MVP. **EN no roadmap** (amplia contribuições).
- **Princípio de honestidade do projeto:** onde a confiabilidade é "best-effort" (ex.:
  casar produto entre lojas por texto), o app **mostra isso**, não finge precisão.

---

## 2. Escopo — o que é e o que NÃO é

### É (MVP)
- **Movido por nota fiscal** — os gastos vêm dos XMLs, sem entrada manual.
- **Modelos suportados: NF-e (55) + NFC-e (65).** Compartilham o mesmo schema — custo
  marginal quase zero, e o dia-a-dia (mercado/farmácia) costuma ser **65**, não 55.
- **CF-e/SAT:** schema diferente → o app **marca como "não suportado ainda"** (não quebra;
  sinaliza). Suporte a SAT fica no roadmap.
- **Só despesas** (saídas). **Só BRL.**

### NÃO é (fora do MVP — roadmap)
- Entrada manual de gastos / app de finanças abrangente (aluguel, serviços sem NF-e).
- Receitas.
- Download automático de XML do SEFAZ / login / certificado digital.
- **Scan de QR code pelo próprio app** (ver §3, decisão consciente).
- Multiusuário, EN, outras moedas, comparativo planejado × real.

---

## 3. Ingestão de dados

- **Entrada do MVP:** **upload de zip pela UI** (o zip que o Gui já exporta do
  NFe-visualizador), processando **o lote inteiro de uma vez**. Também aceitar XML avulso.
- **Dedup idempotente pela chave de acesso** (44 dígitos, única por nota): se o mesmo XML
  entrar 2× (zips de meses sobrepostos), o app reconhece a chave e **não duplica o gasto**.
- **Marcação de status por nota:**
  - **Duplicada** (mesma chave) → marcada, não recontabilizada.
  - **Inválida** (não parseia) → marcada.
  - **Cancelada** → marcada **só se o XML de evento de cancelamento vier no zip**; sem ele,
    não há como saber sem consultar o SEFAZ (fora de escopo). Expectativa honesta.
- **QR scan (fora do MVP, decisão consciente):** o QR da nota entrega só a **chave + URL do
  portal**, não o XML; baixar o XML dali recai no problema de login/certificado já
  descartado, e "escanear" é atividade de câmera/celular — não combina com web app em
  Docker. O **NFe-visualizador já faz essa parte**; o app ingere o resultado. QR scan fica
  no roadmap.

### ⚠️ Problema de captura na FONTE (anterior ao app — investigação separada)
As compras de **supermercado/farmácia** do Gui **não estão vindo no XML** (o "XML vazio"
observado). Causa mais provável: essas compras são **NFC-e (65) / CF-e-SAT**, e o
NFe-visualizador pode estar exportando esses tipos **vazios / só em PDF / não capturando**.
**Isto é um problema da fonte de captura, não do nosso app** — o app não resolve enquanto
o XML completo não chegar. Tratar como **frente separada** (investigar o que o
NFe-visualizador exporta pra uma nota de supermercado, e se a Nota Fiscal Paulista
disponibiliza o XML por outro caminho). O app já nasce lendo 55+65 pra engolir tudo assim
que a captura funcionar.

---

## 4. Parser → modelo de dados

- **Parsing em Python** (libs maduras: `nfelib` / `nfetoolkit`) — schema-aware, lida melhor
  com os namespaces e campos opcionais da NF-e do que um parser XML genérico.
- **Grão duplo** (o valor está no item):
  - `notas` (cabeçalho): chave, data/hora, loja (nome + CNPJ), município/UF, total,
    forma de pagamento, modelo (55/65), status (ok/duplicada/inválida/cancelada).
  - `itens` (uma linha por produto): descrição (`xProd`), **NCM**, quantidade, unidade,
    valor unitário, valor da linha, GTIN quando houver, + FK pra `notas`.
- **Storage: SQLite** (1 arquivo, backup trivial, roda em qualquer host). Postgres só se um
  dia precisar de concorrência real (roadmap).
- **Validado contra XML real (2026-08-29):** `nfeProc → NFe`, modelo 55, com `det` trazendo
  `xProd` + `NCM` + quantidade + valor. Pressuposto de extração **confirmado**. Ressalva: só
  vimos notas de **1 item**; multi-item (mercado) usa o mesmo schema (`det` repete), mas
  ainda não foi validado com uma nota real dessas.

---

## 5. Classificação (o núcleo diferenciador)

### Taxonomia
- **Seed + crescível:** começa com uma lista inicial (§9) e o usuário **gerencia pela UI**
  (criar/renomear/mover/apagar categoria e subcategoria) — isso é **feature do MVP**.
- **2 níveis** (categoria › subcategoria) + **tags livres** (várias por item, ortogonais à
  árvore: ex. categoria "Iogurte" + tags "desnatado", "orgânico"). Profundidade > 2 níveis
  fica no roadmap (árvore funda vira inferno de UI).
- **LLM pode propor categoria nova**, mas **sob revisão** do usuário (não cria sozinho).

### Cascata de classificação (ordem de prioridade)
1. **Memória por produto** — humano classificou aquele produto → vínculo produto→categoria,
   reaplicado sempre que o **mesmo produto** reaparecer. Preciso, nunca erra; só cobre o
   que já foi visto.
2. **NCM âncora** — tabela fixa NCM→categoria dá uma **categoria-base garantida sem LLM**
   (ex.: NCM 0901 = Café). O piso determinístico.
3. **LLM** (opcional) — só pro que sobrou; refina dentro da âncora do NCM.
4. **Bucket "Não classificado"** — o resto, pra revisão manual.
- **Regras por padrão** (ex.: "`xProd` contendo 'iogurte' → Iogurte") ficam no **roadmap** —
  são poderosas mas erram por falso-positivo ("sorvete sabor iogurte"), então exigem
  cuidado que não vale gastar no MVP.
- **Baixa confiança do LLM** → vai pro bucket "Não classificado".

### Realimentação
- **Modelo do MVP: memória por produto.** Classificação humana vira vínculo persistente do
  produto e é reaplicada automaticamente aos próximos iguais.

### Identidade do produto (o que é "o mesmo produto")
- **GTIN (código de barras) quando existir** — identificador global, confiável.
- **Senão:** `xProd` **normalizado** + **CNPJ da loja**.
- **Consequência honesta:** casar produto é confiável **por GTIN** e **dentro da mesma
  loja**; **entre lojas diferentes por texto é best-effort**. O gráfico de **preço no
  tempo** funciona muito bem com GTIN e dentro da loja; cross-loja por nome é aproximado —
  e o app sinaliza isso.

### LLM
- **Opcional.** A base (regras + NCM) funciona **sem LLM** — importante porque a maioria do
  público não tem GPU/Ollama.
- **Backend:** só **Ollama** no MVP. **URL configurável por variável de ambiente desde o dia
  1** (senão a imagem pública fica presa no host do Gui). Backend configurável / endpoints
  OpenAI-compatible no roadmap.
- **Qualidade incerta** — classificação PT-BR de produto em modelo local (teto 12 GB VRAM no
  `juicey`) **precisa de eval num lote** antes de se confiar. Não presumir que funciona.

---

## 6. Orçamento (features estilo Cashew)

- **MVP:** budget **por categoria**, período **mensal**.
- **Roadmap:** budget por subcategoria; metas; recorrência; contas/carteiras; comparativo
  planejado × real.
- **Só despesas**, **só BRL** (ver §2).

---

## 7. Visualização

- **Usuário monta as próprias visões** (estilo Cashew): escolhe categorias, meses, lojas,
  produtos que quer ver — não um dashboard fixo.
- **Visões do MVP:** gasto por mês · por categoria · por loja · top produtos · **evolução de
  preço de um produto no tempo** (diferencial forte — a NF-e traz preço unitário histórico;
  funciona melhor com GTIN / dentro da loja, ver §5).
- **Comparativo planejado × real:** roadmap.
- Gráfico interativo e bonito **já dá na fase Python** (ex.: bibliotecas que renderizam no
  navegador). Não precisa esperar o React.

---

## 8. Arquitetura, stack e deploy

### Stack — "pedras grandes" fixadas, resto delegado ao Fable
- Linguagem: **Python** (o parser obriga; evita dois runtimes).
- **Framework web** (a escolher/fixar), **SQLite**, **Docker** — fixados.
- Bibliotecas menores: **o Fable escolhe** dentro dessas restrições.

### API-first (requisito-âncora)
- **A lógica (parsing, classificação, budgets, queries) vive num núcleo que fala JSON, não
  HTML.** A UI é **cliente** desse núcleo.
- **MVP:** backend Python servindo **API** + **UI Python simples** (server-rendered) por
  cima.
- **Evolução barata pra front JS/React** (gráficos "de produto", mais fluidez): troca-se só
  a camada de cima; o núcleo não se mexe. **Armadilha a evitar:** frameworks que **grudam**
  lógica e UI no mesmo código (migração viraria reescrita).

### Deploy
- **Web app self-hosted em Docker.**
- **Publicar `docker-compose` + imagem oficial** (essencial pro público).
- **Instância do Gui roda no `juicey`.** Como a classificação usa o Ollama do `juicey`
  (`localhost:11434` no host), o app em Docker alcança via `host.docker.internal:11434`
  (Windows). URL por env var (§5).

---

## 9. Taxonomia inicial (SEED — o Gui edita)

Ponto de partida, 2 níveis. **Editável agora** (é só pedir mudanças) **e depois na UI**.
Regra definida: **apagar/mover categoria que já tem despesas → despesas vão pro bucket
"Não classificado".**

- **Mercado**:
  - Frutas
  - Verduras
  - Legumes 
  - Carnes e peixes
  - Laticínios
  - Padaria 
  - Mercearia (secos/enlatados) 
  - Congelados 
- **Bebidas**:
  - Cerveja
  - Vinho
  - Destilados 
  - Café
  - Chá
- **Limpeza**:
  - Faxina
  - Lavanderia
  - Louça
- **Cuidado pessoal**:
  - Cabelo
  - Pele
- **Saúde**:
  - Higiene
  - Medicamentos
  - Farmácia (não-medicamento)
  - Suplementos
- **Restaurante e delivery**:
  - Restaurante
  - Delivery
  - Lanche
  - Cafeteria
- **Eletrônicos**: 
  - Eletrônicos
  - Acessórios
- **Vestuário**
- **Automóvel**:
  - Borracharia
  - Combustível
  - Mecânico
- **Outros**:
  - Petshop

Notas:
- **Bucket especial:** rótulo visível **"Não classificado"**, id interno `uncategorized`.
- **Café** entrou como subcategoria (caso real, NCM 0901); se for consumo grande, promover a
  categoria. Chamada do Gui.

---

## 10. Qualidade (é público)

- **Testes desde o início com fixtures anonimizadas** de vários tipos de nota (55, 65,
  cancelada, sem GTIN, multi-item…). Resolve testes **e** privacidade de uma vez.
- **Anonimização:** precisa de um passo/utilitário que gere fixtures a partir de notas reais
  trocando CPF/nome/CNPJ por fake. Faz parte do trabalho.
- **CI (GitHub Actions):** roda testes/lint a cada push, pega quebra sozinho. Padrão em repo
  público, sinaliza qualidade, baixo esforço. **Sim.**
- **Aceitar contribuições:** sim (CONTRIBUTING, issues abertas).

---

## 11. Decisões em aberto / mini-decisões pro spec

- [ ] **Rótulo do bucket:** "Não classificado" (recomendado) vs. "Uncategorized" visível.
  - Decisão: "Não Classificado"
- [ ] **Framework web Python** específico (a fixar quando escrever o spec).

- [ ] **Multi-item real:** validar o parser com uma nota de mercado (muitos itens) quando
      houver uma.
- [ ] **Comportamento ao renomear/mover categoria com histórico** além do delete (já
      resolvido: delete → "Não classificado"). Renome mantém vínculos; mover reatribui.
- [ ] **Seed final:** o Gui vai enviar edições (tirar/renomear/adicionar)
  - Nova versão proposta.

## 12. Unknowns (honestos — não sabemos ainda)

- O que a coleção do Gui realmente contém por modelo (55/65/SAT) — depende de investigar a
  captura na fonte (§3).
- Causa exata do "XML vazio" das compras de supermercado (frente separada).
- Qualidade real da classificação por LLM local em PT-BR no teto de 12 GB VRAM (precisa
  eval).
- Comportamento do NFe-visualizador ao exportar 65/SAT.

## 13. Roadmap (consolidado — fora do MVP)

Entrada manual + app de finanças abrangente · receitas · multiusuário / contas familiares ·
EN · QR scan no app · download automático via SEFAZ · CF-e/SAT · regras por padrão na
classificação · backend LLM configurável (OpenAI-compatible) · budget por subcategoria /
metas / recorrência / carteiras · comparativo planejado × real · front JS/React · Postgres.

---

## 14. Próximos passos

1. Gui edita a **seed** (§9) e bate o martelo no **rótulo do bucket** (§11).
2. Claude lê a **doc de prompting do Fable 5**
   (`https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5`).
3. Claude transforma este documento em **spec por componente** (ingestão, parser/modelo,
   classificação, orçamento, visualização, deploy) pronto pro Claude Code / Fable 5.
4. Frente **separada**: investigar a captura de 65/SAT na fonte (NFe-visualizador / NF
   Paulista).

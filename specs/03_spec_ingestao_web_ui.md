# Spec — `ingestão-web / UI`

Camada web do app NF-e: **shell da aplicação** + **pipeline de importação** + **UI server-rendered**. Amarra `parser` e `classificação` num app HTTP. Lê `report_projeto_nfe.md` como contexto; esta spec é o contrato deste componente. **API-first**: a lógica já existe nos núcleos JSON — aqui a UI é **cliente** do próprio JSON, não dona de lógica. Faça o mais simples que passe no §7; pare nas fronteiras (§6).

Decisões travadas: **framework = FastAPI + Jinja2/HTMX** (§8 do report — núcleo JSON com FastAPI, UI fina server-rendered por cima; troca por React depois mexe só na camada de cima). Este componente é **dono da migração versionada e do seed**, da **config por env var**, e da **orquestração parser→classificação**. Ingestão do MVP = **upload de zip (lote inteiro) ou XML avulso pela UI**.

## 1. Escopo

Sobe o app FastAPI, aplica schema+seed, recebe upload, roda o lote (parser → classificação base) e serve leitura/revisão pela API e por páginas server-rendered. Entrega: shell + migração, pipeline de importação, a **API JSON** (§4) e a **UI** (§5), incluindo **revisão de não-classificados** e **gestão de taxonomia** (features de UI do MVP, §5 do report). Sem budgets, sem gráficos, sem Docker.

## 2. App shell

- **FastAPI** servindo a API (§4); **Jinja2 + HTMX** para as páginas (§5) — HTMX faz POST/atualização parcial batendo na mesma API. Sem build de front, sem SPA.
- **Config só por env var** (imagem pública não pode grudar no host do Gui): `APP_DB_PATH` (SQLite), `LLM_ATIVO` (default **off**), `OLLAMA_URL`, `OLLAMA_MODEL`, `LLM_LIMIAR_CONFIANCA`. Ler no boot; expor estado em `/api/health`.
- **Migração versionada e idempotente** no startup: aplica DDL do `parser` (`importacoes/notas/itens/importacao_arquivos`) + da `classificação` (`categorias/ncm_ancora/produtos/tags/produto_tags` + `ALTER itens ADD produto_id`) + **seeds** (taxonomia §9, `ncm_ancora`). Controlar por **`schema_version`** (o `ALTER` não é idempotente em SQLite — roda uma vez por versão). Rodar 2× deixa o banco idêntico.

## 3. Pipeline de importação (orquestração)

`POST /api/importacoes` recebe o arquivo e, **síncrono no MVP**:
1. `.zip` → itera os XMLs; `.xml` → um só. Chama o **parser** (persiste `notas/itens`, dedup por chave, **cancelamento em duas passadas**, SAT/corrompido → `importacao_arquivos`). Nenhum arquivo derruba o lote.
2. Depois do parser, chama a **classificação base** (identidade de produto + cascata **memória → NCM → bucket**) sobre os `itens` novos sem `produto_id`. **LLM não roda no import** — é opt-in, disparado à parte (§4), coerente com a spec de classificação.
3. Responde `ResultadoImportacao` (contadores do parser) **+** resumo de classificação (quantos resolvidos por NCM/memória/bucket).

## 4. API JSON (contrato)

```
POST   /api/importacoes            multipart file(.zip|.xml) → {importacao_id, contadores, classificacao}
GET    /api/importacoes/{id}       resumo + log por arquivo (importacao_arquivos)

GET    /api/notas?mes=&loja_cnpj=&status=   lista paginada (cabeçalhos)
GET    /api/notas/{chave}          cabeçalho + itens

GET    /api/produtos?classificado=false&origem=   fila de revisão
POST   /api/produtos/{id}/categoria  {categoria_id}   → classificação manual (origem='manual', reaplica)
POST   /api/produtos/{id}/tags       {nome}           → tag manual (MVP)
DELETE /api/produtos/{id}/tags/{tag_id}

GET    /api/categorias             árvore (2 níveis)
POST   /api/categorias             {nome, parent_id?}
PATCH  /api/categorias/{id}        {nome?, parent_id?}   renomear/mover (vínculos seguem)
DELETE /api/categorias/{id}        histórico → bucket 'uncategorized'

POST   /api/llm/classificar        dispara passo LLM opt-in sobre a fila (exige LLM_ATIVO)
GET    /api/health                 schema_version, llm_ativo, contagens
```

Categorias, classificação manual e tags **delegam às operações da `classificação`** — este componente só expõe HTTP. Dinheiro em centavos e `quantidade/valor_unitario` como string decimal **atravessam intactos** (não reformatar no JSON).

## 5. UI server-rendered (Jinja2 + HTMX)

- `/` — upload (zip/xml) + últimos imports; envio via HTMX aciona o pipeline (§3).
- `/importacoes/{id}` — resultado do lote: contadores + tabela por arquivo (nova/duplicada/inválida/cancelamento/SAT).
- `/notas` — lista com filtros (mês, loja, status); `/notas/{chave}` — cabeçalho + itens.
- `/revisar` — **fila de não-classificados**: atribuir categoria inline (HTMX → `POST /api/produtos/{id}/categoria`), reaplica ao mesmo produto.
- `/taxonomia` — gerenciar categorias/subcategorias (criar/renomear/mover/apagar); apagar com histórico **avisa** que vai pro bucket.
- **Honestidade (§5 report):** onde `identidade_origem='texto'`, marcar produto como *casamento aproximado* na UI (não fingir precisão cross-loja).

## 6. Fronteiras (não fazer aqui)

Parsing/extração (parser) · cascata/NCM/identidade/edição de taxonomia como **lógica** (classificação — aqui só HTTP) · **budgets** (orçamento) · **gráficos/agregações analíticas** (visualização) · **Docker/compose/deploy** · SEFAZ/QR. Regras por regex e tags automáticas por LLM = roadmap.

## 7. Pronto = suíte verde no CI

Fixtures anonimizadas (repo público — sem CPF/CNPJ/nome real).

Invariantes:
- **Pipeline ponta-a-ponta:** zip fixture → contadores certos; **dedup idempotente** (reimportar não recontabiliza); **cancelamento em duas passadas** via HTTP; SAT/inválida caem no log e o lote não quebra.
- **Classificação no import:** produto com NCM do mapa sai classificado **sem LLM**; resto no bucket; **LLM não dispara no import**.
- **Revisão:** `POST categoria` grava `origem='manual'` e reaplica ao mesmo produto nos próximos itens.
- **Taxonomia via API:** apagar → bucket; renomear → vínculos intactos; mover → vínculos seguem.
- **Migração versionada:** rodar startup 2× não duplica nem erra (`ALTER` só uma vez); config lida **só de env**; `LLM_ATIVO` off por padrão.
- **UI smoke:** rotas respondem 200; upload aciona o pipeline; `/revisar` grava categoria.
- Saídas serializam em JSON; nenhum dado pessoal real nas fixtures.

# Spec — `ingestão-web / UI`

Camada web do app NF-e: **shell da aplicação** + **pipeline de importação** + **UI server-rendered**. Amarra `parser` (spec 01) e `classificação` (spec 02) num app HTTP. Lê `docs/historico/report_projeto_nfe.md` como contexto; esta spec é o contrato deste componente. **API-first**: a lógica mora nos núcleos; aqui só HTTP, transação e página. Faça o mais simples que passe no §7; pare nas fronteiras (§6).

Decisões travadas: **framework = FastAPI + Jinja2/HTMX** (§8 do report — núcleo JSON com FastAPI, UI fina server-rendered por cima; trocar por React depois mexe só na camada de cima). Ingestão do MVP = **upload de zip (lote inteiro) ou XML avulso pela UI**.

> Revisada em 2026-10-15, antes da primeira linha de código deste componente, para casar com o que
> as specs 01 e 02 construíram (decisões do Gui de 2026-10-15: env vars do LLM, criar categoria,
> tags adiadas, JS sem CDN).

## 1. Escopo

Sobe o app FastAPI, garante esquema + seed no startup, recebe upload, roda o lote (parser → classificação base) e serve leitura/revisão pela API e por páginas server-rendered. Entrega: shell, pipeline de importação, a **API JSON** (§4) e a **UI** (§5), incluindo **revisão de não-classificados** e **gestão de taxonomia**. Sem orçamento, sem gráficos, sem Docker, **sem tags** (roadmap: as tabelas existem, nenhuma tela as consome ainda).

## 2. App shell

- **FastAPI** serve a API (§4) e as páginas (§5). **Jinja2** renderiza; **HTMX** faz as atualizações parciais. Sem build de front, sem SPA.
- **JS vendorizado, sem CDN:** `htmx.min.js` mora em `src/nfe_parser/web/static/`, com a versão fixada e a licença ao lado. O app self-hosted funciona sem internet.
- **Config só por env var**, lida no boot (imagem pública não pode grudar no host do Gui):
  - `APP_DB_PATH` — caminho do arquivo SQLite. **Obrigatória**: sem ela o app não sobe. A pasta é criada se faltar.
  - `OLLAMA_URL` — presente **liga** o LLM; ausente o desliga (default: **desligado**).
  - `OLLAMA_MODELO`, `LLM_LIMIAR` — obrigatórias **quando** `OLLAMA_URL` existe; sem valor padrão. Configuração pela metade = o app não sobe (spec 02 §7.2, `llm.llm_do_ambiente`).
- **Esquema e seed no startup, usando o que a spec 02 já entrega:** `banco.abrir_banco` (DDL idempotente + migrações versionadas por `PRAGMA user_version`) e `seed.carregar_seed_padrao` (idempotente; nunca desfaz edição do usuário). Este componente só **chama** os dois, numa transação. Rodar o startup 2× deixa o banco idêntico.
- **Uma conexão SQLite por requisição**, com `PRAGMA foreign_keys = ON`.
- **Quem abre e fecha a transação é a camada web**, uma por operação. Os núcleos não commitam (exceto `importar`, que é dono do lote — spec 01 §6.2).
- Subir: `uvicorn nfe_parser.web.app:criar_app_do_ambiente --factory`.

## 3. Pipeline de importação (orquestração)

`POST /api/importacoes` recebe o arquivo e, **síncrono no MVP**:
1. Grava o upload num arquivo temporário com a mesma extensão e chama `importador.importar(conexao, caminho, origem=<nome original>)`. Só `.zip` e `.xml` (maiúscula ou minúscula); outra extensão → **400**, nada gravado. O `importar` é uma transação própria: o lote entra inteiro ou não entra (spec 01 §6.2).
2. **Depois** que o lote foi gravado, chama `varredura.classificar_produtos_pendentes(conexao)` **sem LLM**, numa segunda transação. **LLM não roda no import** — é opt-in, disparado à parte (§4).
   - Se a classificação falhar, a importação **continua gravada**, a resposta é **500**, e os produtos seguem pendentes (`origem IS NULL`): a próxima importação ou o disparo do LLM os pega.
3. Responde **201** com `{importacao_id, contadores, classificacao}`:
   - `contadores` = as colunas de `importacoes`: `total_arquivos, notas_novas, duplicadas, invalidas, cancelamentos_aplicados, nao_suportadas`.
   - `classificacao` = os **produtos distintos** dos itens das notas **novas** desta importação, contados pelo estado atual: `{produtos, memoria, ncm, llm, bucket}`. `memoria` = `origem in ('manual','memoria')`; `bucket` = `origem IS NULL`. Montado do banco, sem mudar contrato de núcleo.

## 4. API JSON (contrato)

Categorias são endereçadas por **`slug`**, nunca por `id` — o slug é a chave de fora, o id a de dentro (`taxonomia.py`). Produtos e importações, por `id`.

```
POST   /api/importacoes              multipart `arquivo` (.zip|.xml) → 201 {importacao_id, contadores, classificacao}
GET    /api/importacoes              as 20 mais recentes: [{importacao_id, origem, iniciado_em, finalizado_em, contadores}]
GET    /api/importacoes/{id}         {importacao_id, origem, iniciado_em, finalizado_em, contadores, classificacao,
                                      arquivos: [{arquivo, resultado, chave, detalhe}]}   (arquivos na ordem do log)

GET    /api/notas?mes=YYYY-MM&loja_cnpj=&status=ok|cancelada&pagina=1&por_pagina=50
                                     {notas: [cabeçalho], total, pagina, por_pagina}
GET    /api/notas/{chave}            a nota com itens, exatamente a saída de `serializacao.nota_para_json`

GET    /api/produtos?classificado=true|false&origem=manual|memoria|ncm|llm&pagina=1&por_pagina=50
                                     {produtos: [produto], total, pagina, por_pagina}   — a fila de revisão.
                                     Não classificado = `origem` NULL **ou** no bucket (inclui o devolvido à fila)
POST   /api/produtos/{id}/categoria  {categoria_slug} → origem='manual'; devolve o produto. Com o slug do
                                     bucket = **devolver à fila** (spec 02 §4)

GET    /api/categorias               árvore: [{slug, nome, is_bucket, n_produtos, filhas: [{slug, nome, n_produtos}]}]
POST   /api/categorias               {nome, parent_slug?} → 201 {slug, nome, parent_slug}
PATCH  /api/categorias/{slug}        {nome?, parent_slug?} → renomear e/ou mover; `parent_slug: null` sobe para
                                     nível 1, `parent_slug` ausente não move. Devolve {slug, nome, parent_slug}
DELETE /api/categorias/{slug}        → 204; produtos vão pro bucket (spec 02 §7.2)

POST   /api/llm/classificar          roda a varredura COM o LLM → {classificados}; LLM desligado → 409
GET    /api/health                   {status:"ok", schema_version, llm_ativo, contagens:{notas, itens, produtos, categorias}}
```

- **Cabeçalho de nota:** `{chave, modelo, dh_emi, emit_nome, emit_cnpj, valor_total_centavos, valor_total, status, n_itens}`. Ordem: `dh_emi` desc, depois `chave`. `mes` filtra por `substr(dh_emi,1,7)`.
- **Produto:** `{id, descricao_exemplo, identidade_origem, aproximado, gtin, categoria_slug, categoria, origem, n_itens}`. `aproximado = identidade_origem == 'texto'`. `classificado=false` ⇔ `origem IS NULL` (inclui o bucket). Ordem: `n_itens` desc, depois `id`.
- **Paginação:** `pagina ≥ 1`, `1 ≤ por_pagina ≤ 200`. Parâmetro fora do formato → 422.
- **Dinheiro** segue a spec 01 §6.2: `*_centavos` (int, fonte de verdade) + string `"123.45"` derivada. `quantidade`/`valor_unitario` atravessam como string decimal intacta.
- **Erros dos núcleos:** `LookupError` (não existe) → **404**; `ValueError` (regra recusada: apagar bucket, categoria com filhas, ciclo, terceiro nível, nome vazio, slug repetido) → **400**. Corpo `{"detail": "<mensagem do núcleo>"}`.
- Categorias e classificação manual **delegam** a `taxonomia.py` e `categorizacao.definir_categoria_manual`. Leituras ficam em `nfe_parser/consultas.py` — SQL puro, sem FastAPI, testável sem HTTP.

## 5. UI server-rendered (Jinja2 + HTMX)

Navegação comum a todas as páginas. As páginas chamam as **mesmas** funções que a API (consultas e núcleos), não a API por HTTP.

- `/` — formulário de upload (zip/xml) + últimas importações. Enviar roda o pipeline (§3) e redireciona (303) para `/importacoes/{id}`. Extensão errada → a página volta com a mensagem, status 400.
- `/importacoes/{id}` — contadores, resumo da classificação e tabela por arquivo (nova/duplicada/inválida/cancelamento/SAT).
- `/notas` — lista com filtros (mês, loja, status) e paginação; `/notas/{chave}` — cabeçalho + itens com categoria.
- `/revisar` — **fila de não-classificados** (`classificado=false` por padrão; `?todos=true` mostra todos): os que a classificação automática não resolveu **e os que o Gui devolveu**. Cada linha tem um seletor de categoria. Para produto **fora** da fila, a 1ª opção é **"↩ Não Classificado (voltar à fila)"** (o nome do bucket); dentro da fila ela não aparece, e o bucket **nunca** vem pré-selecionado — um "Salvar" sem escolher não devolve nada por acidente. O devolvido aparece com o selo *devolvido por você* (decisão do Gui de 2026-10-16, `docs/mockups/rodada-01-devolver-a-fila.html`). O HTMX posta em `/revisar/{id}` e troca só a linha. Sem HTMX (requisição comum), o mesmo POST redireciona para `/revisar`. Com LLM ligado, um botão posta em `/revisar/llm`, que roda a varredura com LLM e volta.
- **Números na tela** em formato brasileiro (`R$ 1.234,56`; `3,33`), por operação de texto sobre centavos e strings decimais — nunca float. O JSON da API não passa por essa formatação.
- `/taxonomia` — árvore com criar / renomear / mover / apagar (formulários, POST + redirect). Apagar **avisa** quantos produtos vão pro bucket antes de confirmar. Erro do núcleo → a página volta com a mensagem, status 400.
- **Honestidade (§5 do report):** produto com `identidade_origem='texto'` aparece marcado como *casamento aproximado* em `/revisar` e em `/notas/{chave}`.

## 6. Fronteiras (não fazer aqui)

Parsing/extração (parser) · cascata/NCM/identidade/edição de taxonomia como **lógica** (classificação — aqui só HTTP) · **orçamento** · **gráficos/agregações analíticas** (visualização) · **Docker/compose/deploy** · SEFAZ/QR · **tags** (roadmap) · regras por regex (roadmap).

## 7. Pronto = suíte verde no CI

Fixtures anonimizadas (repo público — sem CPF/CNPJ/nome real). Testes pela `TestClient` do FastAPI, sobre um banco em `tmp_path`; o LLM entra como função injetada em `criar_app`, nunca por rede.

**Shell e config**
- C1. `criar_app(caminho)` sobe e o banco sai com esquema na versão corrente e o seed carregado; `GET /api/health` → 200 com `schema_version` = `migracoes.versao_do_banco`, `llm_ativo: false`, contagens.
- C2. Subir o app 2× sobre o mesmo arquivo não erra nem duplica categorias.
- C3. `criar_app_do_ambiente()` lê `APP_DB_PATH`; sem ela, levanta. Sem `OLLAMA_URL`, `llm_ativo` é `false`; com `OLLAMA_URL` e sem `OLLAMA_MODELO`, levanta; `LLM_LIMIAR` que não é número entre 0 e 1 também levanta.

**Pipeline**
- C4. Zip com nota boa + XML quebrado + CF-e SAT → 201; contadores certos; os três arquivos no log de `GET /api/importacoes/{id}`.
- C5. Reimportar o mesmo zip → `notas_novas: 0`, `duplicadas` = notas do zip; contagem de notas no banco não muda.
- C6. Cancelamento via HTTP: (a) zip com o evento ANTES da nota → nota `cancelada` (duas passadas); (b) evento num upload posterior ao da nota → nota `cancelada`.
- C7. Extensão que não é `.zip`/`.xml` → 400 e nenhuma importação gravada.
- C8. Classificação no import: item com NCM do mapa sai com `origem='ncm'` e a categoria do mapa; item com NCM fora do mapa vai ao bucket; o resumo `classificacao` bate com isso.
- C9. **LLM não dispara no import**, mesmo com LLM ligado (função espiã não é chamada). `POST /api/llm/classificar` chama o LLM para os pendentes; com LLM desligado → 409.

**Leitura**
- C10. `GET /api/notas` filtra por `mes`, `loja_cnpj` e `status`, pagina, e traz `total`; `GET /api/notas/{chave}` devolve o mesmo JSON de `nota_para_json`; chave inexistente → 404.

**Revisão**
- C11. `GET /api/produtos?classificado=false` traz `origem IS NULL` e o que está no bucket, com `aproximado` certo; `classificado=true` traz o resto. `POST /api/produtos/{id}/categoria` grava `origem='manual'`; um item do mesmo produto importado depois sai com essa categoria. Produto ou slug inexistente → 404.

**Taxonomia via API**
- C12. Criar (nível 1 e subcategoria) → aparece na árvore; criar sob subcategoria → 400. Renomear → vínculos intactos. Mover → vínculos seguem; `parent_slug: null` sobe para nível 1. Apagar → produtos no bucket; apagar o bucket → 400; slug inexistente → 404.

**UI smoke**
- C13. `/`, `/notas`, `/revisar`, `/taxonomia`, `/importacoes/{id}`, `/notas/{chave}` respondem 200 com HTML. Upload pelo formulário roda o pipeline e redireciona para a importação. POST em `/revisar/{id}` grava a categoria (com e sem HTMX). `htmx.min.js` é servido de `/static/`.
- C14. Produto `texto` aparece como *casamento aproximado* em `/revisar`.
- C15. **Devolver à fila:** em `?todos=true`, produto fora da fila tem "↩ Não Classificado (voltar à fila)" como 1ª opção; produto na fila não a tem, e nenhum seletor pré-seleciona o bucket. Devolver (pela tela ou pela API) grava `origem='manual'` no bucket: o produto aparece na fila com *devolvido por você*, e nem a próxima importação nem o LLM o reclassificam.

Saídas serializam em JSON; nenhum dado pessoal real nas fixtures.

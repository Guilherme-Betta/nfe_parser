# Spec — `visualização`

Camada de **consulta e gráficos**: o usuário monta as próprias visões dos gastos (estilo Cashew), não um dashboard fixo. Lê `report_projeto_nfe.md` (§7) como contexto; esta spec é o contrato. **API-first** (JSON, não HTML) — as agregações vivem num núcleo que responde JSON; a página desenha em cima. Monta no app shell da `ingestão/UI`. Faça o mais simples que passe no §7; pare nas fronteiras (§6).

Decisões travadas (§7 do report): visões do MVP = **gasto por mês · por categoria · por loja · top produtos · evolução de preço de um produto no tempo**; tudo **read-only**; dinheiro em **centavos (int)** (o front formata pra R$). Roadmap = comparativo planejado×real, visões salvas, front React. Honestidade (§5): casar produto **entre lojas** por texto é *best-effort* — o app **sinaliza**, não finge precisão.

## 1. Escopo

O motor de **agregações gerais** que o `orçamento` delegou pra cá + a página de exploração. Entrega: as queries analíticas (§3), a **API JSON** (§4) e a página `/relatorios` com filtros e gráficos (§5). **Só leitura** — nenhuma query escreve. Sem parsing, sem classificação, sem budgets.

## 2. Modelo de dados

**Sem tabelas novas** — lê `notas`, `itens`, `produtos`, `categorias`. Se algum relatório pedir, **índice aditivo** (ex.: `notas(emit_cnpj)` pro gasto-por-loja) via migração versionada; nada além disso.

## 3. Agregações (regras comuns)

Todas: somam `itens.valor_linha` (centavos), **só `notas.status='ok'`** (cancelada nunca conta), mês = `substr(notas.dh_emi,1,7)`. **Filtros compostos** aceitos por todas (o usuário monta a visão): período (`de`/`ate` em `'YYYY-MM'`), `categoria_id` (**com rollup**: inclui subcategorias da categoria pedida), `loja_cnpj`, `produto_id`.

- **gasto-mensal** — série por `'YYYY-MM'`.
- **gasto-categoria** — soma por categoria; **rollup** subcategoria→mãe (mesma regra do orçamento §3); bucket/sem categoria retornado à parte.
- **gasto-loja** — soma por loja (`emit_cnpj` + `emit_nome`).
- **top-produtos** — soma por produto, ordenado desc, `limite` (default 20); `ordenar=valor|quantidade`.
- **preco-no-tempo** — série de `valor_unitario` por data pra um `produto_id`. Cada série carrega `identidade_origem`; **`texto` = aproximado** (best-effort, dentro da loja), **`gtin` = confiável** (cross-loja ok). Fusão cross-loja de produtos-texto é roadmap.

## 4. API JSON (contrato)

```
GET /api/relatorios/gasto-mensal     ?de=&ate=&categoria_id=&loja_cnpj=&produto_id=
                                       → [{mes, gasto}]
GET /api/relatorios/gasto-categoria  ?de=&ate=&loja_cnpj=
                                       → { linhas:[{categoria_id, nome, gasto}], nao_classificado:{gasto} }
GET /api/relatorios/gasto-loja       ?de=&ate=&categoria_id=
                                       → [{emit_cnpj, emit_nome, gasto}]
GET /api/relatorios/top-produtos     ?de=&ate=&categoria_id=&loja_cnpj=&limite=20&ordenar=valor|quantidade
                                       → [{produto_id, descricao_exemplo, gasto, quantidade, identidade_origem}]
GET /api/relatorios/preco-no-tempo   ?produto_id=  (obrigatório)
                                       → { identidade_origem, pontos:[{data, valor_unitario, emit_nome}] }
```

Centavos atravessam como int; `quantidade`/`valor_unitario` como string decimal exata (não reformatar no JSON — o front decide a exibição).

## 5. UI (`/relatorios`, no shell da ingestão/UI)

- Controles de filtro (período, categorias, lojas, produto) — o usuário **compõe a visão**; troca de filtro via HTMX re-consulta a API.
- Gráficos desenhados **no navegador** por uma lib JS leve que consome o JSON (ex.: Chart.js/ECharts — escolha do Fable; **não precisa React**, §7). **O tipo de gráfico é escolha de apresentação (front), não do dado:** a API entrega os números, ela **não fixa** o tipo. Cada análise abre num **default sensato** (mensal→linha, categoria→barra, loja→barra, top produtos→barra, preço no tempo→linha) e o usuário **troca** pelos tipos que fazem sentido pra aquela forma de dado. Fora só as combinações que mentem sobre o dado (ex.: série temporal ou ranking em pizza).
- **Sinalização honesta:** série/produto com `identidade_origem='texto'` marcado como *aproximado* na UI.

## 6. Fronteiras (não fazer aqui)

Parsing/ingestão · classificação/identidade/edição de taxonomia · **budgets** (orçamento) · qualquer **escrita** (componente é read-only) · montagem do app/rotas base é do shell da `ingestão/UI` (aqui só o módulo de queries + contrato JSON + a página de relatórios) · **roadmap:** comparativo planejado×real, visões salvas/nomeadas, fusão cross-loja de produtos-texto, front React · Docker/deploy.

## 7. Pronto = suíte verde no CI

Fixtures anonimizadas (repo público — sem CPF/CNPJ/nome real).

Invariantes:
- Cada agregação soma **exato ao centavo**; **cancelada nunca conta**; filtros (período/categoria-com-rollup/loja/produto) aplicados corretos.
- **gasto-mensal** agrupa por `'YYYY-MM'` de `dh_emi`; item de fora do intervalo não entra.
- **gasto-categoria** faz rollup subcategoria→mãe (consistente com orçamento §3); bucket/sem categoria sai em `nao_classificado`, não somado às categorias.
- **top-produtos** ordena desc e respeita `limite`; `ordenar` por valor e por quantidade.
- **preco-no-tempo** ordenado por data; `identidade_origem='gtin'` não-aproximado, `'texto'` marcado aproximado.
- **Read-only:** nenhuma query do componente escreve no banco.
- Saídas serializam em JSON; centavos int; nenhum dado pessoal real nas fixtures.

# Spec — `visualização`

Camada de **consulta e gráficos**: o usuário monta as próprias visões dos gastos (estilo Cashew), não um dashboard fixo. Lê `docs/historico/report_projeto_nfe.md` (§7) como contexto; esta spec é o contrato. **API-first** (JSON, não HTML) — as agregações vivem num núcleo que responde JSON; a página desenha em cima. Monta no app shell da `ingestão/UI` (spec 03). Faça o mais simples que passe no §7; pare nas fronteiras (§6).

Decisões travadas (§7 do report): visões do MVP = **gasto por mês · por categoria · por loja · top produtos · evolução de preço de um produto no tempo**; tudo **read-only**; dinheiro em **centavos (int)** (o front formata pra R$). Roadmap = comparativo planejado×real, visões salvas, front React. Honestidade (§5): casar produto **entre lojas** por texto é *best-effort* — o app **sinaliza**, não finge precisão.

> Revisada em 2026-10-15, antes do código: categoria por **slug** (spec 03), o mesmo motor de gasto
> do orçamento (`gastos.py`, spec 04), e as regras de gráfico do método de visualização adotado.

## 1. Escopo

O motor de **agregações gerais** que o `orçamento` delegou pra cá + a página de exploração. Entrega: as queries analíticas (§3, em `nfe_parser/relatorios.py`), a **API JSON** (§4) e a página `/relatorios` com filtros e gráficos (§5). **Só leitura** — nenhuma query escreve. Sem parsing, sem classificação, sem budgets.

## 2. Modelo de dados

**Sem tabelas novas** — lê `notas`, `itens`, `produtos`, `categorias`. Nenhum índice novo no MVP.

## 3. Agregações (regras comuns)

Todas usam as regras de `gastos.py` (as mesmas do orçamento, spec 04 §3): somam `itens.valor_linha` (centavos), **só `notas.status='ok'`** (cancelada nunca conta), mês = `substr(notas.dh_emi,1,7)`. **Filtros compostos, aceitos por todas** (o usuário monta a visão): período (`de`/`ate` em `'YYYY-MM'`, inclusivos), `categoria_slug` (**com rollup**: inclui as subcategorias da pedida), `loja_cnpj`, `produto_id`. Categoria ou produto inexistente → `LookupError`.

- **gasto-mensal** — série por `'YYYY-MM'`, em ordem. **Meses sem gasto entram com 0** entre o primeiro e o último (ou entre `de` e `ate`, quando dados): um buraco na série é informação, e o gráfico de linha não pode ligar os pontos por cima dele.
- **gasto-categoria** — soma por categoria de nível 1, com rollup (a mesma função do orçamento); bucket, produto sem categoria e item sem produto saem à parte, em `nao_classificado`.
- **gasto-loja** — soma por loja (`emit_cnpj`, com um `emit_nome`), maior primeiro; empate pelo CNPJ.
- **top-produtos** — soma por produto, maior primeiro, `limite` (default 20, 1–100); `ordenar=valor|quantidade`. A quantidade é somada em **decimal exato** (a string do XML), nunca float, e sai como string. Empate pelo `produto_id`.
- **preco-no-tempo** — os pontos `{data, valor_unitario, emit_nome, emit_cnpj}` de um `produto_id`, por data. Leva `identidade_origem` e `aproximado` (`texto` = aproximado, dentro da loja; `gtin` = confiável cross-loja).

## 4. API JSON (contrato)

```
GET /api/relatorios/gasto-mensal     → [{mes, gasto}]
GET /api/relatorios/gasto-categoria  → { linhas: [{categoria_slug, nome, gasto}], nao_classificado: {gasto} }
GET /api/relatorios/gasto-loja       → [{emit_cnpj, emit_nome, gasto}]
GET /api/relatorios/top-produtos     ?limite=20&ordenar=valor|quantidade
                                     → [{produto_id, descricao_exemplo, gasto, quantidade, identidade_origem, aproximado,
                                         emit_cnpj}]   (emit_cnpj só no produto por texto: a identidade dele é a loja)
GET /api/relatorios/preco-no-tempo   ?produto_id=  (obrigatório)
                                     → { produto_id, descricao_exemplo, identidade_origem, aproximado,
                                         pontos: [{data, valor_unitario, emit_nome, emit_cnpj}] }
```

Todas aceitam `de`, `ate`, `categoria_slug`, `loja_cnpj`, `produto_id`. Parâmetro fora do formato → 422; categoria ou produto inexistente → 404. Centavos atravessam como int; `quantidade`/`valor_unitario` como string decimal exata.

## 5. UI (`/relatorios`, no shell da ingestão/UI)

- **Uma linha de filtros acima de tudo** (período, categoria, loja; o produto entra ao clicar num produto do ranking e sai por um "remover"). Os filtros são um formulário GET — a página recarrega com a visão nova, e todos os gráficos respondem ao mesmo recorte.
- Os gráficos são desenhados **no navegador** pelo **Chart.js** (copiado em `web/static/`, sem CDN), a partir do JSON que as mesmas funções do §3 produzem, embutido na página.
- **O tipo de gráfico é escolha de apresentação**, trocada por um seletor em cada análise, só entre tipos que não mentem sobre o dado:

  | Análise | Padrão | Alternativa |
  | ------- | ------ | ----------- |
  | gasto mensal | linha | barras |
  | por categoria | barras horizontais | barras verticais |
  | por loja | barras horizontais | barras verticais |
  | top produtos | barras horizontais | barras verticais |
  | preço no tempo | linha | pontos |

  ⛔ **Sem pizza/rosca.** Série temporal e ranking em pizza mentem; e para categoria/loja a regra "a cor segue a entidade, nunca a posição" não fecha com mais de 8 fatias possíveis — a barra compara melhor e com uma cor só.
- **Uma série por gráfico, uma cor** (o azul validado contra as superfícies clara e escura); sem legenda (o título nomeia a série). "Não classificado" aparece como barra cinza à parte, rotulada. Traços finos, grade discreta, tooltip com o valor em R$.
- **Toda análise tem a tabela gêmea** (renderizada no servidor): o tooltip nunca é o único jeito de ler um valor.
- **Sinalização honesta:** produto/série com `identidade_origem='texto'` marcado como *aproximado*.
- **Rótulo repetido ganha o fim do CNPJ** no gráfico (filiais com o mesmo nome; o mesmo produto sem código de barras em lojas diferentes); a tabela gêmea mostra o CNPJ inteiro. O **seletor de loja** da linha de filtros segue a mesma regra: duas lojas de mesmo nome nunca saem como opções idênticas.
- Item **Relatórios** na navegação.

## 6. Fronteiras (não fazer aqui)

Parsing/ingestão · classificação/identidade/edição de taxonomia · **budgets** (orçamento) · qualquer **escrita** (componente é read-only) · montagem do app/rotas base (shell da `ingestão/UI`) · **roadmap:** comparativo planejado×real, visões salvas/nomeadas, fusão cross-loja de produtos-texto, front React · Docker/deploy.

## 7. Pronto = suíte verde no CI

Fixtures anonimizadas (repo público — sem CPF/CNPJ/nome real).

- V1. Cada agregação soma **exato ao centavo**; **cancelada nunca conta**; filtros (período/categoria-com-rollup/loja/produto) aplicados corretos.
- V2. **gasto-mensal** agrupa por `'YYYY-MM'` de `dh_emi`, em ordem; mês sem gasto no meio sai com 0; fora do intervalo não entra.
- V3. **gasto-categoria** faz rollup subcategoria→mãe (igual ao orçamento); bucket sai em `nao_classificado`.
- V4. **gasto-loja** soma por loja, maior primeiro.
- V5. **top-produtos** ordena desc, respeita `limite`; `ordenar=quantidade` soma em decimal exato.
- V6. **preco-no-tempo** ordenado por data; `gtin` não-aproximado, `texto` aproximado; produto inexistente → 404.
- V7. **Read-only:** nenhuma função do componente muda o banco (`total_changes` igual antes e depois).
- V8. **UI smoke:** `/relatorios` responde 200 com e sem filtros; traz as tabelas e o JSON dos gráficos; o seletor de tipo da série mensal não oferece pizza; `chart.umd.js` é servido; produto `texto` aparece como aproximado; lojas de mesmo nome saem distinguidas pelo fim do CNPJ no seletor de loja.
- Saídas serializam em JSON; centavos int; nenhum dado pessoal real nas fixtures.

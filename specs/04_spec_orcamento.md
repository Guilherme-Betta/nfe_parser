# Spec — `orçamento`

Consumidor do núcleo: define **tetos de gasto por categoria/mês** e calcula o **realizado** contra eles. Lê `report_projeto_nfe.md` (§6) como contexto; esta spec é o contrato. **API-first** (JSON, não HTML). Monta no app shell da `ingestão/UI`. Faça o mais simples que passe no §7; pare nas fronteiras (§6).

Decisões travadas (§6 do report): **MVP = budget por categoria, período mensal; só despesas; só BRL.** Roadmap = por subcategoria, metas, recorrência, contas/carteiras, comparativo multi-período planejado×real. Dinheiro em **centavos (int)**, como no resto do app.

## 1. Escopo

CRUD de orçamentos (teto por categoria nível-1 por mês) + o **realizado do mês** (agrega `itens`→`produtos`→`categorias`, exclui canceladas) + o readout `limite / gasto / saldo` por categoria. Entrega: tabela `orcamentos`, a query de realizado com rollup, a **API JSON** (§4) e a **página** `/orcamento` (§5). Sem parsing, sem classificação, sem analytics gerais.

## 2. Modelo de dados (DDL — idempotente)

```sql
CREATE TABLE IF NOT EXISTS orcamentos (
  id INTEGER PRIMARY KEY,
  categoria_id INTEGER NOT NULL REFERENCES categorias(id),
  mes TEXT NOT NULL,                         -- competência 'YYYY-MM'
  limite INTEGER NOT NULL,                    -- centavos (>0)
  criado_em TEXT NOT NULL, atualizado_em TEXT NOT NULL,
  UNIQUE (categoria_id, mes)
);
CREATE INDEX IF NOT EXISTS idx_orcamentos_mes ON orcamentos(mes);
```

Migração **versionada** (mesmo runner da `ingestão/UI`, via `schema_version`). **Regra de negócio (app, não CHECK):** no MVP `categoria_id` só pode ser **categoria nível-1** (`parent_id IS NULL`) e **nunca o bucket** (`slug='uncategorized'`) — rejeitar subcategoria/bucket com erro claro. Orçamento por subcategoria é roadmap.

## 3. Realizado (agregação)

`gasto_por_categoria(mes)` — para o mês pedido:
- **Fonte:** `itens.valor_linha` (centavos) somado, via `itens.produto_id → produtos.categoria_id`.
- **Mês:** `substr(notas.dh_emi,1,7) = mes` (competência = data de emissão, `'YYYY-MM'`).
- **Status:** só `notas.status='ok'` — **cancelada não conta**.
- **Rollup:** produto classificado numa **subcategoria** soma no teto da **categoria-mãe** (subir `parent_id` até o nível 1). Um budget de "Mercado" inclui "Laticínios", "Padaria", etc.
- **Sem categoria:** produtos no bucket / `categoria_id IS NULL` **não entram em nenhum orçamento** — retornados **à parte** (`nao_classificado`), pra revisão, não fingindo caber num teto.
- **Saldo:** `saldo = limite − gasto`; negativo = **estouro** (sinalizar, não esconder).

## 4. API JSON (contrato)

```
GET    /api/orcamentos?mes=YYYY-MM   → { mes,
                                         linhas: [{categoria_id, nome, limite|null, gasto, saldo|null, pct|null}],
                                         nao_classificado: {gasto},
                                         totais: {limite, gasto} }
POST   /api/orcamentos               {categoria_id, mes, limite}   (valida nível-1, não-bucket, limite>0)
PATCH  /api/orcamentos/{id}          {limite}
DELETE /api/orcamentos/{id}
```

`linhas` inclui **toda categoria nível-1 com orçamento no mês OU com gasto no mês** (`limite=null` quando há gasto sem teto — deixa o Gui ver onde o dinheiro foi e criar o teto). Centavos atravessam como int; `pct = gasto/limite` só quando há limite.

## 5. UI (`/orcamento`, no shell da ingestão/UI)

- Seletor de **mês**; lista por categoria: **limite · gasto · saldo** + barra de progresso (estouro em destaque).
- Editar/criar/apagar teto inline (HTMX → API do §4).
- Linha **"Não classificado"** separada, com o gasto sem categoria e atalho pra `/revisar`.

## 6. Fronteiras (não fazer aqui)

Parsing/ingestão · classificação/identidade/taxonomia · **analytics gerais** (por loja, top produtos, preço no tempo, group-by arbitrário = `visualização`) · montagem do app/rotas e render são do shell da `ingestão/UI` (aqui só o módulo + contrato JSON + a página de orçamento) · **roadmap:** subcategoria, metas, recorrência, carteiras, comparativo multi-período · Docker/deploy.

## 7. Pronto = suíte verde no CI

Fixtures anonimizadas (repo público — sem CPF/CNPJ/nome real).

Invariantes:
- **Realizado** soma exato ao centavo; **cancelada não conta**; item de outro mês (por `dh_emi`) não entra.
- **Rollup:** item classificado em subcategoria soma no teto da categoria-mãe; produto no bucket/sem categoria **fica fora** dos tetos e aparece em `nao_classificado`.
- **CRUD:** `UNIQUE (categoria_id, mes)` respeitado; orçamento em subcategoria ou no bucket é **rejeitado**; `limite>0`.
- **Saldo:** `limite − gasto`, negativo permitido e sinalizado como estouro.
- `linhas` traz categoria com gasto **sem** teto (`limite=null`), não só as orçadas.
- Migração versionada idempotente (rodar 2× não duplica/erra).
- Saídas serializam em JSON; nenhum dado pessoal real nas fixtures.

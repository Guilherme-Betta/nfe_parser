# Spec — `orçamento`

Consumidor do núcleo: define **tetos de gasto por categoria/mês** e calcula o **realizado** contra eles. Lê `docs/historico/report_projeto_nfe.md` (§6) como contexto; esta spec é o contrato. **API-first** (JSON, não HTML). Monta no app shell da `ingestão/UI` (spec 03). Faça o mais simples que passe no §7; pare nas fronteiras (§6).

Decisões travadas (§6 do report): **MVP = budget por categoria, período mensal; só despesas; só BRL.** Roadmap = por subcategoria, metas, recorrência, contas/carteiras, comparativo multi-período planejado×real. Dinheiro em **centavos (int)**, como no resto do app.

> Revisada em 2026-10-15, antes do código, para seguir as convenções que a spec 03 fixou: categoria
> endereçada por **slug**, migração no runner que já existe (`PRAGMA user_version`), transação
> aberta pela camada `operacoes`.

## 1. Escopo

CRUD de orçamentos (teto por categoria nível-1 por mês) + o **realizado do mês** (agrega `itens`→`produtos`→`categorias`, exclui canceladas) + o readout `limite / gasto / saldo` por categoria. Entrega: tabela `orcamentos`, a query de realizado com rollup, a **API JSON** (§4) e a **página** `/orcamento` (§5). Sem parsing, sem classificação, sem analytics gerais.

## 2. Modelo de dados

**Migração v4** em `migracoes.py` (o runner de `PRAGMA user_version` da spec 02; uma migração aplicada é imutável):

```sql
CREATE TABLE IF NOT EXISTS orcamentos (
  id INTEGER PRIMARY KEY,
  categoria_id INTEGER NOT NULL REFERENCES categorias(id) ON DELETE CASCADE,
  mes TEXT NOT NULL,                         -- competência 'YYYY-MM'
  limite INTEGER NOT NULL,                   -- centavos (>0)
  criado_em TEXT NOT NULL, atualizado_em TEXT NOT NULL,
  UNIQUE (categoria_id, mes)
);
CREATE INDEX IF NOT EXISTS idx_orcamentos_mes ON orcamentos(mes);
```

**Regras de negócio (app, não CHECK):** no MVP a categoria só pode ser **nível-1** (`parent_id IS NULL`) e **nunca o bucket** — subcategoria/bucket recusados com erro claro. `limite` inteiro > 0. `mes` = `'YYYY-MM'` com mês 01–12. Orçamento por subcategoria é roadmap.

⚠️ **Apagar categoria com orçamento** (spec 02, `taxonomia.apagar_categoria`): sem regra, o `REFERENCES` impediria. Os orçamentos da categoria apagada são **apagados junto**, pelo `ON DELETE CASCADE` — o teto era daquela categoria, e o gasto dela vai para o bucket, que não tem teto. Fica no banco, e não em `taxonomia.py`: o núcleo da spec 02 não precisa conhecer uma tabela da 04.

## 3. Realizado (agregação)

Núcleo em `nfe_parser/gastos.py` — o mesmo motor que a `visualização` (spec 05) usa:
- **Fonte:** `itens.valor_linha` (centavos) somado, via `itens.produto_id → produtos.categoria_id`.
- **Mês:** `substr(notas.dh_emi,1,7)` (competência = data de emissão).
- **Status:** só `notas.status='ok'` — **cancelada não conta**.
- **Rollup:** produto numa **subcategoria** soma no teto da **categoria-mãe** (sobe `parent_id` até o nível 1, por CTE recursiva).
- **Sem categoria:** produto no bucket, produto com `categoria_id` NULL e item sem produto **não entram em nenhum orçamento** — retornados à parte (`nao_classificado`), pra revisão.
- **Saldo:** `saldo = limite − gasto`; negativo = **estouro** (`estouro: true`, sinalizado, não escondido).

## 4. API JSON (contrato)

```
GET    /api/orcamentos?mes=YYYY-MM   (obrigatório) → { mes,
         linhas: [{orcamento_id|null, categoria_slug, nome, limite|null, gasto, saldo|null, pct|null, estouro}],
         nao_classificado: {gasto},
         totais: {limite, gasto} }
POST   /api/orcamentos               {categoria_slug, mes, limite} → 201 {id, categoria_slug, mes, limite}
PATCH  /api/orcamentos/{id}          {limite} → {id, categoria_slug, mes, limite}
DELETE /api/orcamentos/{id}          → 204
```

- `linhas` traz **toda categoria nível-1 com orçamento no mês OU com gasto no mês** (`limite=null` quando há gasto sem teto — mostra onde o dinheiro foi e deixa criar o teto). Ordem por slug.
- `pct = gasto/limite` (razão, 4 casas) só quando há limite. `estouro = saldo < 0`.
- `totais.limite` = soma dos limites; `totais.gasto` = **todo** o gasto do mês, incluindo o não classificado (o total honesto).
- Erros como na spec 03: `LookupError` → 404; `ValueError` (subcategoria, bucket, limite ≤ 0, mês inválido, orçamento repetido) → 400.

## 5. UI (`/orcamento`, no shell da ingestão/UI)

- Seletor de **mês** (padrão: o mês corrente); lista por categoria: **limite · gasto · saldo** + barra de progresso (estouro em destaque).
- Criar teto (categoria nível-1 + valor em reais), alterar e apagar — formulários, POST + redirect, mantendo o mês. Valor digitado em reais (`1.234,56` ou `1234.56`) vira centavos por aritmética decimal, nunca float.
- Linha **"Não classificado"** separada, com o gasto sem categoria e atalho pra `/revisar`.
- Item **Orçamento** na navegação.

## 6. Fronteiras (não fazer aqui)

Parsing/ingestão · classificação/identidade/taxonomia · **analytics gerais** (por loja, top produtos, preço no tempo = `visualização`) · montagem do app/rotas base (shell da `ingestão/UI`) · **roadmap:** subcategoria, metas, recorrência, carteiras, comparativo multi-período · Docker/deploy.

## 7. Pronto = suíte verde no CI

Fixtures anonimizadas (repo público — sem CPF/CNPJ/nome real).

- O1. **Realizado** soma exato ao centavo; **cancelada não conta**; item de outro mês (por `dh_emi`) não entra.
- O2. **Rollup:** item em subcategoria soma no teto da categoria-mãe; produto no bucket fica fora dos tetos e aparece em `nao_classificado`.
- O3. **CRUD:** criar devolve o orçamento; repetir `(categoria, mes)` → 400; subcategoria ou bucket → 400; `limite ≤ 0` → 400; mês fora do formato → 400 (API: 422 no GET); categoria inexistente → 404; alterar e apagar id inexistente → 404.
- O4. **Saldo:** `limite − gasto`, negativo permitido e com `estouro: true`.
- O5. `linhas` traz categoria com gasto **sem** teto (`limite=null`) e categoria com teto **sem** gasto (`gasto=0`).
- O6. Migração v4 idempotente (abrir o banco 2× não erra); apagar categoria com orçamento apaga o orçamento junto.
- O7. **UI smoke:** `/orcamento` responde 200 com o mês corrente e com `?mes=`; criar teto pelo formulário grava e redireciona; valor `1.234,56` vira `123456`; estouro aparece destacado.
- Saídas serializam em JSON; nenhum dado pessoal real nas fixtures.

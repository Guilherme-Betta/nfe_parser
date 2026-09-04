# Spec — `parser + modelo de dados`

Núcleo de ingestão do app NF-e. Lê `report_projeto_nfe.md` como contexto; esta spec é o contrato deste componente só. **API-first** (fala JSON, não HTML). Faça o mais simples que passe nos critérios do §5 — sem abstrações além disso, pare nas fronteiras (§4).

Decisões travadas: guardar o XML original na nota; inválidas/não-parseáveis vão num log separado, não em `notas`.

## 1. Escopo

Recebe um **.zip de XMLs** (lote inteiro de uma vez) ou um **.xml avulso** → detecta tipo, extrai, persiste em **SQLite**, devolve relatório JSON. Sem rede (nada de SEFAZ), sem UI, sem entrada manual.

## 2. Modelo de dados (DDL — criação idempotente)

Convenções (não óbvias, respeitar):
- Gasto (`valor_total`, `valor_linha`) = **inteiro em centavos** (sem float).
- `quantidade` e `valor_unitario` = **string decimal exata** do XML (qCom fracionário; vUnCom com muitas casas).
- `chave`, `emit_cnpj`, `ncm`, `gtin` = **TEXT** (têm zero à esquerda).
- Datas = **ISO-8601 com offset**, como no XML.

```sql
CREATE TABLE IF NOT EXISTS importacoes (
  id INTEGER PRIMARY KEY,
  origem TEXT NOT NULL, iniciado_em TEXT NOT NULL, finalizado_em TEXT,
  total_arquivos INTEGER DEFAULT 0, notas_novas INTEGER DEFAULT 0,
  duplicadas INTEGER DEFAULT 0, invalidas INTEGER DEFAULT 0,
  cancelamentos_aplicados INTEGER DEFAULT 0, nao_suportadas INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS notas (
  chave TEXT PRIMARY KEY,                    -- 44 dígitos
  modelo INTEGER NOT NULL,                   -- 55 | 65
  serie INTEGER, numero INTEGER, dh_emi TEXT NOT NULL,
  emit_nome TEXT, emit_cnpj TEXT, emit_municipio TEXT, emit_uf TEXT,
  valor_total INTEGER NOT NULL,              -- centavos (vNF)
  forma_pagamento TEXT,
  status TEXT NOT NULL DEFAULT 'ok' CHECK (status IN ('ok','cancelada')),
  cancelado_em TEXT, xml_raw TEXT NOT NULL,
  importacao_id INTEGER REFERENCES importacoes(id), criado_em TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_notas_dh_emi ON notas(dh_emi);

CREATE TABLE IF NOT EXISTS itens (
  id INTEGER PRIMARY KEY,
  nota_chave TEXT NOT NULL REFERENCES notas(chave),
  n_item INTEGER NOT NULL,                   -- nItem
  descricao TEXT NOT NULL,                   -- xProd (cru)
  cprod TEXT, ncm TEXT, gtin TEXT,           -- gtin NULL quando "SEM GTIN"
  quantidade TEXT NOT NULL, unidade TEXT,
  valor_unitario TEXT, valor_linha INTEGER NOT NULL,  -- centavos (vProd)
  criado_em TEXT NOT NULL,
  UNIQUE (nota_chave, n_item)
);
CREATE INDEX IF NOT EXISTS idx_itens_nota ON itens(nota_chave);
CREATE INDEX IF NOT EXISTS idx_itens_ncm  ON itens(ncm);
CREATE INDEX IF NOT EXISTS idx_itens_gtin ON itens(gtin);

CREATE TABLE IF NOT EXISTS importacao_arquivos (  -- log por arquivo do lote
  id INTEGER PRIMARY KEY,
  importacao_id INTEGER NOT NULL REFERENCES importacoes(id),
  arquivo TEXT, arquivo_hash TEXT, chave TEXT,
  resultado TEXT NOT NULL CHECK (resultado IN (
    'nova','duplicada','invalida',
    'cancelamento_aplicado','cancelamento_orfao','nao_suportado_sat')),
  detalhe TEXT
);
```

`status` só tem `ok|cancelada` porque "duplicada"/"inválida" são desfechos de *importação* (log), não estados de nota.

## 3. Comportamento

- **Roteamento por raiz + `ide/mod`:** NF-e/NFC-e mod 55/65 → extrai; `procEventoNFe` com `tpEvento=110111` → cancelamento; `CFe`/modelo 59 → `nao_suportado_sat`; resto ou XML corrompido → `invalida`. **Nenhum arquivo derruba o lote.**
- **Extração 55 e 65 = mesmo caminho** (schema NF-e; parser schema-aware, ex. `nfelib`). Itens: um por `det` (repete em multi-item). `xProd` guardado cru — normalização é da classificação.
- **Dedup idempotente por `chave`:** já existe → não recontabiliza, marca `duplicada`. Reprocessar o mesmo zip deixa o banco idêntico.
- **Cancelamento em duas passadas** (insere notas, depois aplica eventos) pra ordem no zip não importar. Evento sem nota → `cancelamento_orfao`, sem criar nota fantasma. Nota `cancelada` não conta como gasto.
- **Saída:** `ResultadoImportacao` (JSON) com contadores + destino de cada arquivo. Leitura mínima do núcleo: `obter_nota(chave)`, `listar_itens(chave)`.

## 4. Fronteiras (não fazer aqui)

Classificação/NCM/LLM · identidade e normalização de produto (`produtos`) · budgets e agregações analíticas · UI/HTTP/upload · download SEFAZ/QR. Este núcleo só entrega os campos brutos que esses componentes consomem.

## 5. Pronto = suíte verde no CI

Fixtures **anonimizadas** (repo público — sem CPF/CNPJ/nome real): 55 (1 item), 65, multi-item, sem-GTIN, evento de cancelamento, CF-e/SAT, XML corrompido. Anonimização é um utilitário dev a construir.

Invariantes que os testes verificam:
- 55, 65 e multi-item extraídos corretos (N `det` → N itens); multi-item fecha o gap do report §11.
- Dedup idempotente; cancelamento aplicado inclusive com evento antes da nota; órfão e inválido não quebram o lote; SAT ignorado com marca.
- Dinheiro exato ao centavo; quantidade fracionária (kg) preservada; GTIN ausente → NULL.
- Saídas serializam em JSON; nenhum dado pessoal real nas fixtures.

# Spec — `parser + modelo de dados`

Núcleo de ingestão do app NF-e. Lê `docs/historico/report_projeto_nfe.md` como contexto; esta spec é o contrato deste componente só. **API-first** (fala JSON, não HTML). Faça o mais simples que passe nos critérios do §5 — sem abstrações além disso, pare nas fronteiras (§4).

Decisões travadas: guardar o XML original na nota; inválidas/não-parseáveis vão num log separado, não em `notas`.

## 1. Escopo

Recebe um **.zip de XMLs** (lote inteiro de uma vez) ou um **.xml avulso** → detecta tipo, extrai, persiste em **SQLite**, devolve relatório JSON. Sem rede (nada de SEFAZ), sem UI, sem entrada manual.

## 2. Modelo de dados (DDL — criação idempotente)

Convenções (não óbvias, respeitar):
- Gasto (`valor_total`, `valor_linha`) = **inteiro em centavos** (sem float).
- `quantidade` e `valor_unitario` = **string decimal exata** do XML (qCom fracionário; vUnCom com muitas casas).
- `chave`, `emit_cnpj`, `ncm`, `gtin` = **TEXT** (têm zero à esquerda).
- `emit_cnpj` é o **documento do emitente**: o CNPJ (14 dígitos) ou, quando o emitente é pessoa
  física (produtor rural, por exemplo), o **CPF** (11 dígitos). O nome da coluna ficou do tempo
  em que só havia CNPJ; os dois tamanhos nunca colidem (decisão do Gui de 2026-10-16, §6.3).
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
  emit_nome TEXT,
  emit_cnpj TEXT,                            -- CNPJ (14) OU CPF (11) do emitente; nome histórico
  emit_municipio TEXT, emit_uf TEXT,
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
-- migração v5 (2026-10-16): o CHECK acima aceita também 'evento_registrado'

CREATE TABLE IF NOT EXISTS eventos (    -- migração v5: todo evento que abre, guardado
  id INTEGER PRIMARY KEY,
  chave TEXT NOT NULL,                   -- chNFe; ⛔ sem REFERENCES: a nota pode chegar depois
  tp_evento TEXT NOT NULL, n_seq INTEGER NOT NULL,   -- nSeqEvento (1 se ausente)
  dh_evento TEXT, descricao TEXT,        -- descEvento
  correcao TEXT,                         -- xCorrecao: só a carta de correção (110110)
  xml_raw TEXT NOT NULL,
  importacao_id INTEGER REFERENCES importacoes(id), criado_em TEXT NOT NULL,
  UNIQUE (chave, tp_evento, n_seq)
);
```

`status` só tem `ok|cancelada` porque "duplicada"/"inválida" são desfechos de *importação* (log), não estados de nota.

## 3. Comportamento

- **Roteamento por raiz + `ide/mod`:** NF-e/NFC-e mod 55/65 → extrai; `procEventoNFe` → evento (guardado; `tpEvento=110111` cancela, os outros ficam registrados); `CFe`/modelo 59 → `nao_suportado_sat`; resto ou XML corrompido → `invalida`. **Nenhum arquivo derruba o lote.**
- **Extração 55 e 65 = mesmo caminho** (schema NF-e; parser schema-aware, ex. `nfelib`). Itens: um por `det` (repete em multi-item). `xProd` guardado cru — normalização é da classificação.
- **Dedup idempotente por `chave`:** já existe → não recontabiliza, marca `duplicada`. Reprocessar o mesmo zip deixa o banco idêntico.
- **Cancelamento em duas passadas** (insere notas, depois aplica eventos) pra ordem no zip não importar. Evento sem nota → `cancelamento_orfao`, sem criar nota fantasma; o evento fica guardado, e a nota que chegar num lote posterior já entra cancelada (§6.2). Nota `cancelada` não conta como gasto.
- **Saída:** `importar()` devolve o `id` da importação; os contadores ficam em `importacoes`, e o destino de cada arquivo em `importacao_arquivos`. Leitura do núcleo: `nota_para_json(conexao, chave)` — a nota com os itens dentro, como string JSON, ou `None` se a chave não existe.

## 4. Fronteiras (não fazer aqui)

Classificação/NCM/LLM · identidade e normalização de produto (`produtos`) · budgets e agregações analíticas · UI/HTTP/upload · download SEFAZ/QR. Este núcleo só entrega os campos brutos que esses componentes consomem.

## 5. Pronto = suíte verde no CI

Fixtures **anonimizadas** (repo público — sem CPF/CNPJ/nome real): 55 (1 item), 65, multi-item, sem-GTIN, evento de cancelamento, CF-e/SAT, XML corrompido. Anonimização é um utilitário dev a construir.

Invariantes que os testes verificam:
- 55, 65 e multi-item extraídos corretos (N `det` → N itens); multi-item fecha o gap do report §11.
- Dedup idempotente; cancelamento aplicado inclusive com evento antes da nota; órfão e inválido não quebram o lote; SAT ignorado com marca.
- Dinheiro exato ao centavo; quantidade fracionária (kg) preservada; GTIN ausente → NULL.
- Emitente com CPF: o CPF vai em `emit_cnpj`, e a nota importa — inclusive item sem GTIN, que se identifica pelo texto + CPF (§6.3).
- Saídas serializam em JSON; nenhum dado pessoal real nas fixtures.

## 6. Decisões tomadas na implementação

> **Aprovado pelo Gui em 2026-10-16.** Consolida o que as stories 002–006 e 013, a refatoração de
> 2026-10-14 e as decisões de 2026-10-16 decidiram ao construir este núcleo. É contrato; as specs
> das stories voltam a ser só registro.

### 6.1 Onde o texto acima divergia do que foi construído

Aplicado nas §1–§5 na aprovação (2026-10-16): a saída de `importar()` e a leitura por
`nota_para_json`, na §3.

### 6.2 Regras decididas

**Importação**
- **O lote é uma transação.** `importar` grava tudo ou nada: se algo levanta no meio — erro de
  gravação, não de conteúdo —, o lote inteiro é desfeito e o erro sobe (story 013 D3/D4;
  refatoração de 2026-10-14).
- **NF-e que abre mas está incompleta** (sem `pag`, `detPag`, `vNF`, `prod`…) é `invalida`, com o
  erro em `detalhe`. ⛔ Não é tolerada com campo vazio: esses blocos são obrigatórios no leiaute
  4.00 (refatoração de 2026-10-14).
- `.zip` e `.xml` avulso seguem o mesmo caminho. No `.zip`, membros que não terminam em `.xml` e
  diretórios são ignorados — não viram linha nem entram na contagem.
- O `arquivo_hash` é o SHA-256 dos **bytes** do arquivo, não do texto decodificado.
- `cancelamento_orfao` entra no total de arquivos mas não tem contador próprio em `importacoes`.

**Eventos** (story 005; decisão do Gui de 2026-10-16)
- **Todo evento que abre e traz `chNFe` é guardado** em `eventos`, com o XML inteiro — mesmo que a
  nota ainda não esteja no banco: quando ela chegar, a correção já está lá. Reimportar não duplica
  (`UNIQUE (chave, tp_evento, n_seq)`; o primeiro guardado vence). Motivo: coerência com o
  `xml_raw` das notas, e a informação não se perde se o arquivo original sumir.
- Só `tpEvento = 110111` cancela. Outro evento (carta de correção, ciência da operação…) é
  `evento_registrado`, com a descrição no `detalhe`, e não muda nota nenhuma. Sem `chNFe`, não há
  a que ligá-lo: continua `cancelamento_orfao`.
- O evento é lido pelo binding **genérico** do `nfelib` (`nfe_evento_generico`): o de cancelamento
  recusava a carta de correção real (o campo `xCorrecao` não existe nele) e a marcava `invalida`.
- A carta de correção só corrige texto: por lei não muda valores, quantidades, preços, impostos,
  emitente/destinatário nem data. O app guarda e mostra; não aplica nada.
- `cancelado_em` é a hora **do cancelamento**: o `dhEvento` do XML, como veio ("datas como no XML").
  Evento sem `dhEvento` (fora do leiaute) usa a hora da importação, para nota cancelada nunca ficar
  sem carimbo (decisão do Gui de 2026-10-16, §6.3).
- Reaplicar o mesmo evento não move `cancelado_em`: o primeiro carimbo vence, e o resultado
  continua `cancelamento_aplicado`.
- Evento de nota importada num lote **anterior** também aplica. Evento cujo XML não abre é
  `invalida`, e o lote segue.
- E o contrário (2026-10-17): **cancelamento que chegou num lote anterior ao da nota** — guardado,
  e `cancelamento_orfao` naquele lote — é aplicado quando a nota chega. `cancelado_em` é o
  `dhEvento` do evento guardado, com a mesma regra de carimbo acima. A linha da nota no log
  continua `nova`, com `detalhe` = `cancelada: o cancelamento chegou antes, na importação N`; o
  contador `cancelamentos_aplicados` do lote não a conta (ele conta arquivos de cancelamento). A
  linha `cancelamento_orfao` do lote antigo fica como está: o log registra o desfecho daquele lote.
- Banco que já tinha nota `ok` com cancelamento guardado (o caso acima, antes da correção) é
  corrigido uma vez pela **migração v6**, com o mesmo carimbo. Órfão importado antes da v5 não foi
  guardado e não tem como ser aplicado sozinho: reimportar o XML do evento resolve.

**Saída JSON** (story 006, decisão do Gui de 15/09)
- **Dinheiro sai em dois campos:** `valor_total_centavos` (int — a fonte de verdade, com o qual se
  faz conta) e `valor_total` (string `"123.45"` — para ler). Idem `valor_linha_centavos` e
  `valor_linha`. A string é sempre derivada do inteiro na hora de serializar; somar strings é errado.
- **Não saem:** `xml_raw` (o documento inteiro, e o repo é público), `importacao_id` e `criado_em`
  (escrituração do banco); nos itens, `id`, `nota_chave` e `produto_id`.
- Itens saem em ordem de `n_item`, com a categoria (ver spec 02 §7).

### 6.3 Decisões do Gui

1. ✅ **DECIDIDO (Gui, 2026-10-16): opção (c), o CPF faz o papel de "loja".** Antes, NF-e de
   emitente com CPF e item sem GTIN derrubava o lote inteiro (pela UI, erro 500): a identidade de
   produto por texto exige o documento da loja, e o extrator só lia o CNPJ. Agora o CPF vai em
   `emit_cnpj` (§2) e tudo o que agrupa por loja — identidade de produto, filtro, relatórios — o
   trata como mais uma loja. ⚠️ É dado pessoal de terceiro no banco local, mas não é exposição nova:
   o `xml_raw` já guardava o documento inteiro. Fixtures continuam com CPF de mentira.
2. ✅ **DECIDIDO (Gui, 2026-10-16): hora do cancelamento.** `cancelado_em` era a hora da
   IMPORTAÇÃO, e o `dhEvento` extraído do XML era descartado. Agora é o `dhEvento` (§6.2). Notas
   já canceladas num banco existente mantêm o carimbo antigo: o primeiro carimbo vence.

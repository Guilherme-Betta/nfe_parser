# Spec — 006 · A saida em JSON

Fecha a invariante do §5 da `specs/01_spec_parser_modelo.md`: *"Saidas serializam em JSON"*.

E a ultima invariante do §5 que nenhuma story anterior fechou. Com ela, o parser esta completo
pela propria definicao de pronto da spec 01.

---

## 1. O que existe hoje, e por que nao basta

`grep -rn "import json" src/` em 15/09 nao devolve **nada**. Os seis modulos de `src/nfe_parser/`
(`banco`, `classificador`, `extrator`, `importador`, `persistencia`, `cancelamento`) sabem ler XML
e gravar no SQLite, e nenhum deles sabe entregar um resultado para fora.

Hoje a unica forma de ver uma nota importada e abrir o banco com um cliente SQL. Isso nao e uma
saida: e o deposito. A story 006 constroi a primeira saida do projeto.

⚠️ **A consequencia invisivel:** a story 005 ensinou o banco a marcar `status = 'cancelada'`. Como
nao existe saida, ninguem **ve** essa marca. Enquanto o JSON nao mostrar o status, a 005 inteira e
trabalho que o usuario nao consegue observar.

---

## 2. DDL: nada muda

✅ **Verificado em 15/09 contra `src/nfe_parser/banco.py`.** Todo campo que a saida precisa ja
existe no esquema da story 001:

| Campo | Onde | Tipo no banco |
| ----- | ---- | ------------- |
| `notas.valor_total` | `banco.py:29` | INTEGER, **centavos** |
| `notas.status` | `banco.py:31` | TEXT, `'ok'` ou `'cancelada'` |
| `notas.cancelado_em` | `banco.py:32` | TEXT, NULL quando nao cancelada |
| `itens.valor_linha` | `banco.py:45` | INTEGER, **centavos** |

⛔ **Nenhuma tarefa desta story pode tocar em `banco.py`, nem em qualquer modulo existente.** A 006
so **le** o banco. Se alguma tarefa precisar alterar `src/` fora do modulo novo, a spec esta errada.

---

## 3. A decisao de produto: dinheiro sai em DOIS campos

O Gui decidiu na abertura de 15/09, e o racional dele foi: *"o ponto do app e facilitar analises de
despesas, entao facilitar contas e mais util"* — mas pediu tambem que o arquivo continuasse legivel.

**Decisao: cada valor monetario aparece duas vezes.**

| Campo no JSON | Tipo | Para que serve |
| ------------- | ---- | -------------- |
| `valor_total_centavos` | int | **a fonte de verdade.** Espelha o banco. E com ele que se faz conta. |
| `valor_total` | str, `"123.45"` | **apresentacao.** E o que se le ao abrir o arquivo. |

Mesmo par para os itens: `valor_linha_centavos` (int) e `valor_linha` (str).

### Por que isso nao cria duas fontes de verdade

O risco obvio de dois campos e eles discordarem. Aqui nao podem, por construcao:

🔴 **A string e SEMPRE derivada do inteiro, no momento de serializar. Ela nunca e guardada, nunca e
lida do banco, nunca e recebida como parametro.** Existe um unico lugar onde ela nasce — a funcao
`de_centavos` da tarefa 1 — e um unico dado de onde ela vem. Nao ha dois dados: ha um dado e uma
apresentacao dele.

### O contrato para quem consome

📋 **Quem faz conta usa o campo `_centavos`. Quem exibe usa a string.** Somar as strings esta
errado. Isso fica escrito no `README` da saida e nao so nesta spec.

### Por que a string nao pode ser calculada com float

`12345 / 100` e uma divisao de ponto flutuante binario, e ponto flutuante binario **nao representa
decimais exatamente**. O erro nao aparece em `123.45`; aparece em valores grandes e em somas
acumuladas, que e exatamente o caso de uma analise de despesas.

⛔ **A conversao e feita so com aritmetica de inteiro** (`//` e `%`). Nenhuma tarefa desta story
pode usar `/`, `float`, `round` ou `Decimal` para formatar dinheiro. A tarefa 1 tem um teste
especifico para isso, com um valor grande o bastante para o float errar.

---

## 4. Criterios de aceite

Os seis criterios abaixo sao os que o Gui aprovou na abertura da sessao, refinados em blocos
testaveis. Os titulos C1–C3 sao a numeracao dos blocos; os numeros 1–6 entre parenteses apontam
para o criterio aprovado que cada bloco serve.

### C1 — Formatar dinheiro (criterio 2)

`de_centavos(centavos: int) -> str` devolve o valor com exatamente duas casas decimais, usando so
aritmetica de inteiro. `0` vira `"0.00"`, `5` vira `"0.05"`, `12345` vira `"123.45"`.

### C2 — A nota vira JSON (criterios 1, 3, 4, 5, 6)

`nota_para_json(conexao, chave) -> str | None` devolve uma **string** que `json.loads` le de volta.

- **criterio 3:** `status` e `cancelado_em` estao na saida, sempre. Uma nota nao cancelada sai com
  `status = "ok"` e `cancelado_em = null`.
- **criterio 4:** chave que nao esta no banco devolve **`None`**, nunca `"{}"`. Escolhido `None` em
  vez de excecao porque "nao achei" e um desfecho normal de uma consulta, nao um erro de programa.
  Quem chama distingue com `if resultado is None`.
- **criterio 5:** o conjunto de chaves e **fechado e listado abaixo**. `xml_raw` fica de fora, e
  tambem ficam de fora `importacao_id` e `criado_em`, que sao escrituracao interna do banco e nao
  fazem parte da nota.
- **criterio 6:** `ensure_ascii=False`. `"Sao Paulo"` escrito com til volta de `json.loads`
  identico, nao como `\u00e3`.

**As chaves da nota, nesta ordem e so estas:**

    chave · modelo · serie · numero · dh_emi · emit_nome · emit_cnpj · emit_municipio ·
    emit_uf · valor_total_centavos · valor_total · forma_pagamento · status · cancelado_em

### C3 — Os itens vao junto (criterio 1)

A saida da C2 ganha a chave `itens`: uma lista, **ordenada por `n_item`**, vazia quando a nota nao
tem item nenhum.

**As chaves de cada item, nesta ordem e so estas:**

    n_item · descricao · cprod · ncm · gtin · quantidade · unidade · valor_unitario ·
    valor_linha_centavos · valor_linha

`id` e `nota_chave` ficam de fora: o primeiro e chave artificial do SQLite, o segundo ja esta na
nota que contem a lista.

---

## 5. Onde o codigo mora

📁 **Modulo novo: `src/nfe_parser/serializacao.py`.** Ele nasce vazio na tarefa 1 e cresce nas
tarefas 2 e 3. Nenhum arquivo existente de `src/` e alterado por esta story.

⚠️ **Por que modulo novo, e nao dentro de `extrator.py`:** `de_centavos` e a inversa de
`para_centavos`, que mora la — a tentacao de juntar e real. Mas `extrator.py` responde "como tiro
dado de um XML" e a 006 responde "como entrego dado para fora". Sao dois sentidos opostos do fluxo,
e mistura-los faria `extrator.py` importar `json` sem precisar.

---

## 6. O que esta FORA desta story

- ⛔ Serializar um **lote** de notas, ou um resumo de importacao. A 006 entrega **uma nota por
  chamada**. Lote e outra story.
- ⛔ Escrever o JSON em arquivo, ou uma CLI. A funcao devolve string; quem grava e outra camada.
- ⛔ Ler JSON de volta para dentro do banco. Nao ha desserializacao nesta story.
- ⛔ Qualquer campo calculado que o banco nao tenha (total de itens, media, imposto). Criterio 5.

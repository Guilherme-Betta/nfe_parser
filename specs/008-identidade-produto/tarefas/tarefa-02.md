Acrescente UMA funcao ao arquivo `src/nfe_parser/produtos.py`:

```python
def resolver_produto_por_gtin(conexao, gtin, descricao_exemplo):
    ...
```

Ela devolve o `id` (inteiro) da linha de `produtos` que representa aquele codigo de barras,
criando a linha se ela ainda nao existir.

A funcao `normalizar_descricao` ja esta pronta e testada. NAO mexa nela. Esta tarefa NAO a usa:
quem tem GTIN e identificado pelo GTIN, e a descricao so fica guardada para leitura humana.


A TABELA JA EXISTE. Ela foi criada pela migracao v1 e NAO se altera:

```sql
CREATE TABLE produtos (
  id INTEGER PRIMARY KEY,
  identidade_origem TEXT NOT NULL CHECK (identidade_origem IN ('gtin','texto')),
  gtin TEXT,
  descricao_normalizada TEXT, emit_cnpj TEXT,
  descricao_exemplo TEXT,
  categoria_id INTEGER REFERENCES categorias(id),
  origem TEXT CHECK (origem IN ('manual','memoria','ncm','llm')),
  confianca REAL,
  criado_em TEXT NOT NULL, atualizado_em TEXT NOT NULL
);
```


O ALGORITMO, NESTA ORDEM

1. PROCURE: `SELECT id FROM produtos WHERE gtin = ?`
2. Se achou, devolva o `id` encontrado e PARE. Nao atualize nada.
3. Se nao achou, INSIRA uma linha nova e devolva `cursor.lastrowid`.

Na linha nova, grave exatamente estes campos e nenhum outro:

| coluna | valor |
| ------ | ----- |
| `identidade_origem` | a string `'gtin'` |
| `gtin` | o `gtin` recebido |
| `descricao_exemplo` | a `descricao_exemplo` recebida, CRUA, sem normalizar |
| `criado_em` | `datetime.now(UTC).isoformat()` |
| `atualizado_em` | o mesmo valor de `criado_em` |

`descricao_normalizada`, `emit_cnpj`, `categoria_id`, `origem` e `confianca` NAO entram no INSERT.
Elas ficam NULL, e ha teste afirmando isso.

O import do relogio e o mesmo que o resto do projeto ja usa:

```python
from datetime import UTC, datetime
```


REGRA 1 -- ⛔ NADA DE `INSERT OR IGNORE`, `ON CONFLICT` OU `INSERT OR REPLACE`.

Procure primeiro com SELECT, insira so no ramo em que nao achou.

Com `OR IGNORE`, quando a linha ja existe o INSERT e descartado em silencio e o `lastrowid` fica
com um valor que nao e o id daquela linha. A funcao devolveria o id ERRADO, e so na segunda
chamada -- sem erro nenhum aparecendo. Ha teste que chama duas vezes e compara os dois ids.


REGRA 2 -- ⛔ NAO CHAME `conexao.commit()`.

Quem abriu a transacao e que a fecha. Este modulo so escreve.

Nenhum teste pegaria isso (a mesma conexao enxerga o que ela mesma nao commitou), e por isso a
regra esta escrita aqui: e revisao humana, nao teste. Nao commite.

⛔ Tambem nao chame `rollback`, `BEGIN`, `close` nem `execute("PRAGMA ...")`.


REGRA 3 -- O MESMO GTIN E O MESMO PRODUTO, VENHA DE ONDE VIER.

Chamada duas vezes com o mesmo `gtin` e `descricao_exemplo` DIFERENTE, a funcao devolve o MESMO id
e `produtos` continua com UMA linha. Isso e proposital: o codigo de barras e global, e duas lojas
que escrevem a descricao de jeitos diferentes vendem o mesmo produto.

⛔ Nao atualize `descricao_exemplo` nem `atualizado_em` quando encontrar a linha. O ramo do passo 2
nao escreve nada.


REGRA 4 -- NENHUMA CATEGORIA.

`categoria_id`, `origem` e `confianca` ficam NULL. Dizer a que categoria o produto pertence e
assunto de outra story. Ha teste afirmando que `categoria_id` e NULL.


O QUE NAO PODE MUDAR

NAO altere `normalizar_descricao`. Ela ja passa nos testes dela; mexer nela os deixa vermelhos.

NAO faca `CREATE TABLE`, `ALTER TABLE` nem `CREATE INDEX`. O esquema ja esta pronto.

NAO altere nenhum outro arquivo: nem `banco.py`, nem `migracoes.py`, nem teste nenhum.

NAO escreva a resolucao por texto/CNPJ. Ela e a proxima tarefa.

Acrescente a PRIMEIRA migracao ao arquivo `src/nfe_parser/migracoes.py`.

O executor (`versao_do_banco`, `aplicar_migracoes`) ja esta pronto e funcionando. NAO mexa nele.

Escreva uma funcao nova e registre-a em `MIGRACOES`:

```python
def _migracao_01_esquema_classificacao(conexao):
    ...


MIGRACOES = [_migracao_01_esquema_classificacao]
```

Ela cria as 5 tabelas e os 2 indices abaixo, e NADA MAIS.

```sql
CREATE TABLE IF NOT EXISTS categorias (
  id INTEGER PRIMARY KEY,
  slug TEXT NOT NULL UNIQUE,
  nome TEXT NOT NULL,
  parent_id INTEGER REFERENCES categorias(id),
  is_bucket INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS ncm_ancora (
  prefixo TEXT PRIMARY KEY,
  categoria_id INTEGER NOT NULL REFERENCES categorias(id)
);

CREATE TABLE IF NOT EXISTS produtos (
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

CREATE UNIQUE INDEX IF NOT EXISTS ux_produtos_gtin
  ON produtos(gtin) WHERE gtin IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ux_produtos_texto
  ON produtos(descricao_normalizada, emit_cnpj) WHERE gtin IS NULL;

CREATE TABLE IF NOT EXISTS tags (id INTEGER PRIMARY KEY, nome TEXT NOT NULL UNIQUE);

CREATE TABLE IF NOT EXISTS produto_tags (
  produto_id INTEGER NOT NULL REFERENCES produtos(id),
  tag_id INTEGER NOT NULL REFERENCES tags(id),
  PRIMARY KEY (produto_id, tag_id)
);
```

Copie o DDL acima COMO ESTA. Nao renomeie coluna, nao troque tipo, nao acrescente coluna, nao
tire CHECK.


REGRA 1 -- O `WHERE` DOS DOIS INDICES NAO E ENFEITE.

Os dois indices sao PARCIAIS. O `WHERE` e a razao de eles existirem, e ha teste para cada um.

`ux_produtos_gtin ... WHERE gtin IS NOT NULL` -- sem o `WHERE`, dois produtos sem GTIN (os dois
com `gtin` NULL) continuariam sendo aceitos pelo SQLite, mas o indice passaria a cobrir linhas que
ele nao deve cobrir. Com o `WHERE`, a unicidade vale so para quem TEM gtin.

`ux_produtos_texto ... WHERE gtin IS NULL` -- a unicidade por (descricao_normalizada, emit_cnpj)
vale so para os produtos SEM gtin. Quem tem gtin e identificado pelo gtin, e pode repetir
descricao a vontade.

Escreva os dois `WHERE` exatamente como no DDL acima.


REGRA 2 -- NADA DE `executescript`.

`conexao.executescript(...)` faz COMMIT implicito e destroi a transacao que o executor abriu. O
`ROLLBACK` passaria a explodir com "cannot rollback - no transaction is active". Foi medido.

Rode um comando por chamada:

```python
conexao.execute("CREATE TABLE IF NOT EXISTS categorias (...)")
conexao.execute("CREATE TABLE IF NOT EXISTS ncm_ancora (...)")
```

Uma lista de strings com um `for` tambem serve. O que nao pode e `executescript`.


REGRA 3 -- NENHUMA LINHA DE DADO.

Esta migracao cria tabela VAZIA. Nenhum `INSERT`. Nenhuma categoria, nenhum bucket
"uncategorized", nenhum NCM, nenhuma tag. O carregamento de dados e outra story.


O QUE NAO PODE MUDAR:

NAO altere `versao_do_banco` nem `aplicar_migracoes`. Eles ja passam nos testes deles, e mexer
neles deixa aqueles testes vermelhos.

NAO faca `ALTER TABLE` em nada. A tabela `itens` nao e assunto desta tarefa.

NAO altere nenhum outro arquivo.

Acrescente DUAS funcoes ao FIM de `src/nfe_parser/categorizacao.py`, nesta ordem:

```python
def _categoria_do_bucket(conexao):
    ...

def classificar_produto(conexao, produto_id, ncm):
    ...
```

`classificar_produto` decide a categoria de UM produto, GRAVA o resultado na linha dele em
`produtos`, e devolve o `categoria_id` (inteiro) que valeu.

A funcao `buscar_categoria_por_ncm` ja esta pronta e testada. USE-A. ⛔ NAO reescreva a busca por
prefixo, e NAO mexa nela.


AS TABELAS JA EXISTEM. Foram criadas pela migracao v1 e NAO se alteram:

```sql
CREATE TABLE categorias (
  id INTEGER PRIMARY KEY, slug TEXT NOT NULL UNIQUE, nome TEXT NOT NULL,
  parent_id INTEGER REFERENCES categorias(id),
  is_bucket INTEGER NOT NULL DEFAULT 0        -- 1 = o bucket "Nao Classificado"
);
CREATE TABLE produtos (
  id INTEGER PRIMARY KEY, ...,
  categoria_id INTEGER REFERENCES categorias(id),
  origem TEXT CHECK (origem IN ('manual','memoria','ncm','llm')),
  confianca REAL, criado_em TEXT NOT NULL, atualizado_em TEXT NOT NULL
);
```


`_categoria_do_bucket` -- O ALGORITMO

```python
linha = conexao.execute("SELECT id FROM categorias WHERE is_bucket = 1").fetchone()
if linha is None:
    raise LookupError("nenhuma categoria com is_bucket = 1; o seed da taxonomia nao foi carregado")
return linha[0]
```


`classificar_produto` -- O ALGORITMO, NESTA ORDEM

1. LEIA a linha do produto:

```python
linha = conexao.execute(
    "SELECT categoria_id, origem FROM produtos WHERE id = ?", (produto_id,)
).fetchone()
if linha is None:
    raise LookupError(f"produto {produto_id} nao existe")
categoria_atual, origem_atual = linha[0], linha[1]
```

2. PASSO 1 DA CASCATA -- memoria. Se `origem_atual in ("manual", "memoria")`, devolva
   `categoria_atual` e PARE. ⛔ Nao escreva NADA neste ramo.

3. PASSO 2 DA CASCATA -- NCM. Chame `buscar_categoria_por_ncm(conexao, ncm)`.

4. PASSO 4 DA CASCATA -- bucket. Se o passo 3 devolveu `None`, a categoria e
   `_categoria_do_bucket(conexao)` e a origem e `None`. Senao, a origem e a string `"ncm"`.

5. GRAVE, com UM unico UPDATE:

```python
conexao.execute(
    "UPDATE produtos SET categoria_id = ?, origem = ?, atualizado_em = ? WHERE id = ?",
    (categoria, origem, datetime.now(UTC).isoformat(), produto_id),
)
```

6. Devolva `categoria`.

O import do relogio e o mesmo que o resto do projeto ja usa:

```python
from datetime import UTC, datetime
```


REGRA 1 -- ⛔ ESCREVA A CASCATA COMO `if` EM SEQUENCIA DENTRO DA FUNCAO.

⛔ NAO crie `REGRAS = [...]`, `CASCATA = {...}`, nem lista ou dicionario NENHUM no nivel do modulo.
⛔ NAO crie uma funcao por passo da cascata.

Sao tres passos fixos. A indirecao custaria mais do que economiza, e o arquivo tem de continuar
sendo imports + funcoes, na ordem em que foram escritas.


REGRA 2 -- 🔴 O QUE PROTEGE E A `origem`, NAO O FATO DE TER CATEGORIA.

Produto com `categoria_id` preenchido e `origem IS NULL` esta NO BUCKET, e TEM de ser reprocessado:
se o mapa NCM cresceu desde a ultima vez, ele sai do bucket agora.

⛔ Nao escreva `if categoria_atual is not None: return categoria_atual`. Isso prenderia no bucket,
para sempre, todo produto que caiu la uma vez. Ha teste que poe um produto no bucket, acrescenta o
prefixo NCM, roda de novo e exige que ele SAIA.

A unica condicao que faz a funcao parar no passo 1 e `origem_atual in ("manual", "memoria")`.


REGRA 3 -- A LEITURA DO PASSO 1 TAMBEM E A CHECAGEM DE EXISTENCIA.

`WHERE id = NULL` nao casa com nada em SQL. Sem o `if linha is None: raise`, chamar com um
`produto_id` que nao existe -- ou com `None` -- faria o UPDATE afetar ZERO linhas em silencio, e a
funcao devolveria um `categoria_id` que nao foi gravado em lugar nenhum.

⛔ `LookupError`, NAO `ValueError`: o argumento esta bem formado; o que falta e a linha no banco.


REGRA 4 -- O BUCKET GRAVA `origem = None`, E ISSO E DE PROPOSITO.

E o `None` do Python, que vira NULL no SQLite. ⛔ Nao grave a string `"bucket"` nem a string
`"None"`: a coluna tem `CHECK (origem IN ('manual','memoria','ncm','llm'))` e qualquer string fora
dessa lista seria RECUSADA pelo banco.


REGRA 5 -- ⛔ A CHECAGEM DO BUCKET E PREGUICOSA.

So chame `_categoria_do_bucket` no ramo em que o NCM NAO casou. Um banco sem bucket cujo produto
casa pelo NCM tem de classificar normalmente. ⛔ Nao chame a funcao no inicio de
`classificar_produto`.


REGRA 6 -- ⛔ NAO CHAME `conexao.commit()`.

Quem abriu a transacao e que a fecha. Nenhum teste pegaria isso (a mesma conexao enxerga o que ela
mesma nao commitou), e por isso a regra esta escrita aqui: e revisao humana, nao teste.

⛔ Tambem nao chame `rollback`, `BEGIN`, `close` nem `execute("PRAGMA ...")`.


O QUE NAO PODE MUDAR

NAO altere `buscar_categoria_por_ncm`. Ela ja passa nos testes dela.

NAO faca `CREATE TABLE`, `ALTER TABLE` nem `CREATE INDEX`. O esquema ja esta pronto.

NAO escreva nada sobre LLM nem sobre `confianca`. Nao e desta story.

NAO escreva a funcao da classificacao MANUAL. Ela e a proxima tarefa.

NAO altere nenhum outro arquivo: nem `banco.py`, nem `migracoes.py`, nem `produtos.py`, nem teste
nenhum.

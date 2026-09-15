Crie o arquivo NOVO `src/nfe_parser/taxonomia.py` com UMA funcao:

```python
def apagar_categoria(conexao, slug):
    ...
```

O arquivo comeca com estes dois imports, e SO estes dois:

```python
from datetime import UTC, datetime

from nfe_parser.categorizacao import categoria_do_bucket
```

`categoria_do_bucket(conexao)` JA EXISTE e devolve o `id` da categoria "Nao Classificado". Ela
levanta sozinha se o bucket nao existir. NAO reimplemente essa busca.

Colunas das tabelas, que ja existem e NAO se alteram:

```
categorias           id, slug, nome, parent_id, is_bucket
ncm_ancora           prefixo, categoria_id   (categoria_id e NOT NULL)
categorias_apagadas  slug, apagada_em
produtos             id, categoria_id, origem, atualizado_em, e outras
```


O ALGORITMO SAO SETE PASSOS, NESTA ORDEM

PASSO 1 -- ache a categoria, e recuse se ela nao existir:

```python
linha = conexao.execute("SELECT id, is_bucket FROM categorias WHERE slug = ?", (slug,)).fetchone()
if linha is None:
    raise LookupError(f"nao existe categoria com slug {slug!r}")
categoria_id, is_bucket = linha[0], linha[1]
```

PASSO 2 -- recuse apagar o bucket:

```python
if is_bucket:
    raise ValueError(f"a categoria {slug!r} e o bucket; apaga-la quebraria a classificacao")
```

PASSO 3 -- recuse apagar categoria que tem filhas:

```python
filhas = conexao.execute(
    "SELECT COUNT(*) FROM categorias WHERE parent_id = ?", (categoria_id,)
).fetchone()[0]
if filhas:
    raise ValueError(
        f"a categoria {slug!r} tem {filhas} subcategoria(s);"
        " mova ou apague as subcategorias antes de apagar esta"
    )
```

PASSO 4 -- mande os produtos dela para o bucket, ZERANDO a origem:

```python
conexao.execute(
    "UPDATE produtos SET categoria_id = ?, origem = NULL, atualizado_em = ? WHERE categoria_id = ?",
    (categoria_do_bucket(conexao), datetime.now(UTC).isoformat(), categoria_id),
)
```

PASSO 5 -- apague as ancoras NCM que apontavam para ela:

```python
conexao.execute("DELETE FROM ncm_ancora WHERE categoria_id = ?", (categoria_id,))
```

PASSO 6 -- registre a lapide:

```python
conexao.execute(
    "INSERT INTO categorias_apagadas (slug, apagada_em) VALUES (?, ?) ON CONFLICT(slug) DO NOTHING",
    (slug, datetime.now(UTC).isoformat()),
)
```

PASSO 7 -- apague a categoria:

```python
conexao.execute("DELETE FROM categorias WHERE id = ?", (categoria_id,))
```


REGRA 1 -- A ORDEM DOS PASSOS 4, 5 E 7 E OBRIGATORIA. As chaves estrangeiras estao LIGADAS, e
apagar a categoria com produto ou ancora ainda apontando para ela levanta `IntegrityError` e nada
acontece. NAO apague a categoria primeiro. NAO use `ON DELETE CASCADE`.


REGRA 2 -- O PASSO 4 ZERA A `origem`, E ESSE E O PONTO MAIS IMPORTANTE DA TAREFA.

O que protege um produto de ser reclassificado e a coluna `origem`, nao a categoria. Produto que
fosse para o bucket mantendo `origem = 'manual'` ficaria protegido DENTRO do bucket, para sempre.

O UPDATE escreve `origem = NULL` em TODOS os produtos da categoria, sem olhar o que estava la.
NAO acrescente `AND origem IS NULL`. NAO preserve `'manual'`. NAO trate `'manual'` como especial.


REGRA 3 -- O PASSO 6 USA `ON CONFLICT(slug) DO NOTHING`, porque a mesma categoria pode ser apagada
duas vezes ao longo da vida do banco. NAO use `INSERT OR REPLACE`.


REGRA 4 -- A FUNCAO DEVOLVE None, e NAO CHAMA `commit`, `rollback`, `BEGIN`, `close` nem `PRAGMA`:
sao quatro escritas que tem de entrar ou nao entrar juntas.


REGRA 5 -- NENHUMA LISTA, DICIONARIO OU CONSTANTE NO NIVEL DO MODULO. O arquivo e imports +
funcoes, e as proximas tarefas acrescentam funcoes depois da ultima linha.


O QUE NAO PODE MUDAR

NAO faca `CREATE TABLE`, `ALTER TABLE` nem `CREATE INDEX`.

NAO leia `categorias_apagadas`: quem a le e o seed, que e outro arquivo.

NAO escreva funcao para renomear nem para mover categoria. Sao as proximas tarefas.

NAO altere nenhum outro arquivo: nem `banco.py`, nem `migracoes.py`, nem `categorizacao.py`, nem
`seed.py`, nem teste nenhum.

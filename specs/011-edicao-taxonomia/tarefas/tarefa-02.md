O arquivo `src/nfe_parser/taxonomia.py` JA EXISTE e ja tem `apagar_categoria`.

`apagar_categoria` E OS IMPORTS DO TOPO NAO SE ALTERAM. Voce vai devolver o arquivo INTEIRO, entao
ela tem de voltar exatamente como esta hoje, completa. A funcao nova entra DEPOIS da ultima linha
dela.

Acrescente UMA funcao:

```python
def mover_categoria(conexao, slug, novo_parent_slug):
    ...
```

A tabela `categorias` ja existe e NAO se altera. Colunas: `id`, `slug`, `nome`, `parent_id`,
`is_bucket`. O `parent_id` guarda o `id` da categoria pai, ou NULL para categoria de nivel 1.


O ALGORITMO SAO CINCO PASSOS, NESTA ORDEM

PASSO 1 -- ache a categoria que vai ser movida, e recuse se ela nao existir:

```python
linha = conexao.execute("SELECT id FROM categorias WHERE slug = ?", (slug,)).fetchone()
if linha is None:
    raise LookupError(f"nao existe categoria com slug {slug!r}")
categoria_id = linha[0]
```

PASSO 2 -- `novo_parent_slug` igual a None significa "vira categoria de nivel 1". Trate isso e
TERMINE a funcao aqui:

```python
if novo_parent_slug is None:
    conexao.execute("UPDATE categorias SET parent_id = NULL WHERE id = ?", (categoria_id,))
    return
```

PASSO 3 -- ache o novo pai, e recuse se ele nao existir:

```python
pai = conexao.execute("SELECT id FROM categorias WHERE slug = ?", (novo_parent_slug,)).fetchone()
if pai is None:
    raise LookupError(f"nao existe categoria com slug {novo_parent_slug!r} para ser o novo pai")
```

PASSO 4 -- A SUBIDA. Suba a arvore a partir do novo pai; se o caminho passar pela propria categoria
que esta sendo movida, e ciclo:

```python
atual = pai[0]
while atual is not None:
    if atual == categoria_id:
        raise ValueError(
            f"mover {slug!r} para dentro de {novo_parent_slug!r} criaria um ciclo na arvore"
        )
    atual = conexao.execute(
        "SELECT parent_id FROM categorias WHERE id = ?", (atual,)
    ).fetchone()[0]
```

PASSO 5 -- grave:

```python
conexao.execute("UPDATE categorias SET parent_id = ? WHERE id = ?", (pai[0], categoria_id))
```


REGRA 1 -- A SUBIDA DO PASSO 4 E O CORACAO DA TAREFA.

Categoria movida para dentro de uma descendente dela propria fecha um ciclo: a arvore deixa de ter
fim, e quem a percorrer depois roda para sempre. O banco NAO pega isso, porque cada linha, sozinha,
aponta para um pai que existe.

NAO troque o `while` por um teste de um nivel so (comparar o novo pai com a categoria, ou o pai do
novo pai). Um ciclo pode se fechar tres, quatro niveis acima.

Mover uma categoria para dentro dela mesma ja e pego na primeira volta do `while`, porque `atual`
comeca valendo o proprio `categoria_id` nesse caso.

O `while` SEMPRE termina: ou chega a `parent_id` NULL, ou reencontra a categoria movida.


REGRA 2 -- O `id` DA CATEGORIA MOVIDA NAO MUDA, e por isso mover NAO mexe em vinculo nenhum. A
funcao escreve a coluna `parent_id`, e SO ela. NAO apague e reinsira a categoria. NAO escreva na
coluna `slug` nem na coluna `nome`.


REGRA 3 -- A FUNCAO DEVOLVE None, e NAO CHAMA `commit`, `rollback`, `BEGIN`, `close` nem `PRAGMA`.
O `return` do PASSO 2 e um `return` seco, so para terminar mais cedo.


REGRA 4 -- NENHUMA LISTA, DICIONARIO OU CONSTANTE NO NIVEL DO MODULO.


O QUE NAO PODE MUDAR

NAO altere `apagar_categoria` nem os imports do topo. Ela volta inteira e identica.

NAO faca `CREATE TABLE`, `ALTER TABLE` nem `CREATE INDEX`.

NAO escreva funcao para renomear categoria. E a proxima tarefa.

NAO escreva nada sobre `produtos`, `ncm_ancora`, bucket, lapide, classificacao ou seed.

NAO altere nenhum outro arquivo: nem `banco.py`, nem `migracoes.py`, nem `categorizacao.py`, nem
`seed.py`, nem teste nenhum.

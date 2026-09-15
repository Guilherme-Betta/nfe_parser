O arquivo `src/nfe_parser/taxonomia.py` JA EXISTE e ja tem `apagar_categoria`.

`apagar_categoria` E OS IMPORTS DO TOPO NAO SE ALTERAM. Voce vai devolver o arquivo INTEIRO, entao
ela tem de vir de volta exatamente como esta hoje, completa. As funcoes novas entram DEPOIS da
ultima linha dela.

Acrescente DUAS funcoes:

```python
def renomear_categoria(conexao, slug, nome):
    ...


def mover_categoria(conexao, slug, novo_parent_slug):
    ...
```

A tabela ja existe e NAO se altera:

```sql
CREATE TABLE categorias (
  id INTEGER PRIMARY KEY, slug TEXT NOT NULL UNIQUE, nome TEXT NOT NULL,
  parent_id INTEGER REFERENCES categorias(id), is_bucket INTEGER NOT NULL DEFAULT 0
);
```


`renomear_categoria` -- TRES PASSOS, NESTA ORDEM

PASSO 1 -- recuse nome vazio ANTES de ir ao banco:

```python
if not nome:
    raise ValueError(f"renomear_categoria exige um nome nao vazio; recebeu {nome!r}")
```

PASSO 2 -- ache a categoria, e recuse se ela nao existir:

```python
linha = conexao.execute("SELECT id FROM categorias WHERE slug = ?", (slug,)).fetchone()
if linha is None:
    raise LookupError(f"nao existe categoria com slug {slug!r}")
```

PASSO 3 -- grave so o nome:

```python
conexao.execute("UPDATE categorias SET nome = ? WHERE slug = ?", (nome, slug))
```


`mover_categoria` -- CINCO PASSOS, NESTA ORDEM

PASSO 1 -- ache a categoria que vai ser movida, igual ao PASSO 2 acima, e guarde o id dela em
`categoria_id`.

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


REGRA 1 -- A SUBIDA DO PASSO 4 E O CORACAO DESTA TAREFA.

Categoria movida para dentro de uma descendente dela propria fecha um ciclo: a arvore deixa de ter
fim, e quem a percorrer depois roda para sempre. O banco NAO pega isso, porque cada linha, sozinha,
aponta para um pai que existe.

Mover uma categoria para dentro dela mesma ja e pego na primeira volta do `while`, porque `atual`
comeca valendo o proprio `categoria_id` quando o novo pai e a propria categoria.

O `while` SEMPRE termina: ou chega a `parent_id` NULL, ou reencontra a categoria movida.


REGRA 2 -- O `slug` NUNCA MUDA.

`renomear_categoria` escreve a coluna `nome`, e SO ela. NAO calcule slug a partir do nome, NAO
escreva na coluna `slug`, NAO normalize, NAO tire acento, NAO troque espaco por hifen.

O slug e a identidade da categoria para o resto do sistema; muda-lo faria outra parte do programa
achar que a categoria sumiu.


REGRA 3 -- AS DUAS FUNCOES DEVOLVEM None, e NAO CHAMAM `conexao.commit()`, `rollback`, `BEGIN`,
`close` nem `PRAGMA`.

O `return` do PASSO 2 de `mover_categoria` e um `return` seco, so para terminar mais cedo.


REGRA 4 -- NENHUMA LISTA, DICIONARIO OU CONSTANTE NO NIVEL DO MODULO.


O QUE NAO PODE MUDAR

NAO altere `apagar_categoria` nem os imports do topo do arquivo. Ela volta inteira e identica.

NAO faca `CREATE TABLE`, `ALTER TABLE` nem `CREATE INDEX`.

NAO escreva nada sobre `produtos`, `ncm_ancora`, bucket, lapide, classificacao ou seed. Renomear e
mover NAO mexem em vinculo nenhum: o `id` fica igual, e tudo que aponta para ele continua apontando
sozinho. E por isso que esta e a tarefa facil.

NAO altere nenhum outro arquivo: nem `banco.py`, nem `migracoes.py`, nem `categorizacao.py`, nem
`seed.py`, nem teste nenhum.

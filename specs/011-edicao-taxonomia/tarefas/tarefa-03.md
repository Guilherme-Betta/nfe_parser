O arquivo `src/nfe_parser/taxonomia.py` JA EXISTE e ja tem `apagar_categoria` e
`mover_categoria`.

AS DUAS FUNCOES QUE JA ESTAO LA, E OS IMPORTS DO TOPO, NAO SE ALTERAM. Voce vai devolver o arquivo
INTEIRO, entao as duas tem de voltar exatamente como estao hoje, completas, na mesma ordem. A funcao
nova entra DEPOIS da ultima linha delas.

Acrescente UMA funcao:

```python
def renomear_categoria(conexao, slug, nome):
    ...
```

A tabela `categorias` ja existe e NAO se altera. Colunas: `id`, `slug`, `nome`, `parent_id`,
`is_bucket`.


O ALGORITMO SAO TRES PASSOS, NESTA ORDEM

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


REGRA 1 -- O `slug` NUNCA MUDA, E ESSE E O PONTO DA TAREFA.

A funcao escreve a coluna `nome`, e SO ela. NAO calcule slug a partir do nome. NAO escreva na coluna
`slug`. NAO normalize, NAO tire acento, NAO troque espaco por hifen, NAO passe para minusculas.

O slug e a identidade da categoria para o resto do sistema, e o `id` tambem nao muda. E por isso que
renomear NAO mexe em vinculo nenhum: tudo que apontava para a categoria continua apontando sozinho,
sem UPDATE nenhum em outra tabela.


REGRA 2 -- O PASSO 1 VEM ANTES DO PASSO 2.

Nome vazio e argumento malformado, e `ValueError` e a resposta certa mesmo que o slug tambem nao
exista. A coluna `nome` e `NOT NULL`, mas `NOT NULL` NAO recusa string vazia -- o banco nao defende
sozinho, e e por isso que a guarda existe.


REGRA 3 -- A FUNCAO DEVOLVE None, e NAO CHAMA `commit`, `rollback`, `BEGIN`, `close` nem `PRAGMA`.


REGRA 4 -- NENHUMA LISTA, DICIONARIO OU CONSTANTE NO NIVEL DO MODULO.


O QUE NAO PODE MUDAR

NAO altere `apagar_categoria` nem `mover_categoria` nem os imports do topo. As duas voltam
inteiras e identicas.

NAO faca `CREATE TABLE`, `ALTER TABLE` nem `CREATE INDEX`.

NAO escreva nada sobre `produtos`, `ncm_ancora`, bucket, lapide, classificacao ou seed.

NAO altere nenhum outro arquivo: nem `banco.py`, nem `migracoes.py`, nem `categorizacao.py`, nem
`seed.py`, nem teste nenhum.

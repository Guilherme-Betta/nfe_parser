Crie o arquivo NOVO `src/nfe_parser/seed.py` com UMA funcao:

```python
def carregar_categorias(conexao, categorias):
    ...
```

`categorias` e uma LISTA DE DICIONARIOS. Cada um tem `slug` e `nome` sempre, e pode ter `parent` (o
slug do pai) e `is_bucket` (booleano). Exemplo:

```python
[
    {"slug": "mercado", "nome": "Mercado"},
    {"slug": "mercado-frutas", "nome": "Frutas", "parent": "mercado"},
    {"slug": "uncategorized", "nome": "Nao Classificado", "is_bucket": True},
]
```

A tabela ja existe (migracao v1) e NAO se altera:

```sql
CREATE TABLE categorias (
  id INTEGER PRIMARY KEY,
  slug TEXT NOT NULL UNIQUE,
  nome TEXT NOT NULL,
  parent_id INTEGER REFERENCES categorias(id),
  is_bucket INTEGER NOT NULL DEFAULT 0
);
```


O ALGORITMO SAO TRES PASSOS, NESTA ORDEM

PASSO 1 -- percorra a lista inteira e grave cada categoria, exatamente assim:

```python
conexao.execute(
    """
    INSERT INTO categorias (slug, nome, is_bucket) VALUES (?, ?, ?)
    ON CONFLICT(slug) DO UPDATE SET nome = excluded.nome, is_bucket = excluded.is_bucket
    """,
    (cat["slug"], cat["nome"], 1 if cat.get("is_bucket") else 0),
)
```

PASSO 2 -- percorra a lista OUTRA VEZ, agora so para ligar os pais. Para cada categoria que tenha
`parent`:

```python
pai = conexao.execute("SELECT id FROM categorias WHERE slug = ?", (pai_slug,)).fetchone()
if pai is None:
    raise LookupError(
        f"a categoria {cat['slug']} aponta para o pai {pai_slug}, que nao esta no seed"
    )
conexao.execute("UPDATE categorias SET parent_id = ? WHERE slug = ?", (pai[0], cat["slug"]))
```

Quem NAO tem `parent` e pulado. Use `cat.get("parent")`.

PASSO 3 -- ao final, confira o bucket:

```python
quantos = conexao.execute("SELECT COUNT(*) FROM categorias WHERE is_bucket = 1").fetchone()[0]
if quantos != 1:
    raise ValueError(
        f"o banco ficou com {quantos} categorias is_bucket = 1; tem de haver exatamente uma"
    )
```


REGRA 1 -- SAO DUAS PASSADAS SEPARADAS, E ISSO E O CORACAO DA TAREFA.

O filho pode aparecer na lista ANTES do pai. Se voce resolver o `parent` na mesma passada que
insere, o pai ainda nao existe e a ligacao sai NULL em silencio. Por isso o passo 2 e um `for`
proprio, que comeca depois de o primeiro `for` ter terminado.

⛔ NAO junte os dois `for` em um so. ⛔ NAO ordene a lista para pais virem primeiro.


REGRA 2 -- O `ON CONFLICT(slug) DO UPDATE` E OBRIGATORIO.

Rodar a funcao duas vezes com a mesma lista tem de deixar a mesma quantidade de linhas, e o `id` de
cada slug tem de ser o MESMO da primeira vez.

⛔ NAO use `INSERT OR IGNORE` (ele nunca atualiza o nome). ⛔ NAO use `INSERT OR REPLACE` e ⛔ NAO
apague nada: os dois trocam o `id`, e ha outra tabela apontando para ele.


REGRA 3 -- O PASSO 3 CONFERE O BANCO, NAO A LISTA.

Conte com `SELECT COUNT(*)` no banco, depois de gravar. ⛔ NAO conte quantos `is_bucket` vieram na
lista recebida: duas listas carregadas em sequencia, cada uma com o seu bucket, deixariam o banco com
dois e a contagem da lista diria 1.


REGRA 4 -- ⛔ NAO CHAME `conexao.commit()`, `rollback`, `BEGIN`, `close` nem `PRAGMA`.

Quem abriu a transacao e que a fecha.


REGRA 5 -- ⛔ NENHUMA LISTA OU DICIONARIO NO NIVEL DO MODULO.

O arquivo e imports + funcoes, e nesta tarefa ele nao precisa de import nenhum. ⛔ Nada de
`CATEGORIAS = [...]`, nada de constante de configuracao, nada de dado embutido. Os dados chegam pelo
parametro, sempre. A proxima tarefa acrescenta uma funcao depois da ultima linha do arquivo.


O QUE NAO PODE MUDAR

⛔ NAO faca `CREATE TABLE`, `ALTER TABLE` nem `CREATE INDEX`. O esquema ja esta pronto.

⛔ NAO abra arquivo, NAO importe `json`, `pathlib` nem `os`. Esta funcao nao le disco.

⛔ NAO escreva nada sobre `ncm_ancora`, `produtos` ou classificacao. E a proxima tarefa, ou outra
story.

⛔ NAO altere nenhum outro arquivo: nem `banco.py`, nem `migracoes.py`, nem `categorizacao.py`, nem
teste nenhum.

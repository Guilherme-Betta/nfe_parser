Acrescente ao arquivo `src/nfe_parser/seed.py` UMA funcao nova:

```python
def carregar_ncm_ancora(conexao, ancoras):
    ...
```

⛔ A funcao `carregar_categorias`, que ja esta nesse arquivo, NAO se altera. Mantenha-a inteira,
palavra por palavra, e ponha a funcao nova DEPOIS dela.

`ancoras` e uma LISTA DE DICIONARIOS. Cada um tem `prefixo` (texto) e `categoria` (o SLUG da
categoria, nao o id). Exemplo:

```python
[
    {"prefixo": "08", "categoria": "mercado-frutas"},
    {"prefixo": "0403", "categoria": "mercado-laticinios"},
]
```

A tabela ja existe (migracao v1) e NAO se altera:

```sql
CREATE TABLE ncm_ancora (
  prefixo TEXT PRIMARY KEY,
  categoria_id INTEGER NOT NULL REFERENCES categorias(id)
);
```


O ALGORITMO -- UM `for` SO, E DENTRO DELE TRES PASSOS NESTA ORDEM

PASSO 1 -- confira a largura do prefixo ANTES de qualquer consulta:

```python
if len(prefixo) not in (2, 4, 8):
    raise ValueError(
        f"o prefixo NCM {prefixo} tem {len(prefixo)} digitos; so 2, 4 ou 8 casam com a busca"
    )
```

PASSO 2 -- resolva o slug:

```python
linha = conexao.execute("SELECT id FROM categorias WHERE slug = ?", (slug,)).fetchone()
if linha is None:
    raise LookupError(
        f"o prefixo {prefixo} aponta para a categoria {slug}, que nao esta no seed"
    )
```

PASSO 3 -- grave:

```python
conexao.execute(
    """
    INSERT INTO ncm_ancora (prefixo, categoria_id) VALUES (?, ?)
    ON CONFLICT(prefixo) DO UPDATE SET categoria_id = excluded.categoria_id
    """,
    (prefixo, linha[0]),
)
```


REGRA 1 -- A LARGURA 2, 4 OU 8 E O CORACAO DA TAREFA.

Quem le esta tabela consulta exatamente tres fatias do NCM do item: os 8 primeiros digitos, os 4
primeiros e os 2 primeiros. Um prefixo de 5 ou de 6 digitos NUNCA casaria com nada: ficaria gravado,
parecendo mapeamento, sem jamais classificar produto nenhum. Recusar na entrada e o unico jeito de
esse erro ter sintoma.

⛔ NAO aceite outras larguras. ⛔ NAO corte nem complete o prefixo para caber numa delas.


REGRA 2 -- O SLUG INEXISTENTE LEVANTA `LookupError`, E A MENSAGEM CITA OS DOIS NOMES.

Se voce deixar o `SELECT` devolver `None` e passar adiante, o `INSERT` quebra sozinho no `NOT NULL`
da coluna -- mas a mensagem do SQLite nao diz QUAL prefixo nem QUAL slug, e a lista tem dezenas de
linhas.

⛔ NAO use subconsulta no `INSERT` (nada de `VALUES (?, (SELECT id FROM categorias ...))`). Resolva
antes, em Python, para poder levantar com os dois nomes na mensagem.


REGRA 3 -- O `ON CONFLICT(prefixo) DO UPDATE` E OBRIGATORIO.

Rodar duas vezes com a mesma lista tem de deixar a mesma quantidade de linhas. E o mesmo prefixo
apontando para outro slug tem de REAPONTAR, nao duplicar nem recusar.

⛔ NAO use `INSERT OR IGNORE` nem `INSERT OR REPLACE`. ⛔ NAO apague linha nenhuma.


REGRA 4 -- ⛔ NAO CHAME `conexao.commit()`, `rollback`, `BEGIN`, `close` nem `PRAGMA`.


REGRA 5 -- ⛔ NENHUMA LISTA OU DICIONARIO NO NIVEL DO MODULO.

O arquivo continua sendo so funcoes. ⛔ Nada de `ANCORAS = [...]`, nada de mapa de NCM embutido no
codigo. Os dados chegam pelo parametro, sempre.


O QUE NAO PODE MUDAR

⛔ NAO faca `CREATE TABLE`, `ALTER TABLE` nem `CREATE INDEX`.

⛔ NAO abra arquivo, NAO importe `json`, `pathlib` nem `os`.

⛔ NAO mexa em `produtos`, nem escreva logica de classificacao: quem casa o NCM do item com esta
tabela e outro modulo, que ja existe.

⛔ NAO altere nenhum outro arquivo: nem `banco.py`, nem `migracoes.py`, nem `categorizacao.py`, nem
teste nenhum.

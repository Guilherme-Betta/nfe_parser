Crie o arquivo NOVO `src/nfe_parser/categorizacao.py` com UMA funcao:

```python
def buscar_categoria_por_ncm(conexao, ncm):
    ...
```

Ela devolve o `categoria_id` (inteiro) que o mapa curado da aquele codigo NCM, pelo prefixo MAIS
LONGO que casar. Devolve `None` quando nada casa.

A tabela ja existe (migracao v1) e NAO se altera:

```sql
CREATE TABLE ncm_ancora (
  prefixo TEXT PRIMARY KEY,                 -- 2, 4 ou 8 digitos
  categoria_id INTEGER NOT NULL REFERENCES categorias(id)
);
```


O ALGORITMO, NESTA ORDEM

1. Se `ncm` for vazio ou `None`, devolva `None` IMEDIATAMENTE, sem consultar o banco.
2. Faca UMA consulta, exatamente esta:

```python
cursor = conexao.execute(
    """
    SELECT categoria_id FROM ncm_ancora
    WHERE prefixo IN (?, ?, ?)
    ORDER BY LENGTH(prefixo) DESC
    LIMIT 1
    """,
    (ncm[:8], ncm[:4], ncm[:2]),
)
```

3. `fetchone()`. Se veio linha, devolva a coluna 0. Se veio `None`, devolva `None`.


REGRA 1 -- O `ORDER BY LENGTH(prefixo) DESC` E O CORACAO DA TAREFA.

O mapa tem prefixos de larguras diferentes: `04` diz "Mercado" e `0403` diz "Laticinios". Os dois
casam o NCM `04039000`, e a resposta certa e a mais especifica. Sem o `ORDER BY`, o SQLite devolve
qualquer uma das linhas que casam.

⛔ Nao ordene por `prefixo` (isso e ordem alfabetica). Ordene por `LENGTH(prefixo)`.
⛔ Nao use `LIKE`. Nao monte a consulta com f-string.


REGRA 2 -- NCM VAZIO DEVOLVE `None`, E NAO LEVANTA.

Item sem NCM e caso NORMAL em NFC-e, nao erro. O `if not ncm: return None` PRECISA vir antes das
fatias: `None[:8]` levanta `TypeError`, e em SQL `WHERE prefixo = NULL` nao casa com nada -- a
consulta responderia "nao achei" pelo motivo errado, em silencio.


REGRA 3 -- NCM MAIS CURTO QUE 8 DIGITOS FUNCIONA SOZINHO.

Com `ncm = "0403"`, `ncm[:8]` e `ncm[:4]` dao os dois `"0403"`. Prefixo repetido no `IN` nao
atrapalha: o `IN` e um conjunto. ⛔ NAO escreva codigo para remover repetidos, e ⛔ NAO trate o
comprimento do `ncm` com `if`.


REGRA 4 -- ⛔ NAO CHAME `conexao.commit()`, `rollback`, `BEGIN`, `close` nem `PRAGMA`.

Esta funcao so LE. Quem abriu a transacao e que a fecha.


REGRA 5 -- ⛔ NENHUMA LISTA OU DICIONARIO NO NIVEL DO MODULO.

O arquivo e imports + funcoes. Nada de `REGRAS = [...]` nem constante de configuracao. As proximas
tarefas acrescentam funcoes depois da ultima linha dele.


O QUE NAO PODE MUDAR

⛔ NAO faca `CREATE TABLE`, `ALTER TABLE` nem `CREATE INDEX`. O esquema ja esta pronto.

⛔ NAO escreva nada sobre `produtos`, `categorias`, bucket, memoria ou classificacao. Esta tarefa so
le `ncm_ancora`; a cascata e a proxima tarefa.

⛔ NAO altere nenhum outro arquivo: nem `banco.py`, nem `migracoes.py`, nem `produtos.py`, nem teste
nenhum.

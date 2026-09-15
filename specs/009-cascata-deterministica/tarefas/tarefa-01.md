Crie o arquivo NOVO `src/nfe_parser/categorizacao.py` com UMA funcao:

```python
def buscar_categoria_por_ncm(conexao, ncm):
    ...
```

Ela devolve o `categoria_id` (inteiro) que o mapa curado da aquele codigo NCM, pelo prefixo MAIS
LONGO que casar. Devolve `None` quando nada casa.


A TABELA JA EXISTE. Foi criada pela migracao v1 e NAO se altera:

```sql
CREATE TABLE ncm_ancora (
  prefixo TEXT PRIMARY KEY,                 -- 2, 4 ou 8 digitos
  categoria_id INTEGER NOT NULL REFERENCES categorias(id)
);
```


O ALGORITMO, NESTA ORDEM

1. Se `ncm` for vazio ou `None`, devolva `None` IMEDIATAMENTE, sem consultar o banco.
2. Monte os tres candidatos a prefixo: `ncm[:8]`, `ncm[:4]` e `ncm[:2]`.
3. Faca UMA consulta que pega o prefixo mais longo entre os que existem na tabela:

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

4. `fetchone()`. Se veio linha, devolva a coluna 0. Se veio `None`, devolva `None`.


REGRA 1 -- O `ORDER BY LENGTH(prefixo) DESC` E O CORACAO DA TAREFA.

O mapa curado tem prefixos de larguras diferentes apontando para niveis diferentes da taxonomia:
`04` diz "Mercado" e `0403` diz "Mercado > Laticinios". Os DOIS casam o NCM `04031000`, e a
resposta certa e a do `0403` -- a mais especifica.

Sem o `ORDER BY`, o SQLite devolve qualquer uma das linhas que casam, e o resultado fica
imprevisivel. Ha teste que poe prefixo de 8, de 4 e de 2 casando ao mesmo tempo e exige o de 8.

⛔ Nao ordene por `prefixo` (isso e ordem alfabetica). Ordene por `LENGTH(prefixo)`.

⛔ Nao use `LIKE`. Nao monte a consulta com f-string. Use os tres `?` como esta acima.


REGRA 2 -- NCM VAZIO DEVOLVE `None`, E NAO LEVANTA.

Item sem NCM e caso NORMAL e comum em NFC-e. Nao e erro de ninguem: e so um produto que o mapa
deterministico nao alcanca, e quem chama ja sabe o que fazer com `None`.

O `if not ncm: return None` tambem PRECISA vir antes das fatias, por dois motivos:

- `None[:8]` levanta `TypeError`.
- Em SQL, `WHERE prefixo = NULL` nao casa com nada -- nem com uma linha que tenha NULL ali.
  A consulta responderia "nao achei" pelo motivo errado, em silencio.

Ha teste chamando com `""` e com `None`.


REGRA 3 -- NCM MAIS CURTO QUE 8 DIGITOS FUNCIONA SOZINHO.

Se `ncm` for `"0403"`, entao `ncm[:8]` e `ncm[:4]` dao os dois `"0403"`, e `ncm[:2]` da `"04"`.
Prefixo repetido na lista do `IN` nao atrapalha: o `IN` e um conjunto. NAO escreva codigo para
remover repetidos, e NAO trate o comprimento do `ncm` com `if`.


REGRA 4 -- ⛔ NAO CHAME `conexao.commit()`.

Quem abriu a transacao e que a fecha. Esta funcao so LE; nao escreve nada.

⛔ Tambem nao chame `rollback`, `BEGIN`, `close` nem `execute("PRAGMA ...")`.


REGRA 5 -- ⛔ NENHUMA LISTA OU DICIONARIO NO NIVEL DO MODULO.

O arquivo deve conter os imports (se precisar de algum) e a funcao. Nada de `REGRAS = [...]`,
`CASCATA = {...}` nem constante de configuracao. As proximas tarefas acrescentam funcoes a este
mesmo arquivo, e elas vao depois da ultima linha dele.


O QUE NAO PODE MUDAR

NAO faca `CREATE TABLE`, `ALTER TABLE` nem `CREATE INDEX`. O esquema ja esta pronto.

NAO escreva nada sobre `produtos`, `categorias`, bucket, memoria ou classificacao. Esta tarefa so
le `ncm_ancora`. A cascata e a proxima tarefa.

NAO altere nenhum outro arquivo: nem `banco.py`, nem `migracoes.py`, nem `produtos.py`, nem teste
nenhum.

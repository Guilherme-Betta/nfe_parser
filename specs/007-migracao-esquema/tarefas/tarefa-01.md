Crie o arquivo `src/nfe_parser/migracoes.py` (ele ainda NAO existe) e acrescente UMA linha em
`src/nfe_parser/banco.py`.

O modulo poe o banco sob controle de versao usando o `PRAGMA user_version` do SQLite. Nesta tarefa
voce escreve SO O MECANISMO: nenhuma tabela, nenhum DDL, nenhum dado.

```python
MIGRACOES = []


def versao_do_banco(conexao) -> int:
    ...


def aplicar_migracoes(conexao, migracoes=None) -> int:
    ...
```

`MIGRACOES` e uma LISTA DE FUNCOES, e A POSICAO E A VERSAO: indice 0 e a migracao versao 1,
indice 1 e a versao 2. Nesta tarefa ela fica VAZIA.

`versao_do_banco` le o `PRAGMA user_version` e devolve o inteiro. Banco novo devolve 0.

`aplicar_migracoes` roda, em ordem crescente, so as migracoes cuja versao e MAIOR que a versao
atual do banco, e devolve a versao final. `migracoes=None` significa usar `MIGRACOES`. O parametro
existe para o teste injetar uma lista propria -- mantenha-o.


REGRA 1 -- O PRAGMA NAO ACEITA PARAMETRO LIGADO. E o que mais quebra aqui.

    conexao.execute("PRAGMA user_version = ?", (versao,))
    -> sqlite3.OperationalError: near "?": syntax error

Foi medido. O numero tem de ser interpolado:

```python
conexao.execute(f"PRAGMA user_version = {versao}")
```

Escreva assim mesmo. Nao ha risco de SQL injection: `versao` e um `int` calculado dentro desta
funcao a partir da posicao na lista, nunca vem de fora. Para LER, `execute` normal serve:
`conexao.execute("PRAGMA user_version").fetchone()[0]`.


REGRA 2 -- CADA MIGRACAO E ATOMICA, E A VERSAO ENTRA DENTRO DA TRANSACAO.

Se a versao avancasse sem a migracao ter terminado, a proxima abertura pularia aquela migracao e o
banco ficaria quebrado para sempre, sem sintoma. Repare no `PRAGMA` DENTRO do bloco:

```python
for indice, migracao in enumerate(migracoes):
    versao = indice + 1
    if versao <= atual:
        continue
    conexao.execute("BEGIN")
    try:
        migracao(conexao)
        conexao.execute(f"PRAGMA user_version = {versao}")
        conexao.execute("COMMIT")
    except Exception:
        conexao.execute("ROLLBACK")
        raise
```

A excecao SOBE. Nao engula, nao logue, nao devolva codigo de erro.

DDL do SQLite obedece transacao: um `CREATE TABLE` feito dentro do `BEGIN` desaparece no
`ROLLBACK`, e o `user_version` volta junto. Foi medido, e ha teste para isso.


REGRA 3 -- E PROIBIDO `executescript` DENTRO DE UMA MIGRACAO.

Ele faz COMMIT IMPLICITO antes de rodar: destroi a transacao acima, o `ROLLBACK` explode com
"cannot rollback - no transaction is active", e o que ja rodou fica gravado. Foi medido. Use
`conexao.execute(...)`, um comando por chamada.

Voce vai ver `executescript` em `criar_esquema`, no `banco.py`. La esta certo -- nao ha transacao
envolvida. Dentro de migracao, nao.


A UNICA MUDANCA EM `banco.py` -- `abrir_banco` ganha uma linha:

```python
def abrir_banco(caminho):
    conexao = sqlite3.connect(caminho)
    conexao.execute("PRAGMA foreign_keys = ON")
    criar_esquema(conexao)
    aplicar_migracoes(conexao)
    return conexao
```

Mais o `import` de `aplicar_migracoes` no topo.

A ORDEM IMPORTA: `criar_esquema` ANTES. Uma migracao futura altera a tabela `itens`, e num banco
novo ela so existe depois de `criar_esquema` rodar. Invertido, a primeira abertura quebraria.

NAO altere `criar_esquema` -- nem o DDL, nem os nomes, nem a docstring. Ele esta correto e ja
coberto por testes que passam.

NAO faca mais nada: nenhum CREATE TABLE, nenhum ALTER TABLE, nenhuma migracao concreta, nenhum
dado. `MIGRACOES` fica `[]`. NAO altere nenhum outro arquivo.

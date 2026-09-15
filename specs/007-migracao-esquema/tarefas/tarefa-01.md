O arquivo `src/nfe_parser/migracoes.py` ja existe e esta QUASE certo. Ha UM defeito nele.

DEFEITO: a ultima linha de `aplicar_migracoes` e `return versao`.

`versao` e a variavel do `for`. Quando a lista de migracoes esta vazia -- que e o caso agora,
porque `MIGRACOES = []` -- o corpo do laco nunca roda, `versao` nunca chega a existir, e a funcao
levanta `NameError: name 'versao' is not defined`.

Troque essa linha por uma leitura do banco:

```python
    return versao_do_banco(conexao)
```

Essa e a UNICA mudanca em `migracoes.py`. O resto do arquivo esta correto. NAO mexa no laco, no
`BEGIN`/`COMMIT`/`ROLLBACK`, no `raise`, no `PRAGMA` interpolado nem na assinatura da funcao.


AGORA O `src/nfe_parser/banco.py`. Ele esta como no comeco: falta a ligacao inteira.

Sao duas mudancas, e so estas duas.

1. No topo do arquivo, logo depois de `import sqlite3`:

```python
from nfe_parser.migracoes import aplicar_migracoes
```

Sem este import a chamada abaixo levanta `NameError: name 'aplicar_migracoes' is not defined`.

2. Dentro de `abrir_banco`, UMA chamada -- exatamente uma, nao duas, nao tres -- entre
`criar_esquema` e o `return`:

```python
def abrir_banco(caminho):
    conexao = sqlite3.connect(caminho)
    conexao.execute("PRAGMA foreign_keys = ON")
    criar_esquema(conexao)
    aplicar_migracoes(conexao)
    return conexao
```

A ordem importa: `criar_esquema` ANTES. Uma migracao futura altera a tabela `itens`, e num banco
novo ela so existe depois de `criar_esquema` rodar.


NAO altere `criar_esquema` -- nem o DDL, nem os nomes, nem a docstring.

NAO acrescente migracao nenhuma: `MIGRACOES` continua `[]`. Nenhum CREATE TABLE, nenhum
ALTER TABLE, nenhum dado.

NAO altere nenhum outro arquivo.

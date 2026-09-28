O arquivo `src/nfe_parser/varredura.py` JA EXISTE e tem UM import e UMA funcao,
`classificar_produtos_pendentes`.

Voce vai devolver o arquivo INTEIRO. Sao TRES mudancas nele, e mais nada.


MUDANCA 1 -- TROQUE O IMPORT

A linha de import hoje e:

```python
from nfe_parser.categorizacao import classificar_produto
```

Ela passa a ser:

```python
from nfe_parser.classificacao_llm import classificar_produto_com_llm
```

`classificar_produto_com_llm(conexao, produto_id, ncm, llm=None)` JA EXISTE e voce NAO a escreve.
Voce so a CHAMA.


MUDANCA 2 -- A FUNCAO GANHA UM PARAMETRO

```python
def classificar_produtos_pendentes(conexao, llm=None) -> int:
```

O padrao e `None`. NAO mude o nome da funcao. NAO mude o tipo de retorno.


MUDANCA 3 -- TROQUE A CHAMADA DENTRO DO LACO

A linha hoje e:

```python
        classificar_produto(conexao, produto_id, ncm)
```

Ela passa a ser:

```python
        classificar_produto_com_llm(conexao, produto_id, ncm, llm)
```


O QUE NAO PODE MUDAR -- TUDO O RESTO VOLTA IDENTICO

A docstring do MODULO, no topo do arquivo, volta INTEIRA, palavra por palavra.

A docstring de `classificar_produtos_pendentes` volta INTEIRA, palavra por palavra.

As consultas SQL nao mudam: `WHERE origem IS NULL`, o `.fetchall()`, o `ORDER BY id DESC LIMIT 1`.

A contagem nao muda: `resgatados` comeca em `0`, soma `1` quando a `origem` relida `is not None`, e
e devolvida no fim. NAO compare a `origem` com nenhuma string.

NAO chame `commit`, `rollback` nem `BEGIN`. NAO ponha `try`/`except`. NAO acrescente import.

NAO altere nenhum outro arquivo do projeto, e NAO altere teste nenhum. O unico arquivo que voce
escreve e `src/nfe_parser/varredura.py`. Se qualquer outro arquivo aparecer nesta conversa, DEIXE-O
EXATAMENTE COMO ESTA.

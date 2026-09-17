O arquivo `src/nfe_parser/importador.py` JA EXISTE e ja tem TRES funcoes, nesta ordem:
`_processar_arquivo`, `_processar_evento` e `importar`.

Voce devolve o arquivo INTEIRO, com as tres funcoes, na mesma ordem. Sao QUATRO mudancas, e mais
nada. Os cinco imports do topo voltam como estao: NAO acrescente nem tire import nenhum.


MUDANCA 1 -- `_processar_arquivo` recebe `texto` e `classificacao` prontos

Assinatura nova:

```python
def _processar_arquivo(conexao, importacao_id, nome, conteudo_bytes, texto, classificacao) -> None:
```

APAGUE de dentro dela estas duas linhas, que refazem trabalho ja feito:

```python
    texto = conteudo_bytes.decode("utf-8", errors="replace")
    classificacao = classificar_xml(texto)
```

A linha do `arquivo_hash` CONTINUA e continua usando `conteudo_bytes`: o hash e do arquivo, nao do
texto.


MUDANCA 2 -- em `_processar_arquivo`, o `try` cobre SO a extracao

Troque o bloco do ramo `"nfe"` por este, exatamente assim:

```python
    if classificacao == "nfe":
        try:
            extraido = extrair_nota(texto)
        except ValueError as e:
            resultado = "invalida"
            detalhe = str(e)
        else:
            resultado = persistir_nota(conexao, extraido, importacao_id)
            chave = extraido["nota"]["chave"]
```

Os `elif` abaixo NAO mudam. O INSERT em `importacao_arquivos` no fim da funcao NAO muda.


MUDANCA 3 -- `_processar_evento` recebe `texto` pronto, e ganha o mesmo `else`

Assinatura nova:

```python
def _processar_evento(conexao, importacao_id, nome, conteudo_bytes, texto) -> None:
```

APAGUE a linha `texto = conteudo_bytes.decode("utf-8", errors="replace")` de dentro dela, e troque o
`try`/`except` dela por este:

```python
    try:
        evento = extrair_evento(texto)
    except ValueError as e:
        resultado = "invalida"
        detalhe = str(e)
    else:
        resultado = aplicar_cancelamento(conexao, evento)
        chave = evento["ch_nfe"]
```

A docstring da funcao e o comentario que explica o `except` voltam inteiros, palavra por palavra.


MUDANCA 4 -- em `importar`: guarde o que ja foi calculado, e commite no fim

(a) Troque os dois blocos que montam `notas` e `eventos` por estes:

```python
    if caminho.suffix.lower() == ".zip":
        with zipfile.ZipFile(caminho, "r") as arquivo_zip:
            for membro in arquivo_zip.namelist():
                if not membro.lower().endswith(".xml") or membro.endswith("/"):
                    continue
                bytes_content = arquivo_zip.read(membro)
                texto = bytes_content.decode("utf-8", errors="replace")
                classificacao = classificar_xml(texto)
                if classificacao == "evento":
                    eventos.append((membro, bytes_content, texto))
                else:
                    notas.append((membro, bytes_content, texto, classificacao))
    else:
        bytes_content = caminho.read_bytes()
        texto = bytes_content.decode("utf-8", errors="replace")
        classificacao = classificar_xml(texto)
        if classificacao == "evento":
            eventos.append((caminho.name, bytes_content, texto))
        else:
            notas.append((caminho.name, bytes_content, texto, classificacao))
```

Tupla de `notas`: QUATRO elementos. Tupla de `eventos`: TRES.

(b) Troque os dois lacos das passadas por estes, mantendo os comentarios que ja estao acima deles:

```python
    for nome, conteudo_bytes, texto, classificacao in notas:
        _processar_arquivo(conexao, importacao_id, nome, conteudo_bytes, texto, classificacao)

    for nome, conteudo_bytes, texto in eventos:
        _processar_evento(conexao, importacao_id, nome, conteudo_bytes, texto)
```

(c) DEPOIS do UPDATE em `importacoes` e ANTES do `return importacao_id`, acrescente uma linha:

```python
    conexao.commit()
```


REGRA 1 -- O `else` DO `try` E O PONTO DA TAREFA.

`persistir_nota` e `aplicar_cancelamento` ficam FORA do `try`. Se uma delas levantar, o erro SOBE e
derruba a importacao. Erro de gravacao NAO e "XML invalido", e registra-lo como invalido esconderia o
defeito. NAO use variavel de controle, NAO use `if extraido is not None`, NAO ponha um segundo `try`.

REGRA 2 -- `classificar_xml` e chamada UMA vez por arquivo, e so dentro de `importar`.

REGRA 3 -- O `commit` e UM SO, no fim, FORA de qualquer laco. NAO commite dentro dos lacos nem antes
do UPDATE. Um lote e tudo ou nada.

REGRA 4 -- NAO acrescente `rollback` nem `try`/`except` em volta de `importar`.

REGRA 5 -- Nenhuma lista, dicionario ou constante nova no nivel do modulo.


O QUE NAO PODE MUDAR

O UPDATE em `importacoes` volta INTEIRO, com as sete subconsultas de contagem e a tupla de oito
parametros, exatamente como esta hoje. Ele e longo: copie-o inteiro, sem encurtar.

O INSERT em `importacao_arquivos` e igual nas duas funcoes e NAO muda.

`importar` continua com a assinatura `(conexao, caminho, origem: str | None = None) -> int` e
continua devolvendo `importacao_id`. A ordem das passadas nao muda: primeiro TODAS as notas, depois
TODOS os eventos.

NAO faca `CREATE TABLE`, `ALTER TABLE` nem `CREATE INDEX`. NAO escreva nada sobre produto, categoria
ou cascata.

NAO altere nenhum outro arquivo do projeto, e NAO altere teste nenhum. O unico arquivo que voce
escreve e `src/nfe_parser/importador.py`. Se qualquer outro arquivo aparecer nesta conversa,
DEIXE-O EXATAMENTE COMO ESTA.

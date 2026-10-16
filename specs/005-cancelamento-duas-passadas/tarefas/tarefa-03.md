O arquivo `src/nfe_parser/importador.py` esta quase pronto. Falta UMA coisa, e e so isso que voce
vai fazer.

A funcao `importar` ja chama `_processar_evento` na linha da segunda passada, mas essa funcao NAO
EXISTE no arquivo. O teste falha com:

    NameError: name '_processar_evento' is not defined

SUA TAREFA: acrescentar a funcao `_processar_evento` ao arquivo.

⛔ NAO altere a funcao `importar`. Ela ja esta correta.
⛔ NAO altere a funcao `_processar_arquivo`. Ela ja esta correta.
⛔ NAO altere nenhum outro arquivo.

Insira a funcao abaixo ENTRE o fim de `_processar_arquivo` e o comeco de `def importar(`, exatamente
como esta escrita aqui:

```python
def _processar_evento(conexao, importacao_id, nome, conteudo_bytes) -> None:
    arquivo_hash = hashlib.sha256(conteudo_bytes).hexdigest()
    texto = conteudo_bytes.decode("utf-8", errors="replace")
    chave = None
    detalhe = None
    try:
        evento = extrair_evento(texto)
        resultado = aplicar_cancelamento(conexao, evento)
        chave = evento["ch_nfe"]
    except ValueError as e:
        resultado = "invalida"
        detalhe = str(e)

    conexao.execute(
        "INSERT INTO importacao_arquivos (importacao_id, arquivo, arquivo_hash, chave, resultado, detalhe) VALUES (?, ?, ?, ?, ?, ?)",
        (importacao_id, nome, arquivo_hash, chave, resultado, detalhe),
    )
```

O import de que ela precisa JA ESTA no topo do arquivo, na linha
`from nfe_parser.cancelamento import aplicar_cancelamento, extrair_evento`. Nao repita esse import.

OBSERVACAO SOBRE A EDICAO: o bloco SEARCH da sua ultima tentativa nao casou com o arquivo, e por
isso a funcao nunca chegou a ser criada. Para acrescentar uma funcao nova, ancore o SEARCH em
linhas CONTIGUAS que existam de verdade no arquivo — por exemplo as duas ultimas linhas de
`_processar_arquivo`:

```
        (importacao_id, nome, arquivo_hash, chave, resultado, detalhe),
    )
```

e repita essas mesmas linhas no inicio do REPLACE, seguidas da funcao nova.

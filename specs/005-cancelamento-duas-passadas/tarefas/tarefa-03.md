Altere `src/nfe_parser/importador.py` para processar o lote em DUAS PASSADAS.

O PROBLEMA: hoje `importar` varre o `.zip` uma vez so. Quando o arquivo do evento de cancelamento
aparece ANTES da nota que ele cancela, a nota ainda nao esta no banco, e o evento nao tem como ser
aplicado. Por isso o codigo atual registra todo evento como `"cancelamento_orfao"`.

A REGRA MAIS IMPORTANTE DESTA TAREFA, E A UNICA QUE PRECISA DE ATENCAO:

    CADA ARQUIVO E PROCESSADO UMA VEZ SO, E GERA UMA UNICA LINHA DE LOG.

As duas passadas percorrem DUAS LISTAS DIFERENTES. Elas NAO percorrem a mesma lista duas vezes.
A primeira lista tem as notas e o resto; a segunda lista tem SO os eventos. Um arquivo esta numa
lista ou na outra, nunca nas duas.

Se voce percorrer a mesma lista nas duas passadas, cada arquivo vira DUAS linhas em
`importacao_arquivos` e as notas passam pelo tratamento de evento. O banco recusa isso com um erro
de `CHECK constraint failed` ou `NOT NULL constraint failed` na coluna `resultado`.

ESCREVA `importar` COM ESTA ESTRUTURA:

```python
    notas = []
    eventos = []

    # colete os membros (o .zip e o .xml avulso desembocam aqui do mesmo jeito),
    # e ja separe cada um na sua lista:
    for nome, conteudo_bytes in <os membros do lote>:
        texto = conteudo_bytes.decode("utf-8", errors="replace")
        if classificar_xml(texto) == "evento":
            eventos.append((nome, conteudo_bytes))
        else:
            notas.append((nome, conteudo_bytes))

    # PRIMEIRA passada -- so a lista `notas`
    for nome, conteudo_bytes in notas:
        _processar_arquivo(conexao, importacao_id, nome, conteudo_bytes)

    # SEGUNDA passada -- so a lista `eventos`, depois de todas as notas estarem no banco
    for nome, conteudo_bytes in eventos:
        _processar_evento(conexao, importacao_id, nome, conteudo_bytes)
```

A FUNCAO `_processar_evento`, QUE VOCE VAI CRIAR:

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

ATENCAO: `chave` e `detalhe` sao inicializados como `None` ANTES do `try`. Se voce so atribuir
`detalhe` dentro do `except`, o caminho de sucesso estoura
`UnboundLocalError: cannot access local variable 'detalhe'`.

O IMPORT QUE FALTA, no topo do arquivo:

```python
from nfe_parser.cancelamento import aplicar_cancelamento, extrair_evento
```

Essas duas funcoes ja existem e ja estao testadas. NAO as altere e NAO altere
`src/nfe_parser/cancelamento.py`. Os contratos delas:

    extrair_evento(xml_texto) -> {"ch_nfe": str|None, "tp_evento": str|None, "dh_evento": str|None}
                                 levanta ValueError quando o XML nao abre
    aplicar_cancelamento(conexao, evento) -> "cancelamento_aplicado" ou "cancelamento_orfao"
                                 ja cuida de chave ausente, nota inexistente e tipo de evento errado

EM `_processar_arquivo`, APAGUE ESTAS DUAS LINHAS:

```python
    elif classificacao == "evento":
        resultado = "cancelamento_orfao"
```

Elas ficaram inalcancaveis: nenhum evento chega mais a essa funcao.

⛔ NAO acrescente um ramo `else` com `resultado = "desconhecido"`, e NAO acrescente nenhuma lista
de valores permitidos antes do INSERT. Esses valores nao existem no banco e o CHECK vai recusa-los.
Se algum `resultado` estiver saindo vazio, a causa e a separacao das listas acima, nao a falta de
uma validacao.

⛔ NAO mexa no `UPDATE importacoes` no fim da funcao. O `cancelamentos_aplicados = 0` continua como
esta — ajustar esse contador e a proxima tarefa, nao esta.

A funcao continua devolvendo o `importacao_id`. NAO altere nenhum outro arquivo.

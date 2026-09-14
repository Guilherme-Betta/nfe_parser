Altere `src/nfe_parser/importador.py` para processar o lote em DUAS PASSADAS.

O PROBLEMA: hoje `importar` varre o `.zip` uma vez so. Quando o arquivo do evento de cancelamento
aparece ANTES da nota que ele cancela, a nota ainda nao esta no banco, e o evento nao tem como ser
aplicado. Por isso o codigo atual registra todo evento como `"cancelamento_orfao"`.

A CORRECAO: varrer duas vezes. A primeira passada persiste as notas. A segunda aplica os eventos,
quando todas as notas do lote ja estao no banco.

O CONTRATO DO MODULO QUE VOCE VAI CHAMAR — ja existe, ja esta testado, nao mexa nele:

```python
from nfe_parser.cancelamento import aplicar_cancelamento, extrair_evento

extrair_evento(xml_texto) -> dict
    # devolve {"ch_nfe": str|None, "tp_evento": str|None, "dh_evento": str|None}
    # levanta ValueError quando o XML nao abre

aplicar_cancelamento(conexao, evento) -> str
    # devolve "cancelamento_aplicado" ou "cancelamento_orfao"
    # ja cuida sozinho de chave ausente, nota inexistente e tipo de evento errado
```

COMO REESTRUTURAR `importar`:

1. Primeiro COLETE os membros numa lista de pares `(nome, conteudo_bytes)`, sem processar nada.
   Isso vale para os dois caminhos que a funcao ja tem: o `.zip` e o `.xml` avulso. Os dois tem de
   desembocar na mesma lista e nas mesmas duas passadas.

2. PRIMEIRA PASSADA: para cada par da lista, classifique com `classificar_xml`. Se a classificacao
   for `"evento"`, guarde o par numa segunda lista e siga para o proximo SEM registrar nada ainda.
   Todo o resto (`"nfe"`, `"nao_suportado_sat"`, `"invalida"`) continua sendo tratado exatamente
   como hoje, pela funcao `_processar_arquivo`.

3. SEGUNDA PASSADA: para cada evento guardado, chame `extrair_evento` e depois
   `aplicar_cancelamento`, e so entao insira a linha em `importacao_arquivos`.

O QUE A LINHA DE LOG DO EVENTO PRECISA TER:

    resultado  ->  o que `aplicar_cancelamento` devolveu
    chave      ->  o `ch_nfe` do evento, ou NULL quando ele for None
    detalhe    ->  NULL

QUANDO `extrair_evento` LEVANTAR `ValueError`: registre esse arquivo com
`resultado = "invalida"` e um `detalhe` com o texto do erro, e SIGA para o proximo evento. Um
evento que nao abre nao pode derrubar o lote. Isto acontece de verdade: um `<procEventoNFe>` sem
namespace passa pelo `classificar_xml` e falha no parser.

O hash do arquivo continua sendo `hashlib.sha256(conteudo_bytes).hexdigest()`, igual ao que
`_processar_arquivo` ja faz.

Sugestao de desenho: crie uma funcao `_processar_evento(conexao, importacao_id, nome,
conteudo_bytes)` espelhando a `_processar_arquivo` que ja existe, e remova de `_processar_arquivo`
o ramo `elif classificacao == "evento"`, que agora nunca sera alcancado por ela.

DUAS COISAS QUE NAO PODEM MUDAR:

- O `UPDATE importacoes` no fim da funcao fica EXATAMENTE como esta, inclusive o
  `cancelamentos_aplicados = 0`. Ajustar esse contador e a proxima tarefa, nao esta.
- A funcao continua devolvendo o `importacao_id`.

NAO altere nenhum outro arquivo.

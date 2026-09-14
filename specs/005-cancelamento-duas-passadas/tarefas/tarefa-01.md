Crie a funcao `extrair_evento` no arquivo `src/nfe_parser/cancelamento.py`.

Ela recebe o texto XML de um evento de cancelamento de NF-e e devolve um dicionario com tres
chaves: `ch_nfe`, `tp_evento` e `dh_evento`.

```python
def extrair_evento(xml_texto: str) -> dict:
    ...
    return {"ch_nfe": ..., "tp_evento": ..., "dh_evento": ...}
```

COMO ABRIR O XML — use exatamente estes dois imports:

```python
from nfelib.nfe_evento_cancel.bindings.v1_0.proc_evento_canc_nfe_v1_00 import ProcEventoNfe
from xsdata.formats.dataclass.parsers import XmlParser
```

E parseie assim:

```python
proc = XmlParser().from_string(xml_texto, ProcEventoNfe)
```

ATENCAO: a classe `ProcEventoNfe` do evento NAO tem o metodo `.from_xml()`. Ela nao herda de
`CommonMixin`, ao contrario da `NfeProc` usada em `extrator.py`. Se voce chamar `.from_xml()` vai
receber `AttributeError`. Use o `XmlParser` acima.

DE ONDE VEM CADA CAMPO:

    proc.evento.infEvento.chNFe     -> ch_nfe
    proc.evento.infEvento.tpEvento  -> tp_evento
    proc.evento.infEvento.dhEvento  -> dh_evento

AS QUATRO REGRAS QUE OS TESTES COBRAM:

1. `tp_evento` tem de sair como `str` ou `None`. NUNCA como objeto de enum.

   Isto e a parte mais facil de errar da tarefa. O xsdata devolve `tpEvento` de duas formas
   diferentes dependendo do valor lido:
     - quando o valor e "110111", vem um objeto de enum, e o texto esta em `.value`
     - quando e qualquer outro valor ("110110", "ABC"), vem a string crua, que NAO tem `.value`

   Ou seja: `inf.tpEvento.value` funciona no caso feliz e estoura `AttributeError` no outro.
   Normalize com `getattr(tp, "value", tp)` ou equivalente.

2. Campo ausente devolve `None`, e a funcao NAO levanta. Vale para `chNFe`, `tpEvento` e
   `dhEvento`.

3. `proc.evento` pode ser `None`, e `proc.evento.infEvento` tambem pode ser `None`, sem que o
   parser levante. Um `<procEventoNFe></procEventoNFe>` vazio precisa devolver os tres campos como
   `None`, nao estourar `AttributeError`.

4. Quando o parser NAO consegue abrir o XML, levante `ValueError`. O parser sinaliza isso
   levantando `ParserError`, que voce importa assim:

   ```python
   from xsdata.exceptions import ParserError
   ```

   Capture o `ParserError` e levante `ValueError` no lugar, como `extrair_nota` ja faz em
   `src/nfe_parser/extrator.py`.

NAO faca mais nada neste arquivo. A funcao `aplicar_cancelamento` e a proxima tarefa, nao esta.
NAO altere nenhum outro arquivo.

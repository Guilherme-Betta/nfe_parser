from datetime import UTC, datetime

from nfelib.nfe_evento_cancel.bindings.v1_0.proc_evento_canc_nfe_v1_00 import ProcEventoNfe
from xsdata.exceptions import ParserError
from xsdata.formats.dataclass.parsers import XmlParser

# O unico `tpEvento` que cancela uma nota. Os outros existem e sao validos --
# `110110` e carta de correcao, por exemplo -- mas nao mudam o status da nota.
TP_EVENTO_CANCELAMENTO = "110111"


def extrair_evento(xml_texto: str) -> dict:
    """Le um evento de cancelamento e devolve seus tres campos uteis.

    Campo ausente vira `None` em vez de excecao: um evento capenga e dado ruim,
    e quem decide o que fazer com ele e `aplicar_cancelamento`. So um XML que
    nao ABRE vira erro.

    ⚠️ `ProcEventoNfe` NAO tem `.from_xml()`, ao contrario da `NfeProc` usada em
    `extrator.py` -- ela nao herda de `CommonMixin`. Por isso o `XmlParser`.
    """

    try:
        proc = XmlParser().from_string(xml_texto, ProcEventoNfe)
    except ParserError:
        raise ValueError("Erro ao parsear o XML")

    evento = proc.evento
    if evento is None:
        return {"ch_nfe": None, "tp_evento": None, "dh_evento": None}

    inf_evento = evento.infEvento
    if inf_evento is None:
        return {"ch_nfe": None, "tp_evento": None, "dh_evento": None}

    # ⚠️ O `getattr(..., "value", ...)` nao e paranoia: o xsdata devolve
    # `tpEvento` como ENUM quando o valor e conhecido (o texto fica em `.value`)
    # e como STRING CRUA para qualquer outro, emitindo so um `ConverterWarning`.
    # Um `.value` direto funciona no caminho feliz e estoura `AttributeError` na
    # primeira carta de correcao que chegar.
    ch_nfe = getattr(inf_evento.chNFe, "value", inf_evento.chNFe)
    tp_evento = getattr(inf_evento.tpEvento, "value", inf_evento.tpEvento)
    dh_evento = getattr(inf_evento.dhEvento, "value", inf_evento.dhEvento)

    return {"ch_nfe": ch_nfe, "tp_evento": tp_evento, "dh_evento": dh_evento}


def aplicar_cancelamento(conexao, evento: dict) -> str:
    """Cancela a nota que o evento aponta. Devolve o `resultado` para o log.

    A regra e uma so: existe nota no banco para esta chave, e este evento e de
    cancelamento? Entao `'cancelamento_aplicado'`. Caso contrario
    `'cancelamento_orfao'`, sem escrever nada.

    ⛔ Um evento orfao NUNCA inventa a nota que falta. Sem nota, nada e escrito.
    """

    ch_nfe = evento.get("ch_nfe")
    tp_evento = evento.get("tp_evento")

    if tp_evento != TP_EVENTO_CANCELAMENTO or ch_nfe is None:
        return "cancelamento_orfao"

    query_check = "SELECT 1 FROM notas WHERE chave = ?"
    if not conexao.execute(query_check, (ch_nfe,)).fetchone():
        return "cancelamento_orfao"

    # ⭐ O `AND status = 'ok'` e o que torna a funcao idempotente: reimportar o
    # mesmo lote nao move o `cancelado_em` da primeira vez. O desfecho continua
    # sendo "aplicado" porque a pergunta que ele responde e "este evento
    # corresponde a uma nota cancelada?", e a resposta e sim nas duas vezes.
    cancelado_em = datetime.now(UTC).isoformat()
    query_update = (
        "UPDATE notas SET status = 'cancelada', cancelado_em = ? WHERE chave = ? AND status = 'ok'"
    )
    conexao.execute(query_update, (cancelado_em, ch_nfe))
    conexao.commit()

    return "cancelamento_aplicado"

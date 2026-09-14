from nfelib.nfe_evento_cancel.bindings.v1_0.proc_evento_canc_nfe_v1_00 import ProcEventoNfe
from xsdata.formats.dataclass.parsers import XmlParser
from xsdata.exceptions import ParserError
from datetime import UTC, datetime

def extrair_evento(xml_texto: str) -> dict:
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

    ch_nfe = getattr(inf_evento.chNFe, "value", inf_evento.chNFe)
    tp_evento = getattr(inf_evento.tpEvento, "value", inf_evento.tpEvento)
    dh_evento = getattr(inf_evento.dhEvento, "value", inf_evento.dhEvento)

    return {"ch_nfe": ch_nfe, "tp_evento": tp_evento, "dh_evento": dh_evento}

def aplicar_cancelamento(conexao, evento: dict) -> str:
    ch_nfe = evento.get("ch_nfe")
    tp_evento = evento.get("tp_evento")

    if tp_evento != "110111" or ch_nfe is None:
        return "cancelamento_orfao"

    query_check = "SELECT 1 FROM notas WHERE chave = ?"
    if not conexao.execute(query_check, (ch_nfe,)).fetchone():
        return "cancelamento_orfao"

    cancelado_em = datetime.now(UTC).isoformat()
    query_update = "UPDATE notas SET status = 'cancelada', cancelado_em = ? WHERE chave = ? AND status = 'ok'"
    conexao.execute(query_update, (cancelado_em, ch_nfe))
    conexao.commit()

    return "cancelamento_aplicado"

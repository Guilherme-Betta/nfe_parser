from nfelib.nfe_evento_cancel.bindings.v1_0.proc_evento_canc_nfe_v1_00 import ProcEventoNfe
from xsdata.formats.dataclass.parsers import XmlParser
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

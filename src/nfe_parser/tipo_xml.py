"""Descobrir que TIPO de documento fiscal um XML e, antes de qualquer parser.

⚠️ Isto roteia o ARQUIVO (nota, evento, SAT, lixo) e nao tem relacao com a
classificacao de PRODUTO em categoria (`categorizacao.py`). O modulo ja se chamou
`classificador.py`, e o nome confundia as duas coisas.
"""

import xml.etree.ElementTree as ET


def tipo_do_xml(xml_texto: str) -> str:
    """Devolve `"nfe"`, `"evento"`, `"nao_suportado_sat"` ou `"invalida"`.

    Olha so a raiz do XML e, para nota, o `<mod>`: 55 (NF-e) e 65 (NFC-e) sao
    notas; qualquer outro modelo e `"invalida"`. A raiz e aceita com ou sem o
    namespace da NF-e na frente.

    ⭐ Nunca levanta: XML que nem abre tambem e `"invalida"`. E o que deixa o
    `importar` tratar um arquivo corrompido como linha no log, e nao como erro.
    """

    try:
        root = ET.fromstring(xml_texto)
    except ET.ParseError:
        return "invalida"

    namespace = "{http://www.portalfiscal.inf.br/nfe}"
    if root.tag == namespace + "nfeProc" or root.tag == "nfeProc":
        for elem in root.iter():
            if elem.tag.split("}")[-1] == "mod":
                if elem.text in ("55", "65"):
                    return "nfe"
                return "invalida"
        return "invalida"
    elif root.tag == namespace + "CFe" or root.tag == "CFe":
        return "nao_suportado_sat"
    elif root.tag == namespace + "procEventoNFe" or root.tag == "procEventoNFe":
        return "evento"
    else:
        return "invalida"

import xml.etree.ElementTree as ET


def classificar_xml(xml_texto: str) -> str:
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

import xml.etree.ElementTree as ET

def classificar_xml(xml_texto: str) -> str:
    try:
        root = ET.fromstring(xml_texto)
    except ET.ParseError:
        return "invalida"

    namespace = "{http://www.portalfiscal.inf.br/nfe}"
    if root.tag == namespace + "nfeProc" or root.tag == "nfeProc":
        for ide in root.findall(".//ide", namespaces={'nfe': namespace}):
            mod = ide.find("nfe:mod", namespaces={'nfe': namespace})
            if mod is not None and mod.text in ["55", "65"]:
                return "nfe"
        return "invalida"
    elif root.tag == namespace + "CFe" or root.tag == "CFe":
        return "nao_suportado_sat"
    elif root.tag == namespace + "procEventoNFe" or root.tag == "procEventoNFe":
        return "evento"
    else:
        return "invalida"

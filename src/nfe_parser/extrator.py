from decimal import Decimal, InvalidOperation
from xsdata.exceptions import ParserError
from nfelib.nfe.bindings.v4_0.proc_nfe_v4_00 import NfeProc

def para_centavos(texto):
    "Converte uma string de valor monetario vinda do XML da NF-e no inteiro de centavos"

    try:
        valor = Decimal(texto)
    except InvalidOperation:
        raise ValueError("Texto não é um número decimal válido")

    if valor < 0:
        raise ValueError("Valor não pode ser negativo")

    partes = str(valor).split('.')
    if len(partes) > 1 and len(partes[1]) > 2:
        raise ValueError("Valor tem mais de duas casas decimais")

    if len(partes) == 1:
        return int(valor) * 100
    else:
        return int(valor * 100)

    try:
        valor = Decimal(texto)
    except InvalidOperation:
        raise ValueError("Texto não é um número decimal válido")

    if valor < 0:
        raise ValueError("Valor não pode ser negativo")

    partes = str(valor).split('.')
    if len(partes) > 1 and len(partes[1]) > 2:
        raise ValueError("Valor tem mais de duas casas decimais")

    if len(partes) == 1:
        return int(valor) * 100
    else:
        return int(valor * 100)
def extrair_nota(xml_texto):
    try:
        proc = NfeProc.from_xml(xml_texto)
    except ParserError:
        raise ValueError("Erro ao parsear o XML")

    inf = proc.NFe.infNFe

    nota = {
        "chave": inf.Id[3:],  # Remove the prefix "NFe"
        "modelo": int(inf.ide.mod.value),
        "serie": int(inf.ide.serie),
        "numero": int(inf.ide.nNF),
        "dh_emi": inf.ide.dhEmi,
        "emit_nome": inf.emit.xNome,
        "emit_cnpj": inf.emit.CNPJ,
        "emit_municipio": inf.emit.enderEmit.xMun,
        "emit_uf": inf.emit.enderEmit.UF.value,
        "valor_total": para_centavos(inf.total.ICMSTot.vNF),
        "forma_pagamento": inf.pag.detPag[0].tPag,
        "xml_raw": xml_texto,
    }

    itens = []
    for det in inf.det:
        item = {
            "n_item": int(det.nItem),
            "descricao": det.prod.xProd,
            "cprod": det.prod.cProd,
            "ncm": det.prod.NCM,
            "gtin": det.prod.cEAN if det.prod.cEAN != "SEM GTIN" else None,
        }
        itens.append(item)

    return {"nota": nota, "itens": itens}

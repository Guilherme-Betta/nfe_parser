"""Le o XML de uma NF-e/NFC-e e devolve a nota e os itens como dicionarios.

As chaves dos dicionarios sao os nomes das colunas de `notas` e `itens`: e o que
deixa `persistencia.py` grava-los sem traducao nenhuma.
"""

from decimal import Decimal, InvalidOperation

from nfelib.nfe.bindings.v4_0.proc_nfe_v4_00 import NfeProc
from xsdata.exceptions import ParserError


def para_centavos(texto: str) -> int:
    """Converte uma string de valor monetario vinda do XML no inteiro de centavos.

    ⛔ Mais de duas casas decimais e RECUSADO, e nao arredondado: `vNF` e `vProd`
    tem duas casas no leiaute, entao um terceiro digito e dado errado — e
    arredondar esconderia o erro.
    """

    try:
        valor = Decimal(texto)
    except InvalidOperation as e:
        raise ValueError("Texto não é um número decimal válido") from e

    if valor < 0:
        raise ValueError("Valor não pode ser negativo")

    partes = str(valor).split(".")
    if len(partes) > 1 and len(partes[1]) > 2:
        raise ValueError("Valor tem mais de duas casas decimais")

    return int(valor * 100)


def extrair_nota(xml_texto: str) -> dict:
    """Devolve `{"nota": {...}, "itens": [...]}`, ou levanta `ValueError`.

    🔴 `ValueError` e o contrato com `importar`: e ele que vira linha `'invalida'`
    no log, em vez de derrubar o lote. Ha DOIS jeitos de uma nota nao servir, e
    os dois tem de sair como `ValueError`:

    1. o XML nao abre — o parser levanta `ParserError`;
    2. o XML abre, mas falta um bloco obrigatorio. ⚠️ O `xsdata` NAO confere
       obrigatoriedade: o bloco ausente vira `None`, e ler um campo dele levanta
       `AttributeError` (`None.detPag`), `IndexError` (lista `detPag` vazia) ou
       `TypeError` (`None` numa conversao, como `Decimal(None)`).

    ⚠️ O `try` do segundo caso envolve SO a leitura dos campos, que mora em
    `_ler_nota`. Capturar `AttributeError` tem um risco — esconder um erro de
    digitacao no proprio codigo —, e ele fica pequeno porque um nome de campo
    errado falharia em TODA nota, e todos os testes do caminho feliz cairiam
    juntos.

    O `from e` guarda o erro original como causa: o traceback continua mostrando
    QUAL campo faltou.
    """

    try:
        proc = NfeProc.from_xml(xml_texto)
    except ParserError as e:
        raise ValueError("Erro ao parsear o XML") from e

    try:
        return _ler_nota(proc, xml_texto)
    except (AttributeError, IndexError, TypeError) as e:
        raise ValueError(f"NF-e incompleta: {e}") from e


def _ler_nota(proc, xml_texto):
    inf = proc.NFe.infNFe

    nota = {
        "chave": inf.Id[3:],  # o atributo `Id` e "NFe" seguido dos 44 digitos da chave
        "modelo": int(inf.ide.mod.value),
        "serie": int(inf.ide.serie),
        "numero": int(inf.ide.nNF),
        "dh_emi": inf.ide.dhEmi,
        "emit_nome": inf.emit.xNome,
        # O DOCUMENTO do emitente, nao so o CNPJ: emitente pessoa fisica (produtor
        # rural) tem CPF e nenhum CNPJ. Sem o CPF aqui, item sem GTIN numa nota
        # dessas nao teria loja para a chave de texto, e derrubava o lote (spec 01 §6.3).
        # Os tamanhos nunca colidem: CNPJ tem 14 digitos, CPF tem 11.
        "emit_cnpj": inf.emit.CNPJ or inf.emit.CPF,
        "emit_municipio": inf.emit.enderEmit.xMun,
        "emit_uf": inf.emit.enderEmit.UF.value,
        "valor_total": para_centavos(inf.total.ICMSTot.vNF),
        "forma_pagamento": inf.pag.detPag[0].tPag,
        "xml_raw": xml_texto,
    }

    return {"nota": nota, "itens": [_ler_item(det) for det in inf.det]}


def _ler_item(det):
    prod = det.prod
    return {
        "n_item": int(det.nItem),
        "descricao": prod.xProd,
        "cprod": prod.cProd,
        "ncm": prod.NCM,
        "gtin": prod.cEAN if prod.cEAN != "SEM GTIN" else None,
        "quantidade": prod.qCom,
        "valor_unitario": prod.vUnCom,
        "valor_linha": para_centavos(prod.vProd),
        "unidade": prod.uCom,
    }

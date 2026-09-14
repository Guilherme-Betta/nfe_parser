"""Testes de `extrair_evento` — tarefa 1 da story 005-cancelamento-duas-passadas.

Escritos ANTES da implementacao (passo 2 do loop) e congelados por commit. O
modelo local recebe este arquivo como LEITURA (`--read`), nunca como editavel.

🔴 O STUB DAQUI E NOVO, E ISSO NAO E DETALHE. O stub de evento que a story 004
usa (`EVENTO_MINIMO`, em `test_classificador.py` e outros dois modulos) NAO tem
`chNFe`: ele parseia sem erro e devolve `chNFe=None`. Se os testes da 005
usassem aquele stub, a segunda passada nao acharia nota nenhuma, TUDO viraria
orfao, e nada estouraria — os testes "provariam" o comportamento errado.

Criterios em `specs/005-cancelamento-duas-passadas/spec.md` §3, bloco C1.
"""

import pytest
from nfe_parser.cancelamento import extrair_evento

NS = "http://www.portalfiscal.inf.br/nfe"

CHAVE_1ITEM = "35260499999999000199550010000000011000000017"


def _evento(chave=CHAVE_1ITEM, tp_evento="110111", dh_evento="2026-04-10T10:00:00-03:00"):
    """Monta um evento de cancelamento. Passe `None` para omitir um campo."""
    campos = ""
    if chave is not None:
        campos += f"<chNFe>{chave}</chNFe>"
    if dh_evento is not None:
        campos += f"<dhEvento>{dh_evento}</dhEvento>"
    if tp_evento is not None:
        campos += f"<tpEvento>{tp_evento}</tpEvento>"
    return (
        f'<procEventoNFe xmlns="{NS}" versao="1.00"><evento versao="1.00">'
        f"<infEvento>{campos}</infEvento></evento></procEventoNFe>"
    )


# --- C1.1 -------------------------------------------------------------------
def test_evento_completo_devolve_os_tres_campos():
    evento = extrair_evento(_evento())

    assert evento == {
        "ch_nfe": CHAVE_1ITEM,
        "tp_evento": "110111",
        "dh_evento": "2026-04-10T10:00:00-03:00",
    }


# --- C1.2, C1.3 -------------------------------------------------------------
def test_campo_ausente_vira_none_sem_levantar():
    """Um evento capenga e dado ruim, nao excecao. Quem decide o que fazer com
    ele e `aplicar_cancelamento` — esta funcao so relata o que leu."""
    assert extrair_evento(_evento(chave=None))["ch_nfe"] is None
    assert extrair_evento(_evento(tp_evento=None))["tp_evento"] is None
    assert extrair_evento(_evento(dh_evento=None))["dh_evento"] is None


def test_o_stub_sem_chave_da_story_004_continua_parseando():
    """🔒 O stub literal da 004, que parseia e devolve chave nenhuma.

    Se esta assercao falhar, os tres modulos de teste da 004 que usam este
    mesmo XML mudaram de comportamento junto.
    """
    evento_minimo = (
        f'<procEventoNFe xmlns="{NS}"><evento><infEvento>'
        "<tpEvento>110111</tpEvento></infEvento></evento></procEventoNFe>"
    )

    assert extrair_evento(evento_minimo)["ch_nfe"] is None


# --- C1.4 -------------------------------------------------------------------
@pytest.mark.parametrize("tp_evento", ["110111", "110110", "ABC"])
def test_tp_evento_sai_sempre_como_string(tp_evento):
    """⭐ O criterio que mais custa se for esquecido.

    O xsdata devolve `tpEvento` como ENUM quando o valor e '110111' (o texto
    fica em `.value`) e como STRING CRUA para qualquer outro valor, emitindo so
    um `ConverterWarning`. Um `inf.tpEvento.value` ingenuo passa no caminho
    feliz e estoura `AttributeError` na primeira carta de correcao que chegar.
    """
    lido = extrair_evento(_evento(tp_evento=tp_evento))["tp_evento"]

    assert lido == tp_evento
    assert isinstance(lido, str)


# --- C1.5 -------------------------------------------------------------------
@pytest.mark.parametrize(
    "xml",
    [
        f'<procEventoNFe xmlns="{NS}"></procEventoNFe>',
        f'<procEventoNFe xmlns="{NS}"><evento></evento></procEventoNFe>',
    ],
)
def test_evento_ou_infevento_ausente_devolve_tudo_none(xml):
    """O parser aceita os dois e devolve `None` no lugar do objeto — entao um
    acesso encadeado direto estoura `AttributeError`, nao `ParserError`."""
    assert extrair_evento(xml) == {"ch_nfe": None, "tp_evento": None, "dh_evento": None}


# --- C1.6 -------------------------------------------------------------------
def test_xml_que_nao_abre_levanta_value_error():
    """Evento SEM NAMESPACE. Nao e um caso inventado: o `classificar_xml`
    aceita a tag `procEventoNFe` crua (`classificador.py:20`) e a manda para ca,
    onde o parser levanta `ParserError`. Sem virar `ValueError`, esta excecao
    sobe e derruba o lote inteiro."""
    sem_namespace = (
        f"<procEventoNFe><evento><infEvento><chNFe>{CHAVE_1ITEM}</chNFe>"
        "<tpEvento>110111</tpEvento></infEvento></evento></procEventoNFe>"
    )

    with pytest.raises(ValueError):
        extrair_evento(sem_namespace)

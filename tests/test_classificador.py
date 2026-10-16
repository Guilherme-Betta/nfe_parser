"""Testes de `classificar_xml` — tarefa 3 da story 004-lote-zip-dedup.

Escritos ANTES da implementacao (passo 2 do loop) e congelados por commit. O
modelo local recebe este arquivo como LEITURA (`--read`), nunca como editavel.

⭐ O QUE FAZ ESTA FUNCAO SER DIFICIL: ela precisa responder sobre XML que o
`nfelib` RECUSA. Usar `NfeProc.from_xml` aqui seria pedir ao parser estrito que
classifique justamente o que ele nao consegue abrir. Por isso a leitura da raiz
e com `xml.etree.ElementTree`, e por isso `classificar_xml` **nunca levanta**:
ela devolve `"invalida"` no lugar.

Criterios em `specs/004-lote-zip-dedup/spec.md` §3, bloco C3.
"""

from pathlib import Path

import pytest

from nfe_parser.classificador import classificar_xml

FIXTURES = Path(__file__).parent / "fixtures"

NS = "http://www.portalfiscal.inf.br/nfe"

# XML minimos, inline de proposito (decisao (c) da §5 da spec): o roteamento
# decide pela RAIZ, entao um documento completo provaria a mesma coisa custando
# uma fixture grande e mais contexto no `--read` do passo 3.
CFE_MINIMO = f'<CFe xmlns="{NS}"><infCFe><ide><mod>59</mod></ide></infCFe></CFe>'
EVENTO_MINIMO = (
    f'<procEventoNFe xmlns="{NS}"><evento><infEvento>'
    "<tpEvento>110111</tpEvento></infEvento></evento></procEventoNFe>"
)
NFE_MOD_99 = (
    f'<nfeProc xmlns="{NS}"><NFe><infNFe Id="NFe{"9" * 44}">'
    "<ide><mod>99</mod></ide></infNFe></NFe></nfeProc>"
)


def _fixture(nome):
    return (FIXTURES / nome).read_text(encoding="utf-8")


# --- C3.1 -------------------------------------------------------------------
@pytest.mark.parametrize("nome", ["nfe_55_1item.xml", "nfe_55_3itens.xml", "nfe_65_1item.xml"])
def test_as_tres_fixtures_sao_nfe(nome):
    assert classificar_xml(_fixture(nome)) == "nfe"


# --- C3.2 -------------------------------------------------------------------
def test_cfe_sat_e_nao_suportado():
    assert classificar_xml(CFE_MINIMO) == "nao_suportado_sat"


# --- C3.3 -------------------------------------------------------------------
def test_proc_evento_e_evento():
    """A story 004 CLASSIFICA o evento. Aplicar o cancelamento e a story 005."""
    assert classificar_xml(EVENTO_MINIMO) == "evento"


# --- C3.4 -------------------------------------------------------------------
@pytest.mark.parametrize(
    "texto",
    [
        "<nfeProc><quebrado",  # XML malformado
        "",  # string vazia
        "   ",  # so espaco em branco
        "<qualquerCoisa/>",  # raiz desconhecida
        "isto nao e xml nenhum",  # texto solto
    ],
    ids=["malformado", "vazio", "espaco", "raiz-desconhecida", "texto-solto"],
)
def test_o_que_nao_da_para_rotear_e_invalida(texto):
    assert classificar_xml(texto) == "invalida"


# --- C3.5 -------------------------------------------------------------------
def test_nfe_proc_com_modelo_fora_de_55_e_65_e_invalida():
    """A raiz esta certa, o modelo nao. Nao da para extrair, e nao e CF-e."""
    assert classificar_xml(NFE_MOD_99) == "invalida"


# --- C3.6 -------------------------------------------------------------------
def test_nunca_levanta_excecao():
    """O importador chama isto dentro do laco do lote.

    Se `classificar_xml` levantar, um arquivo ruim derruba o lote inteiro — que
    e exatamente o criterio 4 da story.
    """
    entradas = [
        "",
        "<nfeProc><quebrado",
        "\x00\x01\x02",  # bytes binarios decodificados, como um .zip renomeado
        "<a><b></a>",  # tag fechada fora de ordem
        "<" * 500,  # lixo repetido
    ]

    for texto in entradas:
        assert classificar_xml(texto) in {"nfe", "nao_suportado_sat", "evento", "invalida"}


# --- C3.7 -------------------------------------------------------------------
def test_o_namespace_nao_atrapalha_a_leitura_da_raiz():
    """O que engana: `root.tag` vem como "{http://...}nfeProc", nao "nfeProc".

    Comparar `root.tag == "nfeProc"` falha em TODA nota real — e passaria num
    teste que usasse XML sem namespace. Por isso as fixtures deste projeto tem
    o namespace de verdade, e este teste exige as duas formas.
    """
    sem_ns = "<nfeProc><NFe><infNFe><ide><mod>55</mod></ide></infNFe></NFe></nfeProc>"
    com_ns = f'<nfeProc xmlns="{NS}"><NFe><infNFe><ide><mod>55</mod></ide></infNFe></NFe></nfeProc>'

    assert classificar_xml(sem_ns) == "nfe"
    assert classificar_xml(com_ns) == "nfe"


def test_o_modelo_65_tambem_e_nfe_e_nao_so_o_55():
    com_ns = f'<nfeProc xmlns="{NS}"><NFe><infNFe><ide><mod>65</mod></ide></infNFe></NFe></nfeProc>'

    assert classificar_xml(com_ns) == "nfe"


# --- devolve sempre uma das quatro strings --------------------------------
def test_o_retorno_e_sempre_uma_das_quatro_strings():
    valores = {
        classificar_xml(_fixture("nfe_55_1item.xml")),
        classificar_xml(CFE_MINIMO),
        classificar_xml(EVENTO_MINIMO),
        classificar_xml("<quebrado"),
    }

    assert valores == {"nfe", "nao_suportado_sat", "evento", "invalida"}

"""Testes do extrator de NF-e 55 — contrato da story 002-extrair-nfe-55.

Escritos ANTES da implementacao (passo 2 do loop) e congelados por commit. O
modelo local recebe este arquivo como LEITURA (`--read`), nunca como arquivo
editavel: se ele puder editar o teste, ele edita o teste para faze-lo passar,
que e o caminho mais curto para o objetivo dado.

Criterios em `specs/002-extrair-nfe-55/spec.md` §5 e §6. A numeracao dos
nomes de teste segue as tabelas de la -- por isso ela comeca em 01 aqui e
em 17 no `test_para_centavos.py`.

⭐ `para_centavos` e testado em `tests/test_para_centavos.py`, num modulo
separado de proposito: a story e fatiada em duas invocacoes do Aider, e um
import de funcao que ainda nao existe quebraria a COLETA do modulo inteiro,
impedindo a tarefa 1 de ficar verde. Ver o cabecalho daquele arquivo.
"""

from pathlib import Path

import pytest

from nfe_parser.extrator import extrair_nota

FIXTURE = Path(__file__).parent / "fixtures" / "nfe_55_1item.xml"

CHAVE = "35260499999999000199550010000000011000000017"
DH_EMI = "2026-04-15T10:30:00-03:00"


@pytest.fixture
def xml_texto():
    """O texto cru da fixture, que e tambem o que deve voltar em xml_raw."""
    return FIXTURE.read_text(encoding="utf-8")


@pytest.fixture
def resultado(xml_texto):
    return extrair_nota(xml_texto)


@pytest.fixture
def nota(resultado):
    return resultado["nota"]


@pytest.fixture
def item(resultado):
    return resultado["itens"][0]


# ---------------------------------------------------------------------------
# extrair_nota — identificacao da nota
# ---------------------------------------------------------------------------


def test_extrair_nota_01_chave_sem_prefixo_e_com_44_digitos(nota):
    """inf.Id vem como "NFe3526...". A chave sao os 44 digitos depois do prefixo."""
    assert nota["chave"] == CHAVE
    assert len(nota["chave"]) == 44
    assert nota["chave"].isdigit()


def test_extrair_nota_02_modelo_e_inteiro_55(nota):
    """ide.mod e um enum (Tmod.VALUE_55), nao uma string. A coluna e INTEGER."""
    assert nota["modelo"] == 55
    assert type(nota["modelo"]) is int


def test_extrair_nota_03_serie_e_numero_sao_inteiros(nota):
    assert nota["serie"] == 1
    assert nota["numero"] == 1
    assert type(nota["serie"]) is int
    assert type(nota["numero"]) is int


def test_extrair_nota_04_dh_emi_igual_ao_xml_com_offset(nota):
    """Ja chega ISO-8601 com offset. Converter para datetime e voltar perde o offset."""
    assert nota["dh_emi"] == DH_EMI


def test_extrair_nota_05_emitente_completo(nota):
    assert nota["emit_nome"] == "MERCEARIA EXEMPLO LTDA"
    assert nota["emit_cnpj"] == "99999999000199"
    assert nota["emit_municipio"] == "SAO PAULO"


def test_extrair_nota_06_emit_uf_e_string_nao_enum(nota):
    """enderEmit.UF e TufEmi.SP. str() dele devolveria "TufEmi.SP"."""
    assert nota["emit_uf"] == "SP"
    assert type(nota["emit_uf"]) is str


def test_extrair_nota_07_valor_total_e_804_nao_803(nota):
    """vNF = "8.04". int(float("8.04") * 100) devolve 803."""
    assert nota["valor_total"] == 804
    assert type(nota["valor_total"]) is int


def test_extrair_nota_08_forma_pagamento_vem_do_tpag(nota):
    """inf.pag e objeto, nao lista; detPag e que e lista."""
    assert nota["forma_pagamento"] == "01"


def test_extrair_nota_09_xml_raw_e_o_texto_recebido_intacto(nota, xml_texto):
    assert nota["xml_raw"] == xml_texto


# ---------------------------------------------------------------------------
# extrair_nota — o item
# ---------------------------------------------------------------------------


def test_extrair_nota_10_um_item(resultado):
    assert len(resultado["itens"]) == 1


def test_extrair_nota_11_quantidade_e_valor_unitario_sao_strings_exatas(item):
    """Passar por float/Decimal e voltar para string transforma "1.5000" em "1.5".

    O jeito de acertar este teste e NAO converter: o nfelib ja devolve o texto
    exato do XML.
    """
    assert item["quantidade"] == "1.5000"
    assert item["valor_unitario"] == "5.3600000000"
    assert type(item["quantidade"]) is str
    assert type(item["valor_unitario"]) is str


def test_extrair_nota_12_valor_linha_e_804_nao_803(item):
    """vProd = "8.04". Mesma armadilha do criterio 7."""
    assert item["valor_linha"] == 804
    assert type(item["valor_linha"]) is int


def test_extrair_nota_13_descricao_e_o_xprod_cru(item):
    assert item["descricao"] == "TOMATE ITALIANO KG"


def test_extrair_nota_14_ncm_e_cprod_como_strings(item):
    """NCM tem zero a esquerda: 07020000. Como int viraria 7020000."""
    assert item["ncm"] == "07020000"
    assert item["cprod"] == "SKU-0001"


def test_extrair_nota_15_sem_gtin_vira_none(item):
    """cEAN = "SEM GTIN". String vazia nao serve: a coluna e NULL."""
    assert item["gtin"] is None


def test_extrair_nota_16_n_item_e_inteiro(item):
    assert item["n_item"] == 1
    assert type(item["n_item"]) is int


# ---------------------------------------------------------------------------
# Caminho de erro (§6) — item 1 da rubrica de qualidade
# ---------------------------------------------------------------------------


def test_extrair_nota_24_xml_corrompido_levanta_value_error():
    with pytest.raises(ValueError):
        extrair_nota("<nfeProc><naofecha>")


def test_extrair_nota_25_xml_valido_que_nao_e_nfe_levanta_value_error():
    with pytest.raises(ValueError):
        extrair_nota('<?xml version="1.0"?><pedido><item>x</item></pedido>')


def test_extrair_nota_26_string_vazia_levanta_value_error():
    with pytest.raises(ValueError):
        extrair_nota("")

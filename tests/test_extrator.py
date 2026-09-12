"""Testes do extrator de NF-e 55 — contrato da story 002-extrair-nfe-55.

Escritos ANTES da implementacao (passo 2 do loop) e congelados por commit. O
modelo local recebe este arquivo como LEITURA (`--read`), nunca como arquivo
editavel: se ele puder editar o teste, ele edita o teste para faze-lo passar,
que e o caminho mais curto para o objetivo dado.

Criterios em `specs/002-extrair-nfe-55/spec.md` §5 e §6. A numeracao dos
comentarios abaixo segue as tabelas de la.
"""

from pathlib import Path

import pytest

from nfe_parser.extrator import extrair_nota, para_centavos

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
# para_centavos — o coracao da story
# ---------------------------------------------------------------------------


def test_17_converte_exato():
    assert para_centavos("8.04") == 804


def test_18_nao_usa_float():
    """int(float("0.29") * 100) devolve 28. O certo e 29.

    Este teste existe para reprovar a implementacao mais obvia. Nao remova.
    """
    assert para_centavos("0.29") == 29
    assert para_centavos("1.13") == 113
    assert para_centavos("2.01") == 201


def test_19_inteiro_sem_casas_decimais():
    assert para_centavos("10") == 1000


def test_20_zero():
    assert para_centavos("0.00") == 0


def test_21_mais_de_duas_casas_rejeita_em_vez_de_truncar():
    """A Fase 0 passou com int(Decimal("1.005") * 100), que devolve 100.

    Truncar dinheiro em silencio e pior que estourar: o numero errado segue
    para o banco e ninguem percebe. Aqui tem que levantar.
    """
    with pytest.raises(ValueError):
        para_centavos("1.005")


def test_22_texto_nao_numerico_rejeita():
    with pytest.raises(ValueError):
        para_centavos("abc")


def test_23_string_vazia_rejeita():
    with pytest.raises(ValueError):
        para_centavos("")


# ---------------------------------------------------------------------------
# extrair_nota — identificacao da nota
# ---------------------------------------------------------------------------


def test_01_chave_sem_prefixo_e_com_44_digitos(nota):
    """inf.Id vem como "NFe3526...". A chave sao os 44 digitos depois do prefixo."""
    assert nota["chave"] == CHAVE
    assert len(nota["chave"]) == 44
    assert nota["chave"].isdigit()


def test_02_modelo_e_inteiro_55(nota):
    """ide.mod e um enum (Tmod.VALUE_55), nao uma string. A coluna e INTEGER."""
    assert nota["modelo"] == 55
    assert type(nota["modelo"]) is int


def test_03_serie_e_numero_sao_inteiros(nota):
    assert nota["serie"] == 1
    assert nota["numero"] == 1
    assert type(nota["serie"]) is int
    assert type(nota["numero"]) is int


def test_04_dh_emi_igual_ao_xml_com_offset(nota):
    """Ja chega ISO-8601 com offset. Converter para datetime e voltar perde o offset."""
    assert nota["dh_emi"] == DH_EMI


def test_05_emitente_completo(nota):
    assert nota["emit_nome"] == "MERCEARIA EXEMPLO LTDA"
    assert nota["emit_cnpj"] == "99999999000199"
    assert nota["emit_municipio"] == "SAO PAULO"


def test_06_emit_uf_e_string_nao_enum(nota):
    """enderEmit.UF e TufEmi.SP. str() dele devolveria "TufEmi.SP"."""
    assert nota["emit_uf"] == "SP"
    assert type(nota["emit_uf"]) is str


def test_07_valor_total_e_804_nao_803(nota):
    """vNF = "8.04". int(float("8.04") * 100) devolve 803."""
    assert nota["valor_total"] == 804
    assert type(nota["valor_total"]) is int


def test_08_forma_pagamento_vem_do_tpag(nota):
    """inf.pag e objeto, nao lista; detPag e que e lista."""
    assert nota["forma_pagamento"] == "01"


def test_09_xml_raw_e_o_texto_recebido_intacto(nota, xml_texto):
    assert nota["xml_raw"] == xml_texto


# ---------------------------------------------------------------------------
# extrair_nota — o item
# ---------------------------------------------------------------------------


def test_10_um_item(resultado):
    assert len(resultado["itens"]) == 1


def test_11_quantidade_e_valor_unitario_sao_strings_exatas(item):
    """Passar por float/Decimal e voltar para string transforma "1.5000" em "1.5".

    O jeito de acertar este teste e NAO converter: o nfelib ja devolve o texto
    exato do XML.
    """
    assert item["quantidade"] == "1.5000"
    assert item["valor_unitario"] == "5.3600000000"
    assert type(item["quantidade"]) is str
    assert type(item["valor_unitario"]) is str


def test_12_valor_linha_e_804_nao_803(item):
    """vProd = "8.04". Mesma armadilha do criterio 7."""
    assert item["valor_linha"] == 804
    assert type(item["valor_linha"]) is int


def test_13_descricao_e_o_xprod_cru(item):
    assert item["descricao"] == "TOMATE ITALIANO KG"


def test_14_ncm_e_cprod_como_strings(item):
    """NCM tem zero a esquerda: 07020000. Como int viraria 7020000."""
    assert item["ncm"] == "07020000"
    assert item["cprod"] == "SKU-0001"


def test_15_sem_gtin_vira_none(item):
    """cEAN = "SEM GTIN". String vazia nao serve: a coluna e NULL."""
    assert item["gtin"] is None


def test_16_n_item_e_inteiro(item):
    assert item["n_item"] == 1
    assert type(item["n_item"]) is int


# ---------------------------------------------------------------------------
# Caminho de erro (§6) — item 1 da rubrica de qualidade
# ---------------------------------------------------------------------------


def test_24_xml_corrompido_levanta_value_error():
    with pytest.raises(ValueError):
        extrair_nota("<nfeProc><naofecha>")


def test_25_xml_valido_que_nao_e_nfe_levanta_value_error():
    with pytest.raises(ValueError):
        extrair_nota('<?xml version="1.0"?><pedido><item>x</item></pedido>')


def test_26_string_vazia_levanta_value_error():
    with pytest.raises(ValueError):
        extrair_nota("")

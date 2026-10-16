"""Testes do bloco "itens" de `extrair_nota` — tarefa 2b da story 002.

Escritos ANTES da implementacao (passo 2 do loop) e congelados por commit. O
modelo local recebe este arquivo como LEITURA (`--read`), nunca como arquivo
editavel.

Separado de `test_extrator_nota.py` pelo mesmo motivo que aquele e separado de
`test_para_centavos.py`: cada sub-tarefa do modelo local precisa de um oraculo
que fale so dela. Ver o cabecalho de `test_extrator_nota.py`.

Criterios em `specs/002-extrair-nfe-55/spec.md` §5, itens 10-16b.
"""

from pathlib import Path

import pytest

from nfe_parser.extrator import extrair_nota

FIXTURE = Path(__file__).parent / "fixtures" / "nfe_55_1item.xml"


@pytest.fixture
def resultado():
    return extrair_nota(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture
def item(resultado):
    return resultado["itens"][0]


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


def test_extrair_nota_16b_unidade(item):
    assert item["unidade"] == "KG"

"""Testes de N itens -> N linhas — tarefa 2 da story 003.

Escritos ANTES da implementacao (passo 2 do loop) e congelados por commit. O
modelo local recebe este arquivo como LEITURA (`--read`), nunca como arquivo
editavel.

Criterios C2 (assercoes 2.1 a 2.5) e C3.3 de
`specs/003-nfce-65-multi-item/spec.md` §3.

O C3.3 mora aqui, e nao num modulo proprio, porque ele so EXISTE com mais de um
item: a story 002 provou "SEM GTIN" -> None com um item so, caso em que "por
item" e "global" dao o mesmo resultado. E a mesma fixture, o mesmo defeito.
"""

from pathlib import Path

import pytest

from nfe_parser.extrator import extrair_nota

FIXTURES = Path(__file__).parent / "fixtures"
FIXTURE_3 = FIXTURES / "nfe_55_3itens.xml"
FIXTURE_1 = FIXTURES / "nfe_55_1item.xml"


@pytest.fixture
def itens():
    return extrair_nota(FIXTURE_3.read_text(encoding="utf-8"))["itens"]


# --- C2.1 e C2.2 -------------------------------------------------------------

def test_2_1_tres_det_produzem_tres_itens(itens):
    # Nao 1 (parou no primeiro <det>), nao 4 (contou algo que nao e item).
    assert len(itens) == 3


def test_2_2_n_item_sai_1_2_3_na_ordem(itens):
    assert [i["n_item"] for i in itens] == [1, 2, 3]
    assert all(isinstance(i["n_item"], int) for i in itens)


# --- C2.3 --------------------------------------------------------------------

def test_2_3_as_descricoes_sao_distintas_e_batem_com_o_xml(itens):
    """Esta e a assercao que pega "extraiu o item 1 tres vezes".

    Esse modo de falha passaria em 2.1 (len == 3) e passaria em 2.2 se o nItem
    viesse do indice do laco em vez de vir do XML. So comparar o CONTEUDO de
    cada linha o expoe.
    """
    descricoes = [i["descricao"] for i in itens]
    assert descricoes == [
        "ACHOCOLATADO EM PO 400G",
        "TOMATE ITALIANO KG",
        "ARROZ BRANCO TIPO 1 1KG",
    ]
    assert len(set(descricoes)) == 3


def test_2_3_os_demais_campos_tambem_variam_por_item(itens):
    assert [i["cprod"] for i in itens] == ["SKU-0010", "SKU-0001", "SKU-0030"]
    assert [i["unidade"] for i in itens] == ["UN", "KG", "PC"]
    assert [i["ncm"] for i in itens] == ["18069000", "07020000", "10063021"]
    # Strings exatas do XML, com os zeros a direita preservados.
    assert [i["quantidade"] for i in itens] == ["2.0000", "1.5000", "3.0000"]
    assert [i["valor_unitario"] for i in itens] == [
        "3.3300000000",
        "5.3600000000",
        "0.9500000000",
    ]


# --- C2.4 --------------------------------------------------------------------

def test_2_4_valor_linha_de_cada_item_em_centavos(itens):
    # Os tres sao armadilha de float por conta propria:
    #   int(float("6.66") * 100) == 665 | ("8.04") == 803 | ("2.85") == 284
    assert [i["valor_linha"] for i in itens] == [666, 804, 285]
    assert all(isinstance(i["valor_linha"], int) for i in itens)


def test_2_4_a_soma_das_linhas_fecha_com_o_total():
    """⚠️ Esta assercao so vale porque a fixture foi construida para ela valer.

    Na `nfe_55_3itens.xml` o frete, o seguro e o desconto sao zero DE PROPOSITO.
    Numa NF-e real o vNF inclui esses campos e a soma dos vProd NAO fecha com
    ele. Isto e propriedade da fixture, nao regra do dominio: nao escreva
    validacao de soma dentro do extrator.py por causa deste teste.
    """
    r = extrair_nota(FIXTURE_3.read_text(encoding="utf-8"))
    assert sum(i["valor_linha"] for i in r["itens"]) == r["nota"]["valor_total"]
    assert r["nota"]["valor_total"] == 1755


# --- C2.5 --------------------------------------------------------------------

def test_2_5_uma_nota_de_um_item_continua_dando_um_item():
    # Multi-item nao pode virar "sempre >= 2". A fixture de 1 item nao e tocada.
    r = extrair_nota(FIXTURE_1.read_text(encoding="utf-8"))
    assert len(r["itens"]) == 1
    assert r["itens"][0]["n_item"] == 1


# --- C3.3 --------------------------------------------------------------------

def test_3_3_gtin_e_resolvido_por_item_e_nao_globalmente(itens):
    """O item 2 tem "SEM GTIN"; os itens 1 e 3 tem GTIN de verdade.

    Um codigo que decidisse o GTIN uma vez para a nota inteira — olhando o
    primeiro item e aplicando a todos — passaria em todos os testes da story
    002 e falharia aqui, que e o ponto.
    """
    assert [i["gtin"] for i in itens] == [
        "7891000100103",
        None,
        "7891910000197",
    ]


def test_3_3_sem_gtin_vira_none_e_nao_string_vazia(itens):
    assert itens[1]["gtin"] is None
    assert itens[1]["gtin"] != ""
    assert itens[1]["gtin"] != "SEM GTIN"

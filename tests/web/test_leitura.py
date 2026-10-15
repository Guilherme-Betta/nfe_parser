"""Leitura de notas via API — spec 03 §4, criterio C10."""

import json

import pytest

from nfe_parser.serializacao import nota_para_json
from tests.apoio import (
    CHAVE_1ITEM,
    CHAVE_3ITENS,
    CHAVE_65,
    chave,
    enviar,
    evento,
    texto,
    variante,
    zip_de,
)

OUTRA_LOJA = "88888888000188"


@pytest.fixture
def quatro_notas(cliente):
    """04, 05 e 06/2026 da loja das fixtures; uma de 07/2026 de OUTRA loja, cancelada."""
    da_outra_loja = variante(
        "nfe_55_1item.xml", chave(1), cnpj=OUTRA_LOJA, dh_emi="2026-07-01T09:00:00-03:00"
    )
    lote = zip_de(
        {
            "a.xml": texto("nfe_55_1item.xml"),
            "b.xml": texto("nfe_65_1item.xml"),
            "c.xml": texto("nfe_55_3itens.xml"),
            "d.xml": da_outra_loja,
            "e.xml": evento(chave(1)),
        }
    )
    assert enviar(cliente, "lote.zip", lote).status_code == 201
    return cliente


def _chaves(resposta):
    return [nota["chave"] for nota in resposta.json()["notas"]]


def test_lista_sem_filtro_traz_todas_da_mais_recente_para_a_mais_antiga(quatro_notas):
    resposta = quatro_notas.get("/api/notas")

    assert resposta.status_code == 200
    assert _chaves(resposta) == [chave(1), CHAVE_3ITENS, CHAVE_65, CHAVE_1ITEM]
    assert resposta.json()["total"] == 4


def test_cabecalho_da_nota_traz_dinheiro_nos_dois_campos(quatro_notas):
    nota = quatro_notas.get("/api/notas", params={"mes": "2026-06"}).json()["notas"][0]

    assert nota == {
        "chave": CHAVE_3ITENS,
        "modelo": 55,
        "dh_emi": "2026-06-02T08:15:00-03:00",
        "emit_nome": nota["emit_nome"],
        "emit_cnpj": "99999999000199",
        "valor_total_centavos": 1755,
        "valor_total": "17.55",
        "status": "ok",
        "n_itens": 3,
    }


@pytest.mark.parametrize(
    ("params", "esperado"),
    [
        ({"mes": "2026-05"}, [CHAVE_65]),
        ({"loja_cnpj": OUTRA_LOJA}, [chave(1)]),
        ({"status": "cancelada"}, [chave(1)]),
        ({"status": "ok", "loja_cnpj": "99999999000199", "mes": "2026-04"}, [CHAVE_1ITEM]),
    ],
)
def test_filtros_por_mes_loja_e_status(quatro_notas, params, esperado):
    assert _chaves(quatro_notas.get("/api/notas", params=params)) == esperado


def test_paginacao(quatro_notas):
    primeira = quatro_notas.get("/api/notas", params={"por_pagina": 3}).json()
    segunda = quatro_notas.get("/api/notas", params={"por_pagina": 3, "pagina": 2}).json()

    assert [n["chave"] for n in primeira["notas"]] == [chave(1), CHAVE_3ITENS, CHAVE_65]
    assert [n["chave"] for n in segunda["notas"]] == [CHAVE_1ITEM]
    assert (segunda["total"], segunda["pagina"], segunda["por_pagina"]) == (4, 2, 3)


@pytest.mark.parametrize(
    "params", [{"mes": "2026-5"}, {"status": "talvez"}, {"pagina": 0}, {"por_pagina": 201}]
)
def test_parametro_fora_do_formato_e_422(quatro_notas, params):
    assert quatro_notas.get("/api/notas", params=params).status_code == 422


def test_detalhe_e_a_saida_de_nota_para_json(quatro_notas, banco):
    resposta = quatro_notas.get(f"/api/notas/{CHAVE_3ITENS}")

    assert resposta.status_code == 200
    assert resposta.json() == json.loads(nota_para_json(banco, CHAVE_3ITENS))


def test_chave_inexistente_e_404(quatro_notas):
    resposta = quatro_notas.get(f"/api/notas/{chave(999)}")

    assert resposta.status_code == 404
    assert chave(999) in resposta.json()["detail"]

"""Fila de revisao e classificacao manual via API — spec 03 §4, criterio C11."""

import pytest

from tests.web.apoio import ACHOCOLATADO, TOMATE, chave, enviar, produto, texto, variante


@pytest.fixture
def tomate_no_bucket(cliente):
    """A nota de 3 itens com o TOMATE fora do mapa NCM: ele cai no bucket, os outros nao."""
    xml = variante("nfe_55_3itens.xml", chave(1), ncm=("07020000", "99999999"))
    assert enviar(cliente, "nota.xml", xml).status_code == 201
    return cliente


def test_fila_de_nao_classificados_traz_so_origem_nula(tomate_no_bucket, banco):
    corpo = tomate_no_bucket.get("/api/produtos", params={"classificado": "false"}).json()

    assert corpo["total"] == 1
    (item,) = corpo["produtos"]
    assert item == {
        "id": produto(banco, TOMATE)[0],
        "descricao_exemplo": TOMATE,
        "identidade_origem": "texto",
        "aproximado": True,
        "gtin": None,
        "categoria_slug": "uncategorized",
        "categoria": item["categoria"],
        "origem": None,
        "n_itens": 1,
    }


def test_filtros_classificado_e_origem(tomate_no_bucket):
    classificados = tomate_no_bucket.get("/api/produtos", params={"classificado": "true"}).json()
    por_ncm = tomate_no_bucket.get("/api/produtos", params={"origem": "ncm"}).json()

    assert classificados["total"] == 2
    assert all(p["origem"] == "ncm" for p in classificados["produtos"])
    assert {p["descricao_exemplo"] for p in por_ncm["produtos"]} >= {ACHOCOLATADO}
    assert all(p["aproximado"] is False for p in por_ncm["produtos"])


def test_categoria_manual_grava_e_vale_para_os_proximos_itens(tomate_no_bucket, banco):
    produto_id = produto(banco, TOMATE)[0]

    resposta = tomate_no_bucket.post(
        f"/api/produtos/{produto_id}/categoria", json={"categoria_slug": "vegetais"}
    )

    assert resposta.status_code == 200
    assert resposta.json()["categoria_slug"] == "vegetais"
    assert resposta.json()["origem"] == "manual"
    assert produto(banco, TOMATE)[1:] == ("vegetais", "manual")

    # outra nota, mesma loja, mesmo TOMATE fora do mapa: resolve para o MESMO produto
    proxima = variante("nfe_55_1item.xml", chave(2), ncm=("07020000", "99999999"))
    corpo = enviar(tomate_no_bucket, "proxima.xml", proxima).json()

    assert corpo["classificacao"]["memoria"] == 1
    item = tomate_no_bucket.get(f"/api/notas/{chave(2)}").json()["itens"][0]
    assert item["categoria_slug"] == "vegetais"


@pytest.mark.parametrize(
    ("produto_id", "slug"), [(999, "vegetais"), (None, "nao-existe")], ids=["produto", "slug"]
)
def test_produto_ou_categoria_inexistente_e_404(tomate_no_bucket, banco, produto_id, slug):
    produto_id = produto_id or produto(banco, TOMATE)[0]

    resposta = tomate_no_bucket.post(
        f"/api/produtos/{produto_id}/categoria", json={"categoria_slug": slug}
    )

    assert resposta.status_code == 404
    assert "nao existe" in resposta.json()["detail"]


def test_paginacao_da_fila(cliente):
    enviar(cliente, "nota.xml", texto("nfe_55_3itens.xml"))

    corpo = cliente.get("/api/produtos", params={"por_pagina": 2, "pagina": 2}).json()

    assert (corpo["total"], len(corpo["produtos"]), corpo["pagina"]) == (3, 1, 2)

"""Orcamento via API e pagina — spec 04 §4 e §5, criterios O3 e O7."""

from datetime import datetime

import pytest

from tests.apoio import enviar, texto

JUNHO = "2026-06"


@pytest.fixture
def com_junho(cliente):
    """ACHOCOLATADO 6,66 + ARROZ 2,85 em `mercado` (rollup) e TOMATE 8,04 em `vegetais`."""
    assert enviar(cliente, "junho.xml", texto("nfe_55_3itens.xml")).status_code == 201
    return cliente


def _criar(cliente, slug="mercado", limite=1000, mes=JUNHO):
    return cliente.post(
        "/api/orcamentos", json={"categoria_slug": slug, "mes": mes, "limite": limite}
    )


def test_get_do_mes(com_junho):
    corpo = com_junho.get("/api/orcamentos", params={"mes": JUNHO}).json()

    assert {(l["categoria_slug"], l["gasto"]) for l in corpo["linhas"]} == {
        ("mercado", 951),
        ("vegetais", 804),
    }
    assert corpo["nao_classificado"] == {"gasto": 0}
    assert corpo["totais"] == {"limite": 0, "gasto": 1755}


@pytest.mark.parametrize("params", [{}, {"mes": "2026-6"}])
def test_get_sem_mes_ou_mes_fora_do_formato_e_422(cliente, params):
    assert cliente.get("/api/orcamentos", params=params).status_code == 422


def test_criar_alterar_apagar(com_junho):
    criado = _criar(com_junho, limite=900)

    assert criado.status_code == 201
    orcamento_id = criado.json()["id"]
    assert criado.json() == {
        "id": orcamento_id,
        "categoria_slug": "mercado",
        "mes": JUNHO,
        "limite": 900,
    }
    linha = next(
        l
        for l in com_junho.get("/api/orcamentos", params={"mes": JUNHO}).json()["linhas"]
        if l["categoria_slug"] == "mercado"
    )
    assert (linha["saldo"], linha["estouro"]) == (-51, True)

    alterado = com_junho.patch(f"/api/orcamentos/{orcamento_id}", json={"limite": 2000})
    assert alterado.json()["limite"] == 2000

    assert com_junho.delete(f"/api/orcamentos/{orcamento_id}").status_code == 204
    assert com_junho.delete(f"/api/orcamentos/{orcamento_id}").status_code == 404


@pytest.mark.parametrize(
    ("slug", "limite", "mes"),
    [
        ("mercado-mercearia", 1000, JUNHO),
        ("uncategorized", 1000, JUNHO),
        ("mercado", 0, JUNHO),
        ("mercado", 1000, "2026-13"),
    ],
    ids=["subcategoria", "bucket", "limite-zero", "mes-invalido"],
)
def test_criar_recusado_e_400(cliente, slug, limite, mes):
    resposta = _criar(cliente, slug, limite, mes)

    assert resposta.status_code == 400
    assert resposta.json()["detail"]


def test_criar_repetido_e_400(cliente):
    _criar(cliente)

    assert _criar(cliente).status_code == 400


def test_categoria_ou_orcamento_inexistente_e_404(cliente):
    assert _criar(cliente, slug="nao-existe").status_code == 404
    resposta = cliente.patch("/api/orcamentos/999", json={"limite": 10})
    assert resposta.status_code == 404
    assert "999" in resposta.json()["detail"]


# --- pagina (O7) -----------------------------------------------------------------


def test_pagina_abre_no_mes_corrente(cliente):
    resposta = cliente.get("/orcamento")

    assert resposta.status_code == 200
    assert datetime.now().astimezone().strftime("%Y-%m") in resposta.text


def test_pagina_de_um_mes_mostra_as_categorias(com_junho):
    resposta = com_junho.get("/orcamento", params={"mes": JUNHO})

    assert resposta.status_code == 200
    assert "R$ 9,51" in resposta.text
    assert "Não classificado" in resposta.text


def test_criar_pelo_formulario_converte_reais_e_redireciona(cliente):
    resposta = cliente.post(
        "/orcamento",
        data={"categoria_slug": "mercado", "mes": JUNHO, "limite": "1.234,56"},
        follow_redirects=False,
    )

    assert resposta.status_code == 303
    assert resposta.headers["location"] == f"/orcamento?mes={JUNHO}"
    corpo = cliente.get("/api/orcamentos", params={"mes": JUNHO}).json()
    assert corpo["totais"]["limite"] == 123456


def test_valor_invalido_no_formulario_volta_com_a_mensagem(cliente):
    resposta = cliente.post(
        "/orcamento", data={"categoria_slug": "mercado", "mes": JUNHO, "limite": "abc"}
    )

    assert resposta.status_code == 400
    assert "valor" in resposta.text.lower()


def test_estouro_aparece_destacado(com_junho):
    """⚠️ Confere a AUSENCIA antes: se a palavra estivesse sempre na pagina (num
    rotulo de legenda, numa classe CSS), o teste passaria sem estouro nenhum."""
    _criar(com_junho, limite=100000)
    assert "estouro" not in com_junho.get("/orcamento", params={"mes": JUNHO}).text.lower()

    _criar(com_junho, slug="vegetais", limite=100)  # gasto de 8,04 contra teto de 1,00

    assert "estouro" in com_junho.get("/orcamento", params={"mes": JUNHO}).text.lower()


def test_alterar_e_apagar_pelo_formulario(com_junho):
    orcamento_id = _criar(com_junho, limite=900).json()["id"]

    alterado = com_junho.post(
        f"/orcamento/{orcamento_id}/limite",
        data={"limite": "20,00", "mes": JUNHO},
        follow_redirects=False,
    )
    apagado = com_junho.post(
        f"/orcamento/{orcamento_id}/apagar", data={"mes": JUNHO}, follow_redirects=False
    )

    assert alterado.status_code == apagado.status_code == 303
    assert com_junho.get("/api/orcamentos", params={"mes": JUNHO}).json()["totais"]["limite"] == 0

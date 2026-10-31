"""Relatorios via API e pagina — spec 05 §4 e §5, criterios V1, V6 e V8."""

import json
import re

import pytest

from tests.apoio import (
    ACHOCOLATADO,
    CNPJ_FIXTURE,
    TOMATE,
    chave,
    enviar,
    produto,
    texto,
    variante,
)

FILIAL = "88888888000188"  # mesmo nome da loja das fixtures, outro CNPJ
OUTRA_LOJA = "77777777000177"
NOME_FIXTURE = "MERCEARIA EXEMPLO LTDA"


@pytest.fixture
def com_notas(cliente):
    """Abril (TOMATE), maio (ACHOCOLATADO) e junho (os 3 itens), todos da mesma loja."""
    for nome in ("nfe_55_1item.xml", "nfe_65_1item.xml", "nfe_55_3itens.xml"):
        assert enviar(cliente, nome, texto(nome)).status_code == 201
    return cliente


def _get(cliente, analise, **params):
    return cliente.get(f"/api/relatorios/{analise}", params=params)


def test_gasto_mensal(com_notas):
    resposta = _get(com_notas, "gasto-mensal")

    assert resposta.status_code == 200
    assert resposta.json() == [
        {"mes": "2026-04", "gasto": 804},
        {"mes": "2026-05", "gasto": 1234},
        {"mes": "2026-06", "gasto": 1755},
    ]


def test_gasto_categoria_com_filtro_de_periodo(com_notas):
    corpo = _get(com_notas, "gasto-categoria", de="2026-06", ate="2026-06").json()

    assert {(l["categoria_slug"], l["gasto"]) for l in corpo["linhas"]} == {
        ("mercado", 951),
        ("vegetais", 804),
    }
    assert corpo["nao_classificado"] == {"gasto": 0}


def test_gasto_loja_e_top_produtos(com_notas):
    lojas = _get(com_notas, "gasto-loja", categoria_slug="mercado").json()
    top = _get(com_notas, "top-produtos", limite=1).json()

    assert [(l["emit_cnpj"], l["gasto"]) for l in lojas] == [("99999999000199", 1234 + 951)]
    assert len(top) == 1
    assert top[0]["descricao_exemplo"] == ACHOCOLATADO
    assert top[0]["quantidade"] == "4.0000"


def test_preco_no_tempo(com_notas, banco):
    produto_id = produto(banco, TOMATE)[0]

    corpo = _get(com_notas, "preco-no-tempo", produto_id=produto_id).json()

    assert corpo["aproximado"] is True
    assert [p["valor_unitario"] for p in corpo["pontos"]] == ["5.3600000000", "5.3600000000"]


@pytest.mark.parametrize(
    ("analise", "params"),
    [
        ("gasto-mensal", {"de": "2026-6"}),
        ("gasto-loja", {"ate": "junho"}),
        ("top-produtos", {"ordenar": "preco"}),
        ("top-produtos", {"limite": 0}),
        ("top-produtos", {"limite": 101}),
        ("preco-no-tempo", {}),
    ],
)
def test_parametro_fora_do_formato_e_422(cliente, analise, params):
    assert _get(cliente, analise, **params).status_code == 422


@pytest.mark.parametrize(
    ("analise", "params"),
    [
        ("gasto-mensal", {"categoria_slug": "nao-existe"}),
        ("gasto-categoria", {"produto_id": 999}),
        ("preco-no-tempo", {"produto_id": 999}),
    ],
)
def test_categoria_ou_produto_inexistente_e_404(cliente, analise, params):
    resposta = _get(cliente, analise, **params)

    assert resposta.status_code == 404
    assert "nao existe" in resposta.json()["detail"]


# --- pagina (V8) -----------------------------------------------------------------


def _dados_embutidos(html, nome):
    """O JSON que a pagina embute para o grafico `nome`."""
    trecho = re.search(
        rf'<script type="application/json" id="dados-{nome}">(.*?)</script>', html, re.DOTALL
    )
    assert trecho, f"a pagina nao embute os dados do grafico {nome!r}"
    return json.loads(trecho.group(1))


def test_pagina_traz_tabelas_e_os_dados_dos_graficos(com_notas):
    resposta = com_notas.get("/relatorios")

    assert resposta.status_code == 200
    html = resposta.text
    assert _dados_embutidos(html, "mensal") == [
        {"mes": "2026-04", "gasto": 804},
        {"mes": "2026-05", "gasto": 1234},
        {"mes": "2026-06", "gasto": 1755},
    ]
    assert _dados_embutidos(html, "top")[0]["descricao_exemplo"] == ACHOCOLATADO
    assert "R$ 17,55" in html  # a tabela gemea do mensal
    assert "/static/chart.umd.js" in html


def test_pagina_com_filtros(com_notas):
    html = com_notas.get("/relatorios", params={"de": "2026-06", "categoria_slug": "vegetais"}).text

    assert _dados_embutidos(html, "mensal") == [{"mes": "2026-06", "gasto": 804}]


def test_filtros_vazios_do_formulario_sao_ignorados(com_notas):
    resposta = com_notas.get(
        "/relatorios", params={"de": "", "ate": "", "categoria_slug": "", "loja_cnpj": ""}
    )

    assert resposta.status_code == 200
    assert len(_dados_embutidos(resposta.text, "mensal")) == 3


def _opcoes_do_filtro_de_loja(html):
    seletor = re.search(r'<select name="loja_cnpj".*?</select>', html, re.DOTALL)
    assert seletor, "a pagina nao tem o seletor de loja"
    return re.findall(r'<option value="([^"]*)"[^>]*>([^<]*)</option>', seletor.group(0))


def test_lojas_de_mesmo_nome_sao_distinguidas_no_filtro_de_loja(com_notas):
    """Spec 05 §5: rotulo repetido ganha o fim do CNPJ — no seletor do filtro tambem.
    Duas filiais com o mesmo `xNome` sairiam como duas opcoes identicas, e o usuario
    nao saberia qual filtra o que. Loja de nome unico continua so com o nome."""
    filial = variante("nfe_55_1item.xml", chave(1), cnpj=FILIAL)
    outra = variante("nfe_55_1item.xml", chave(2), cnpj=OUTRA_LOJA)
    outra = outra.replace(NOME_FIXTURE, "PADARIA EXEMPLO")
    assert enviar(com_notas, "filial.xml", filial).status_code == 201
    assert enviar(com_notas, "outra.xml", outra).status_code == 201

    html = com_notas.get("/relatorios").text

    assert _opcoes_do_filtro_de_loja(html) == [
        ("", "todas"),
        (FILIAL, f"{NOME_FIXTURE} · …000188"),
        (CNPJ_FIXTURE, f"{NOME_FIXTURE} · …000199"),
        (OUTRA_LOJA, "PADARIA EXEMPLO"),
    ]


def test_seletor_da_serie_mensal_nao_oferece_pizza(com_notas):
    html = com_notas.get("/relatorios").text
    seletor = re.search(r'<select[^>]*data-grafico="mensal".*?</select>', html, re.DOTALL)

    assert seletor
    opcoes = re.findall(r'<option value="([^"]+)"', seletor.group(0))
    assert opcoes == ["line", "bar"]


def test_produto_por_texto_aparece_aproximado_no_preco(com_notas, banco):
    produto_id = produto(banco, TOMATE)[0]

    html = com_notas.get("/relatorios", params={"produto_id": produto_id}).text

    assert "aproximado" in html
    assert _dados_embutidos(html, "preco")["pontos"]


def test_filtro_inexistente_na_pagina_e_404(cliente):
    resposta = cliente.get("/relatorios", params={"categoria_slug": "nao-existe"})

    assert resposta.status_code == 404
    assert resposta.headers["content-type"].startswith("text/html")


def test_chart_js_e_servido_do_proprio_app(cliente):
    resposta = cliente.get("/static/chart.umd.js")

    assert resposta.status_code == 200
    assert "Chart.js v4.4.1" in resposta.text

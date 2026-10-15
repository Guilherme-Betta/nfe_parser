"""UI server-rendered — spec 03 §5, criterios C13 e C14 (smoke, nao layout)."""

import pytest

from tests.web.apoio import CHAVE_3ITENS, TOMATE, chave, enviar, produto, texto, variante


@pytest.fixture
def importado(cliente):
    """A nota de 3 itens com o TOMATE fora do mapa NCM (bucket). Devolve o id do lote."""
    xml = variante("nfe_55_3itens.xml", CHAVE_3ITENS, ncm=("07020000", "99999999"))
    return enviar(cliente, "nota.xml", xml).json()["importacao_id"]


@pytest.mark.parametrize(
    "rota",
    ["/", "/notas", "/revisar", "/taxonomia", "/importacoes/{id}", f"/notas/{CHAVE_3ITENS}"],
)
def test_paginas_respondem_html(cliente, importado, rota):
    resposta = cliente.get(rota.format(id=importado))

    assert resposta.status_code == 200
    assert resposta.headers["content-type"].startswith("text/html")


@pytest.mark.parametrize("rota", ["/importacoes/999", f"/notas/{chave(999)}"])
def test_pagina_de_coisa_inexistente_e_404(cliente, rota):
    resposta = cliente.get(rota)

    assert resposta.status_code == 404
    assert resposta.headers["content-type"].startswith("text/html")


def test_upload_pelo_formulario_roda_o_pipeline_e_redireciona(cliente, banco):
    resposta = cliente.post(
        "/importar",
        files={"arquivo": ("nota.xml", texto("nfe_55_1item.xml").encode("utf-8"))},
        follow_redirects=False,
    )

    assert resposta.status_code == 303
    importacao_id = banco.execute("SELECT MAX(id) FROM importacoes").fetchone()[0]
    assert resposta.headers["location"] == f"/importacoes/{importacao_id}"
    assert banco.execute("SELECT COUNT(*) FROM notas").fetchone()[0] == 1


def test_upload_com_extensao_errada_volta_com_a_mensagem(cliente):
    resposta = cliente.post("/importar", files={"arquivo": ("notas.txt", b"x")})

    assert resposta.status_code == 400
    assert "zip" in resposta.text


def test_revisar_com_htmx_grava_e_devolve_so_a_linha(cliente, importado, banco):
    produto_id = produto(banco, TOMATE)[0]

    resposta = cliente.post(
        f"/revisar/{produto_id}",
        data={"categoria_slug": "vegetais"},
        headers={"HX-Request": "true"},
    )

    assert resposta.status_code == 200
    assert "<html" not in resposta.text
    assert produto(banco, TOMATE)[1:] == ("vegetais", "manual")


def test_revisar_sem_htmx_grava_e_redireciona(cliente, importado, banco):
    produto_id = produto(banco, TOMATE)[0]

    resposta = cliente.post(
        f"/revisar/{produto_id}", data={"categoria_slug": "vegetais"}, follow_redirects=False
    )

    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/revisar"
    assert produto(banco, TOMATE)[1:] == ("vegetais", "manual")


def test_taxonomia_pelo_formulario_cria_e_apaga(cliente, banco):
    criada = cliente.post("/taxonomia", data={"nome": "Pets"}, follow_redirects=False)
    apagada = cliente.post("/taxonomia/pets/apagar", follow_redirects=False)

    assert criada.status_code == apagada.status_code == 303
    assert banco.execute("SELECT 1 FROM categorias WHERE slug = 'pets'").fetchone() is None
    assert banco.execute("SELECT 1 FROM categorias_apagadas WHERE slug = 'pets'").fetchone()


def test_taxonomia_recusada_volta_com_a_mensagem(cliente):
    resposta = cliente.post("/taxonomia/uncategorized/apagar")

    assert resposta.status_code == 400
    assert "bucket" in resposta.text


def test_htmx_e_servido_do_proprio_app(cliente):
    resposta = cliente.get("/static/htmx.min.js")

    assert resposta.status_code == 200
    assert "htmx" in resposta.text


# C14
def test_produto_por_texto_aparece_como_casamento_aproximado(cliente, importado):
    pagina = cliente.get("/revisar").text

    assert TOMATE in pagina
    assert "casamento aproximado" in pagina

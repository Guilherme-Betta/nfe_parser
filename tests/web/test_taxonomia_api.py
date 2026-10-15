"""Taxonomia via API — spec 03 §4, criterio C12. Categoria e endereçada por slug."""

import pytest

from tests.web.apoio import ACHOCOLATADO, TOMATE, enviar, produto, texto


def _no(arvore, slug):
    """O no `slug` da arvore, procurando nos dois niveis. `(no, slug do pai)`."""
    for raiz in arvore:
        if raiz["slug"] == slug:
            return raiz, None
        for filha in raiz["filhas"]:
            if filha["slug"] == slug:
                return filha, raiz["slug"]
    return None, None


@pytest.fixture
def com_produtos(cliente):
    """TOMATE em `vegetais` e ACHOCOLATADO em `mercado-mercearia`, ambos por NCM."""
    assert enviar(cliente, "nota.xml", texto("nfe_55_3itens.xml")).status_code == 201
    return cliente


def test_arvore_tem_dois_niveis_e_conta_produtos(com_produtos):
    arvore = com_produtos.get("/api/categorias").json()

    mercearia, pai = _no(arvore, "mercado-mercearia")
    assert pai == "mercado"
    assert mercearia["n_produtos"] == 2
    bucket, _ = _no(arvore, "uncategorized")
    assert bucket["is_bucket"] is True
    assert "filhas" not in mercearia


def test_criar_nivel_1_e_subcategoria(cliente):
    raiz = cliente.post("/api/categorias", json={"nome": "Pets"})
    filha = cliente.post("/api/categorias", json={"nome": "Molhos", "parent_slug": "mercado"})

    assert raiz.status_code == filha.status_code == 201
    assert raiz.json() == {"slug": "pets", "nome": "Pets", "parent_slug": None}
    assert filha.json() == {"slug": "mercado-molhos", "nome": "Molhos", "parent_slug": "mercado"}
    assert _no(cliente.get("/api/categorias").json(), "mercado-molhos")[1] == "mercado"


@pytest.mark.parametrize(
    "corpo",
    [
        {"nome": "Morango", "parent_slug": "mercado-frutas"},
        {"nome": "Mercado"},
        {"nome": "!!!"},
    ],
    ids=["terceiro-nivel", "slug-repetido", "sem-letra"],
)
def test_criar_recusado_e_400(cliente, corpo):
    resposta = cliente.post("/api/categorias", json=corpo)

    assert resposta.status_code == 400
    assert resposta.json()["detail"]


def test_criar_com_pai_inexistente_e_404(cliente):
    resposta = cliente.post("/api/categorias", json={"nome": "X", "parent_slug": "nao-existe"})

    assert resposta.status_code == 404
    assert "nao-existe" in resposta.json()["detail"]


def test_renomear_mantem_os_vinculos(com_produtos, banco):
    resposta = com_produtos.patch("/api/categorias/vegetais", json={"nome": "Hortaliças"})

    assert resposta.status_code == 200
    assert resposta.json() == {"slug": "vegetais", "nome": "Hortaliças", "parent_slug": None}
    assert produto(banco, TOMATE)[1] == "vegetais"


def test_mover_os_vinculos_seguem_e_null_sobe_para_nivel_1(com_produtos, banco):
    movida = com_produtos.patch(
        "/api/categorias/mercado-mercearia", json={"parent_slug": "vegetais"}
    )

    assert movida.json()["parent_slug"] == "vegetais"
    assert _no(com_produtos.get("/api/categorias").json(), "mercado-mercearia")[1] == "vegetais"
    assert produto(banco, ACHOCOLATADO)[1] == "mercado-mercearia"

    subida = com_produtos.patch("/api/categorias/mercado-mercearia", json={"parent_slug": None})

    assert subida.json()["parent_slug"] is None
    assert _no(com_produtos.get("/api/categorias").json(), "mercado-mercearia")[1] is None


def test_patch_sem_parent_slug_nao_move(com_produtos):
    com_produtos.patch("/api/categorias/mercado-mercearia", json={"nome": "Secos"})

    assert _no(com_produtos.get("/api/categorias").json(), "mercado-mercearia")[1] == "mercado"


def test_apagar_manda_os_produtos_para_o_bucket(com_produtos, banco):
    """`mercado-mercearia` e folha; `vegetais` nao serviria — tem subcategorias no seed."""
    resposta = com_produtos.delete("/api/categorias/mercado-mercearia")

    assert resposta.status_code == 204
    assert produto(banco, ACHOCOLATADO)[1:] == ("uncategorized", None)
    assert _no(com_produtos.get("/api/categorias").json(), "mercado-mercearia") == (None, None)


@pytest.mark.parametrize(
    ("metodo", "slug", "status"),
    [
        ("delete", "uncategorized", 400),
        ("delete", "mercado", 400),
        ("delete", "nao-existe", 404),
        ("patch", "nao-existe", 404),
    ],
    ids=["apagar-bucket", "apagar-com-filhas", "apagar-inexistente", "patch-inexistente"],
)
def test_edicao_recusada(cliente, metodo, slug, status):
    if metodo == "delete":
        resposta = cliente.delete(f"/api/categorias/{slug}")
    else:
        resposta = cliente.patch(f"/api/categorias/{slug}", json={"nome": "X"})

    assert resposta.status_code == status
    # ⚠️ a mensagem vem do nucleo; o "Not Found" generico seria uma rota que nem existe
    assert slug in resposta.json()["detail"]

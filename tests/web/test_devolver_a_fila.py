"""Devolver um produto a fila de revisao — spec 03 §5 e C15; spec 02 §4.

Decisao do Gui de 2026-10-16 (mockup em `docs/mockups/rodada-01-devolver-a-fila.html`).
Ele escolhe "↩ Nao Classificado (voltar a fila)" no seletor, e o produto vai para
o bucket com `origem='manual'`: a fila o mostra, e a cascata (NCM, LLM) nao mexe
mais nele ate o Gui escolher uma categoria.

🔴 Por que `manual`, e nao `origem` NULL: com NULL, a proxima importacao rodaria
o NCM de novo e poria o produto de volta na categoria que o Gui acabou de recusar.
"""

import re

import pytest
from fastapi.testclient import TestClient

from nfe_parser.web.app import criar_app
from tests.apoio import ACHOCOLATADO, LlmEspiao, chave, enviar, produto, texto, variante

VOLTAR = "↩ Não Classificado (voltar à fila)"


@pytest.fixture
def achocolatado(cliente, banco):
    """A NFC-e do ACHOCOLATADO, que o NCM poe em Mercearia. Devolve o id do produto."""
    assert enviar(cliente, "nota.xml", texto("nfe_65_1item.xml")).status_code == 201
    produto_id, slug, origem = produto(banco, ACHOCOLATADO)
    assert (slug, origem) == ("mercado-mercearia", "ncm")
    return produto_id


def _devolver(cliente, produto_id):
    return cliente.post(
        f"/api/produtos/{produto_id}/categoria", json={"categoria_slug": "uncategorized"}
    )


def _fila(cliente, classificado):
    corpo = cliente.get("/api/produtos", params={"classificado": classificado}).json()
    return [p["descricao_exemplo"] for p in corpo["produtos"]]


def _linha(html, produto_id):
    marca = f'id="produto-{produto_id}"'
    assert marca in html, "o produto nao esta nesta pagina"
    return html.split(marca, 1)[1].split("</tr>", 1)[0]


def _opcoes(linha):
    """`[(value, atributos, texto)]` de cada `<option>` da linha, na ordem."""
    return re.findall(r'<option value="([^"]*)"([^>]*)>([^<]*)</option>', linha)


# --- API -----------------------------------------------------------------------


def test_devolvido_entra_na_fila_e_sai_dos_classificados(cliente, achocolatado):
    resposta = _devolver(cliente, achocolatado)

    assert resposta.status_code == 200
    assert (resposta.json()["categoria_slug"], resposta.json()["origem"]) == (
        "uncategorized",
        "manual",
    )
    assert _fila(cliente, "false") == [ACHOCOLATADO]
    assert _fila(cliente, "true") == []


def test_proxima_importacao_nao_reclassifica_o_devolvido(cliente, banco, achocolatado):
    """Guarda: ja passa antes da mudanca (o degrau 1 protege `manual`) e TEM de
    continuar passando — e ela que justifica `manual` em vez de NULL."""
    _devolver(cliente, achocolatado)

    enviar(cliente, "outra.xml", variante("nfe_65_1item.xml", chave(1)))  # mesmo GTIN

    assert produto(banco, ACHOCOLATADO)[1:] == ("uncategorized", "manual")


def test_llm_nao_e_chamado_para_o_devolvido(caminho_banco):
    """Guarda, como a de cima: o botao do LLM so varre `origem` NULL."""
    espiao = LlmEspiao(resposta=("bebidas", 0.99))
    cliente = TestClient(criar_app(caminho_banco, llm=espiao))
    enviar(cliente, "nota.xml", texto("nfe_65_1item.xml"))
    (achocolatado,) = cliente.get("/api/produtos").json()["produtos"]
    _devolver(cliente, achocolatado["id"])

    cliente.post("/api/llm/classificar")

    assert espiao.chamadas == []


# --- tela ----------------------------------------------------------------------


def test_produto_fora_da_fila_tem_voltar_a_fila_como_primeira_opcao(cliente, achocolatado):
    html = cliente.get("/revisar", params={"todos": "true"}).text

    opcoes = _opcoes(_linha(html, achocolatado))

    assert [valor for valor, _, _ in opcoes[:2]] == ["", "uncategorized"]
    assert opcoes[1][2] == VOLTAR


@pytest.mark.parametrize("todos", ["false", "true"], ids=["fila", "ver-todos"])
def test_produto_na_fila_nao_tem_voltar_a_fila_nem_bucket_pre_selecionado(
    cliente, achocolatado, todos
):
    _devolver(cliente, achocolatado)
    html = cliente.get("/revisar", params={"todos": todos}).text

    opcoes = _opcoes(_linha(html, achocolatado))

    assert "uncategorized" not in [valor for valor, _, _ in opcoes]
    assert not any("selected" in atributos for _, atributos, _ in opcoes)


def test_devolver_pela_tela_marca_devolvido_por_voce_e_aparece_na_fila(cliente, achocolatado):
    resposta = cliente.post(
        f"/revisar/{achocolatado}",
        data={"categoria_slug": "uncategorized"},
        headers={"HX-Request": "true"},
    )

    assert resposta.status_code == 200
    assert "devolvido por você" in resposta.text
    assert "devolvido por você" in _linha(cliente.get("/revisar").text, achocolatado)


def test_topo_da_fila_diz_que_ela_guarda_os_devolvidos(cliente):
    assert "os que você devolveu" in cliente.get("/revisar").text

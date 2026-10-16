"""O NCM vence o LLM, de ponta a ponta pelo app — spec 02 §4 e §7.3 item 2.

O cenario do Gui: o LLM classificou um produto; uma versao nova do app traz uma
ancora NCM que o cobre; na proxima importacao, o produto vai para a categoria do
NCM. A "versao nova" e simulada inserindo a ancora direto no banco.
"""

from fastapi.testclient import TestClient

from nfe_parser.web.app import criar_app
from tests.apoio import ACHOCOLATADO, LlmEspiao, chave, enviar, produto, variante

NCM_SEM_ANCORA = ("18069000", "99999999")


def _confianca(banco, descricao):
    return banco.execute(
        "SELECT confianca FROM produtos WHERE descricao_exemplo = ?", (descricao,)
    ).fetchone()[0]


def test_proxima_importacao_passa_o_produto_do_llm_para_a_ancora_nova(caminho_banco, banco):
    espiao = LlmEspiao(resposta=("bebidas", 0.9))
    cliente = TestClient(criar_app(caminho_banco, llm=espiao))
    enviar(cliente, "a.xml", variante("nfe_65_1item.xml", chave(1), ncm=NCM_SEM_ANCORA))
    cliente.post("/api/llm/classificar")
    assert produto(banco, ACHOCOLATADO)[1:] == ("bebidas", "llm")

    with banco:  # a "versao nova do seed": 99999999 passa a ter ancora
        banco.execute(
            "INSERT INTO ncm_ancora (prefixo, categoria_id)"
            " SELECT '99999999', id FROM categorias WHERE slug = 'mercado-mercearia'"
        )
    enviar(cliente, "b.xml", variante("nfe_65_1item.xml", chave(2), ncm=NCM_SEM_ANCORA))

    assert produto(banco, ACHOCOLATADO)[1:] == ("mercado-mercearia", "ncm")
    assert _confianca(banco, ACHOCOLATADO) is None
    assert espiao.chamadas == [ACHOCOLATADO]  # so a primeira vez; o NCM nao chama o LLM


def test_botao_do_llm_tambem_reancora(caminho_banco, banco):
    espiao = LlmEspiao(resposta=("bebidas", 0.9))
    cliente = TestClient(criar_app(caminho_banco, llm=espiao))
    enviar(cliente, "a.xml", variante("nfe_65_1item.xml", chave(1), ncm=NCM_SEM_ANCORA))
    cliente.post("/api/llm/classificar")
    with banco:
        banco.execute(
            "INSERT INTO ncm_ancora (prefixo, categoria_id)"
            " SELECT '99999999', id FROM categorias WHERE slug = 'mercado-mercearia'"
        )

    cliente.post("/api/llm/classificar")

    assert produto(banco, ACHOCOLATADO)[1:] == ("mercado-mercearia", "ncm")
    assert espiao.chamadas == [ACHOCOLATADO]

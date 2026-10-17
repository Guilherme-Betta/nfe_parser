"""Ollama fora do ar: aviso na tela, nada gravado — spec 03 §5 e C16.

Decisao do Gui de 2026-10-16. Antes, "Sugerir com o LLM" com o Ollama desligado
dava uma pagina de erro 500.
"""

import pytest
from fastapi.testclient import TestClient

from nfe_parser.llm import LlmIndisponivel
from nfe_parser.web.app import criar_app
from tests.apoio import ACHOCOLATADO, TOMATE, chave, enviar, produto, variante

AVISO = "Não consegui falar com o Ollama em http://ollama.invalido:11434"


class LlmQueCai:
    """Responde `resposta` as primeiras `respostas_ate_cair` perguntas, depois cai."""

    def __init__(self, respostas_ate_cair=0, resposta=("bebidas", 0.9)):
        self.restantes = respostas_ate_cair
        self.resposta = resposta

    def __call__(self, descricao, slugs):
        if self.restantes == 0:
            raise LlmIndisponivel(AVISO)
        self.restantes -= 1
        return self.resposta


@pytest.fixture
def dois_pendentes(caminho_banco):
    """Um app cujo LLM responde UMA vez e cai, com ACHOCOLATADO e TOMATE pendentes."""
    cliente = TestClient(criar_app(caminho_banco, llm=LlmQueCai(respostas_ate_cair=1)))
    fora_do_mapa = variante("nfe_55_3itens.xml", chave(1), ncm=("18069000", "99999999")).replace(
        "<NCM>07020000</NCM>", "<NCM>99999999</NCM>"
    )
    assert enviar(cliente, "nota.xml", fora_do_mapa).status_code == 201
    return cliente


def _origens(banco):
    return produto(banco, ACHOCOLATADO)[2], produto(banco, TOMATE)[2]


def test_tela_volta_com_o_aviso_e_503(dois_pendentes, banco):
    resposta = dois_pendentes.post("/revisar/llm")

    assert resposta.status_code == 503
    assert AVISO in resposta.text
    assert "Revisar produtos" in resposta.text


def test_nada_e_gravado_mesmo_o_que_o_llm_respondeu_antes_de_cair(dois_pendentes, banco):
    """O LLM respondeu pelo primeiro produto e caiu no segundo: o primeiro TAMBEM
    nao e gravado — a varredura e uma transacao so."""
    dois_pendentes.post("/revisar/llm")

    assert _origens(banco) == (None, None)


def test_api_responde_503_com_a_mensagem(dois_pendentes, banco):
    resposta = dois_pendentes.post("/api/llm/classificar")

    assert resposta.status_code == 503
    assert AVISO in resposta.json()["detail"]
    assert _origens(banco) == (None, None)

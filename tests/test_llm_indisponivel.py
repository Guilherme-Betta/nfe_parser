"""Ollama fora do ar vira `LlmIndisponivel`, com a URL — spec 02 §7.2.

O erro continua SUBINDO (quem ligou o LLM precisa saber na hora), mas com um nome
proprio e uma mensagem que diz onde o app tentou falar. E isso que deixa a tela
de revisao mostrar um aviso em vez de uma pagina de erro 500 (spec 03 C16).
"""

import urllib.error

import pytest

from nfe_parser.llm import LlmIndisponivel, criar_llm

URL = "http://ollama.invalido:11434"


@pytest.mark.parametrize(
    "falha",
    [
        urllib.error.URLError(ConnectionRefusedError("conexao recusada")),
        TimeoutError("demorou demais"),
        ConnectionResetError("conexao caiu"),
    ],
    ids=["recusada", "timeout", "caiu"],
)
def test_falha_de_rede_vira_llm_indisponivel_com_a_url(monkeypatch, falha):
    def urlopen_falso(requisicao, timeout=None):
        raise falha

    monkeypatch.setattr("urllib.request.urlopen", urlopen_falso)
    llm = criar_llm(URL, "modelo-x", 0.5)

    with pytest.raises(LlmIndisponivel, match="ollama.invalido:11434"):
        llm("MACA FUJI KG", ["mercado-frutas"])

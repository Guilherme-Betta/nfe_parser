"""`LLM_LIMIAR` fora de 0..1 derruba a subida — spec 02 §7.2 e §7.3 item 4.

Um limiar `2` deixava o LLM ligado sem nunca classificar nada, e sem erro: a
confianca do LLM vai de 0 a 1, entao nenhuma resposta passaria. Configuracao
invalida falha cedo, com a mensagem, como as outras variaveis obrigatorias.
"""

import pytest

from nfe_parser.llm import llm_do_ambiente


@pytest.fixture
def ambiente_do_llm(monkeypatch):
    monkeypatch.setenv("OLLAMA_URL", "http://ollama.invalido:11434")
    monkeypatch.setenv("OLLAMA_MODELO", "modelo-x")
    return monkeypatch


@pytest.mark.parametrize("limiar", ["2", "-0.1", "1.01", "nan", "abc", "0,7"])
def test_limiar_que_nao_e_numero_entre_0_e_1_e_recusado_com_a_mensagem(ambiente_do_llm, limiar):
    ambiente_do_llm.setenv("LLM_LIMIAR", limiar)

    with pytest.raises(ValueError, match="LLM_LIMIAR"):
        llm_do_ambiente()


@pytest.mark.parametrize("limiar", ["0", "1", "0.7"])
def test_limiar_entre_0_e_1_inclusive_e_aceito(ambiente_do_llm, limiar):
    ambiente_do_llm.setenv("LLM_LIMIAR", limiar)

    assert callable(llm_do_ambiente())

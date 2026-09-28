"""Testes da conversa com o LLM — story 012, tarefa 1.

🔴 O PORQUE de cada criterio mora em `specs/012-llm-eval/spec.md` §4 (bloco C1)
e §3 (decisoes D2-D5). ⛔ Nao o repita aqui: aquela spec NAO e enviada ao modelo
local, e este arquivo e.

Congelados por commit ANTES da implementacao; o modelo local le (`--read`).

⛔ Nenhum teste daqui fala com um Ollama de verdade. O C1.7 troca
`urllib.request.urlopen` por uma funcao falsa: o que se testa e o CONTRATO da
resposta, e nao o modelo.
"""

import json

import pytest

from nfe_parser.llm import criar_llm, interpretar_resposta, llm_do_ambiente, montar_prompt

SLUGS = ["bebidas", "mercado-frutas"]


def _resposta(categoria, confianca):
    return json.dumps({"categoria": categoria, "confianca": confianca})


# --- C1.1 -------------------------------------------------------------------
def test_resposta_valida_acima_do_limiar_e_aceita():
    assert interpretar_resposta(_resposta("bebidas", 0.9), SLUGS, 0.5) == ("bebidas", 0.9)


# --- C1.2 -------------------------------------------------------------------
def test_nao_sei_devolve_none():
    assert interpretar_resposta(_resposta("nao_sei", 0.99), SLUGS, 0.0) is None


# --- C1.3 -------------------------------------------------------------------
def test_categoria_fora_da_lista_devolve_none():
    """O invariante da spec 02: o LLM nunca inventa categoria. `cafeteria` e uma
    categoria plausivel, e mesmo assim nao foi enviada."""
    assert interpretar_resposta(_resposta("cafeteria", 0.99), SLUGS, 0.0) is None


# --- C1.4 -------------------------------------------------------------------
def test_confianca_abaixo_do_limiar_e_recusada_e_igual_e_aceita():
    assert interpretar_resposta(_resposta("bebidas", 0.49), SLUGS, 0.5) is None
    assert interpretar_resposta(_resposta("bebidas", 0.5), SLUGS, 0.5) == ("bebidas", 0.5)


# --- C1.5 -------------------------------------------------------------------
def test_resposta_malformada_devolve_none_sem_levantar():
    """`True` e `int` em Python — e `True >= 0.5` e verdadeiro. Sem a guarda de
    `bool`, um modelo que responde `"confianca": true` passaria pelo limiar.

    Um laco, e nao `parametrize`: cada caso contaria como teste (Achado N)."""
    malformadas = {
        "nao-json": "isto nao e json",
        "none": None,
        "json-lista": json.dumps(["bebidas", 0.9]),
        "confianca-texto": _resposta("bebidas", "alta"),
        "confianca-bool": _resposta("bebidas", True),
        "acima-de-1": _resposta("bebidas", 1.5),
        "negativa": _resposta("bebidas", -0.1),
        "sem-confianca": json.dumps({"categoria": "bebidas"}),
    }
    for caso, texto in malformadas.items():
        assert interpretar_resposta(texto, SLUGS, 0.0) is None, caso


# --- C1.6 -------------------------------------------------------------------
def test_o_prompt_leva_a_descricao_os_slugs_e_a_saida_nao_sei():
    prompt = montar_prompt("MACA FUJI KG", SLUGS)

    assert "MACA FUJI KG" in prompt
    for slug in SLUGS:
        assert slug in prompt
    assert "nao_sei" in prompt


# --- C1.7 -------------------------------------------------------------------
class _RespostaFalsa:
    def __init__(self, corpo):
        self._corpo = corpo

    def read(self):
        return self._corpo

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_criar_llm_faz_post_no_ollama_e_interpreta_a_resposta(monkeypatch):
    enviadas = []

    def urlopen_falso(requisicao, timeout=None):
        enviadas.append(requisicao)
        corpo = json.dumps({"response": _resposta("mercado-frutas", 0.8)}).encode("utf-8")
        return _RespostaFalsa(corpo)

    monkeypatch.setattr("urllib.request.urlopen", urlopen_falso)

    llm = criar_llm("http://ollama.invalido:11434/", "modelo-x", 0.5)

    assert llm("MACA FUJI KG", SLUGS) == ("mercado-frutas", 0.8)
    assert len(enviadas) == 1
    assert enviadas[0].full_url == "http://ollama.invalido:11434/api/generate"
    corpo = json.loads(enviadas[0].data.decode("utf-8"))
    assert corpo["model"] == "modelo-x"
    assert corpo["stream"] is False
    assert corpo["format"] == "json"
    assert "MACA FUJI KG" in corpo["prompt"]


# --- C1.8 -------------------------------------------------------------------
def test_llm_do_ambiente_desligado_sem_url_e_sem_padrao_para_modelo_ou_limiar(monkeypatch):
    """⛔ Nao existe limiar padrao nem modelo padrao: um padrao seria um numero
    escolhido por nos. Quem liga o LLM diz os dois."""
    for nome in ("OLLAMA_URL", "OLLAMA_MODELO", "LLM_LIMIAR"):
        monkeypatch.delenv(nome, raising=False)

    assert llm_do_ambiente() is None

    monkeypatch.setenv("OLLAMA_URL", "http://ollama.invalido:11434")
    monkeypatch.setenv("OLLAMA_MODELO", "modelo-x")
    with pytest.raises(ValueError):
        llm_do_ambiente()

    monkeypatch.delenv("OLLAMA_MODELO")
    monkeypatch.setenv("LLM_LIMIAR", "0.5")
    with pytest.raises(ValueError):
        llm_do_ambiente()

    monkeypatch.setenv("OLLAMA_MODELO", "modelo-x")
    assert callable(llm_do_ambiente())

import json
import os
import urllib.request

def montar_prompt(descricao, slugs):
    lista = "\n".join(f"- {slug}" for slug in slugs)
    return (
        "Voce classifica produtos de notas fiscais brasileiras.\n"
        "Escolha UMA categoria da lista para o produto.\n"
        "Se nenhuma servir, ou se voce nao souber, responda nao_sei.\n\n"
        f"Categorias:\n{lista}\n\n"
        f"Produto: {descricao}\n\n"
        'Responda SO com JSON: {"categoria": "<uma da lista ou nao_sei>", '
        '"confianca": <numero de 0 a 1>}'
    )

def interpretar_resposta(texto, slugs, limiar):
    try:
        dados = json.loads(texto)
    except (ValueError, TypeError):
        return None

    if not isinstance(dados, dict):
        return None

    categoria = dados.get("categoria")
    if categoria not in slugs:
        return None

    confianca = dados.get("confianca")
    if isinstance(confianca, bool) or not isinstance(confianca, (int, float)):
        return None

    if not (0 <= confianca <= 1):
        return None

    if confianca < limiar:
        return None

    return (categoria, float(confianca))

def perguntar_ao_ollama(prompt, url, modelo):
    corpo = json.dumps(
        {
            "model": modelo,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0},
        }
    ).encode("utf-8")
    requisicao = urllib.request.Request(
        url.rstrip("/") + "/api/generate",
        data=corpo,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(requisicao, timeout=120) as resposta:
        return json.loads(resposta.read().decode("utf-8"))["response"]

def criar_llm(url, modelo, limiar):
    def llm(descricao, slugs):
        texto = perguntar_ao_ollama(montar_prompt(descricao, slugs), url, modelo)
        return interpretar_resposta(texto, slugs, limiar)

    return llm

def llm_do_ambiente():
    url = os.environ.get("OLLAMA_URL")
    if not url:
        return None

    modelo = os.environ.get("OLLAMA_MODELO")
    if not modelo:
        raise ValueError("Variavel de ambiente OLLAMA_MODELO não definida")

    limiar = os.environ.get("LLM_LIMIAR")
    if not limiar:
        raise ValueError("Variavel de ambiente LLM_LIMIAR não definida")

    return criar_llm(url, modelo, float(limiar))

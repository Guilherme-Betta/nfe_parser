"""A conversa com o LLM: montar a pergunta, mandar ao Ollama, e decidir em que acreditar.

Implementa o degrau 3 da cascata da spec 02 (§4) do lado do MODELO. ⛔ Este modulo
nao sabe o que e um banco: ele recebe uma descricao e uma lista de slugs, e
devolve `(slug, confianca)` ou `None`. Quem confere no banco e grava e
`categorizacao.py`.

⭐ O contrato que sai daqui e uma funcao `llm(descricao, slugs)`, e ele e o que
torna o LLM OPT-IN: quem nao constroi um `llm` nao tem LLM nenhum, e a cascata
fica so com NCM e bucket. Nenhum modulo le variavel de ambiente sozinho no meio
da classificacao.

🔴 `None` quer dizer "nao sei", venha de onde vier: o modelo disse `nao_sei`,
inventou categoria, mandou JSON quebrado, ou respondeu com pouca confianca.
Quem recebe nao precisa distinguir, e e por isso que nao distingue.

⛔ Nenhum limiar e nenhum modelo tem valor padrao aqui, e nao e esquecimento: um
padrao seria um numero escolhido por nos. Quem liga o LLM diz os dois, e o eval
(`eval_llm.py`) e o que da base para escolher.
"""

import json
import os
import urllib.request


def montar_prompt(descricao, slugs):
    """Monta a pergunta. A lista de slugs vai inteira, uma por linha.

    ⚠️ Pedir JSON no texto nao basta: e o `"format": "json"` de
    `perguntar_ao_ollama` que obriga o Ollama a devolver JSON valido. O texto
    diz QUAL JSON — e `nao_sei` e a saida honesta que a spec 02 exige existir.
    """

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
    """Devolve `(categoria, confianca)` se a resposta passou em TUDO; senao `None`.

    Nunca levanta: resposta ruim de modelo e caso normal, nao erro de programa.

    🔴 `categoria not in slugs` e a regra que sustenta o invariante "o LLM nunca
    inventa categoria". O `"format": "json"` do Ollama restringe a saida a JSON,
    ⛔ mas nao restringe a categoria a lista. E ela ja cobre `nao_sei`, que nunca
    esta na lista — por isso nao ha regra propria para ele.

    ⚠️ A guarda de `bool` nao e excesso: em Python `True` E `int`, e `True >=
    0.5` e verdadeiro. Sem ela, um modelo que respondesse `"confianca": true`
    passaria por qualquer limiar.

    ⭐ O limiar mora aqui, e nao em quem grava. Gravar e politica do banco;
    acreditar e politica da resposta. E e aqui que o eval precisa dele, porque o
    eval chama o mesmo `llm` que a producao. Igual ao limiar e aceito.
    """

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
    """Faz o `POST /api/generate` e devolve o texto que o modelo respondeu.

    So biblioteca padrao: nenhuma dependencia nova no `pyproject.toml`.

    `temperature: 0` pede a mesma resposta para a mesma pergunta — e o que faz o
    eval ser repetivel. `stream: False` faz a resposta chegar num JSON so.

    🔴 Erro de rede SOBE, de proposito. Quem ligou o LLM e apontou para um
    Ollama fora do ar precisa saber na hora — ⛔ e nao descobrir semanas depois
    que tudo foi para o bucket em silencio.

    ⚠️ O teste troca `urllib.request.urlopen` pelo NOME. Um
    `from urllib.request import urlopen` no topo escaparia da troca, e o teste
    tentaria falar com a rede.
    """

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
    """Fecha URL, modelo e limiar numa funcao `llm(descricao, slugs)`.

    ⭐ E o formato que a cascata (`categorizacao.py`), a varredura e o eval
    esperam. Nos testes, qualquer funcao Python com essa assinatura serve — e e
    isso que permite testar o degrau sem Ollama nenhum.
    """

    def llm(descricao, slugs):
        texto = perguntar_ao_ollama(montar_prompt(descricao, slugs), url, modelo)
        return interpretar_resposta(texto, slugs, limiar)

    return llm


def llm_do_ambiente():
    """Constroi o `llm` a partir de `OLLAMA_URL`, `OLLAMA_MODELO` e `LLM_LIMIAR`.

    Sem `OLLAMA_URL`, devolve `None`: o LLM esta DESLIGADO, e isso nao e erro.

    🔴 Com `OLLAMA_URL` e sem uma das outras duas, levanta `ValueError`. ⛔ Nao
    ha modelo padrao nem limiar padrao — ver o cabecalho. Configuracao pela
    metade e erro de quem configurou, e falhar alto e melhor que classificar com
    um numero que ninguem escolheu.

    📋 O repositorio documenta os NOMES destas variaveis. ⛔ Nenhum valor, nenhum
    `.env`.
    """

    url = os.environ.get("OLLAMA_URL")
    if not url:
        return None

    modelo = os.environ.get("OLLAMA_MODELO")
    if not modelo:
        raise ValueError("Variavel de ambiente OLLAMA_MODELO não definida")

    limiar = os.environ.get("LLM_LIMIAR")
    if not limiar:
        raise ValueError("Variavel de ambiente LLM_LIMIAR não definida")

    return criar_llm(url, modelo, _limiar_valido(limiar))


def _limiar_valido(texto):
    """O `LLM_LIMIAR` como numero entre 0 e 1, ou `ValueError` que diz o que esta errado.

    🔴 A confianca do LLM vai de 0 a 1. Um limiar `2` deixaria o LLM ligado sem que
    resposta nenhuma passasse — e sem erro nenhum. ⚠️ `float("nan")` nao levanta, e
    toda comparacao com NaN da falso: por isso a faixa e conferida com `0 <= x <= 1`,
    que recusa o NaN, e nao com dois `if` de "menor que 0" e "maior que 1".
    """
    erro = f"LLM_LIMIAR={texto!r}: tem de ser um numero entre 0 e 1, com ponto (ex.: 0.7)"
    try:
        limiar = float(texto)
    except ValueError:
        raise ValueError(erro) from None
    if not 0 <= limiar <= 1:
        raise ValueError(erro)
    return limiar

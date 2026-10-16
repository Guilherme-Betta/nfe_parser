O arquivo `src/nfe_parser/llm.py` E NOVO e esta VAZIO. Voce escreve o arquivo inteiro. Ele tem TRES
imports e CINCO funcoes, NESTA ORDEM. Nada mais.


OS IMPORTS

```python
import json
import os
import urllib.request
```

NAO escreva `from urllib.request import urlopen`. O teste troca `urllib.request.urlopen` por uma
funcao falsa, e isso so funciona se o codigo chamar `urllib.request.urlopen(...)` ESCRITO ASSIM.


FUNCAO 1 -- `montar_prompt(descricao, slugs) -> str`

```python
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
```

Copie EXATAMENTE como esta.


FUNCAO 2 -- `interpretar_resposta(texto, slugs, limiar)`

Devolve a tupla `(categoria, confianca)` so se a resposta passar em TODAS as regras abaixo. Em
QUALQUER outro caso devolve `None`. Ela NUNCA levanta excecao.

1. `json.loads(texto)` funciona. Capture `ValueError` e `TypeError` e devolva `None`.
2. o resultado e um `dict`. Se nao for, `None`.
3. `categoria = dados.get("categoria")` esta DENTRO de `slugs`. Se nao estiver, `None`. Isso ja cobre
   `"nao_sei"`, que nunca esta na lista. NAO escreva regra propria para `"nao_sei"`.
4. `confianca = dados.get("confianca")` e `int` ou `float`, e NAO e `bool`. Escreva assim:
   `if isinstance(confianca, bool) or not isinstance(confianca, (int, float)): return None`
5. `0 <= confianca <= 1`. Se nao, `None`.
6. `confianca >= limiar`. Se nao, `None`. IGUAL ao limiar e ACEITO.

No fim: `return (categoria, float(confianca))`.


FUNCAO 3 -- `perguntar_ao_ollama(prompt, url, modelo) -> str`

```python
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
```

Copie EXATAMENTE como esta. NAO ponha `try`/`except` em volta: erro de rede TEM DE SUBIR.


FUNCAO 4 -- `criar_llm(url, modelo, limiar)`

Devolve uma FUNCAO. A funcao devolvida recebe `(descricao, slugs)`, monta o prompt, pergunta ao
Ollama e interpreta a resposta:

```python
def criar_llm(url, modelo, limiar):
    def llm(descricao, slugs):
        texto = perguntar_ao_ollama(montar_prompt(descricao, slugs), url, modelo)
        return interpretar_resposta(texto, slugs, limiar)

    return llm
```


FUNCAO 5 -- `llm_do_ambiente()`

Le tres variaveis de ambiente com `os.environ.get`: `OLLAMA_URL`, `OLLAMA_MODELO` e `LLM_LIMIAR`.

1. `OLLAMA_URL` vazia ou ausente -> `return None`. Isto NAO e erro: o LLM esta desligado.
2. `OLLAMA_URL` definida, mas `OLLAMA_MODELO` vazia ou ausente -> `raise ValueError(...)`.
3. `OLLAMA_URL` definida, mas `LLM_LIMIAR` vazia ou ausente -> `raise ValueError(...)`.
4. senao -> `return criar_llm(url, modelo, float(limiar))`.

NAO invente valor padrao para o modelo. NAO invente valor padrao para o limiar. NENHUM numero de
limiar aparece neste arquivo.


O QUE NAO PODE ENTRAR

NAO acesse banco de dados. NAO importe `sqlite3`. NAO importe nada de `nfe_parser`.
NAO importe `requests` nem `httpx`: so a biblioteca padrao.
NAO escreva `print`, `logging`, `if __name__ == "__main__"` nem argparse.
NAO escreva constante, lista ou dicionario no nivel do modulo.

NAO altere nenhum outro arquivo do projeto, e NAO altere teste nenhum. O unico arquivo que voce
escreve e `src/nfe_parser/llm.py`. Se qualquer outro arquivo aparecer nesta conversa, DEIXE-O
EXATAMENTE COMO ESTA.

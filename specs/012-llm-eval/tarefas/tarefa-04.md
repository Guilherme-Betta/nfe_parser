O arquivo `src/nfe_parser/eval_llm.py` E NOVO e esta VAZIO. Voce escreve o arquivo inteiro. Ele tem
UM import, UMA constante e TRES funcoes. Nada mais.


O IMPORT E A CONSTANTE

```python
import csv

BUCKET = "uncategorized"
```


FUNCAO 1 -- `carregar_gold(caminho)`

Le um CSV com cabecalho `descricao;esperado`. O separador e `;`. Devolve uma lista de tuplas
`(descricao, esperado)`. `esperado` vazio vira `None`.

```python
def carregar_gold(caminho):
    with open(caminho, encoding="utf-8-sig", newline="") as arquivo:
        leitor = csv.DictReader(arquivo, delimiter=";")
        return [(linha["descricao"], linha["esperado"] or None) for linha in leitor]
```

O `utf-8-sig` e de proposito: o Excel grava BOM. NAO troque por `utf-8`.


FUNCAO 2 -- `prever(gold, llm, slugs)`

Para CADA tupla do `gold`, chama `llm(descricao, slugs)`. O `llm` devolve `None` ou uma tupla
`(slug, confianca)`. Guarde `None` quando vier `None`, e SO O SLUG quando vier tupla. Devolva a lista,
na MESMA ordem do `gold`.

```python
def prever(gold, llm, slugs):
    predicoes = []
    for descricao, _esperado in gold:
        resposta = llm(descricao, slugs)
        predicoes.append(resposta[0] if resposta is not None else None)
    return predicoes
```


FUNCAO 3 -- `avaliar(gold, predicoes)`

`gold` e a lista de `(descricao, esperado)`. `predicoes` e a lista de slug-ou-`None`, na mesma ordem.

PASSO 1 -- se `len(gold) != len(predicoes)`, `raise ValueError(...)`.

PASSO 2 -- percorra os dois juntos com `zip`. Para cada par:

(a) se `esperado is None`: a linha e FORA DA TAXONOMIA. Some `1` em `fora_total`. Se `previsto is
None`, some `1` em `fora_no_bucket`. Depois `continue`. Esta linha NAO entra em mais nada.

(b) senao: `previsto_chave = previsto if previsto is not None else BUCKET`. Some `1` em `avaliados`.
Se `previsto is None`, some `1` em `no_bucket`. A linha ACERTOU quando `previsto_chave == esperado`;
nesse caso some `1` em `acertos`.

(c) ainda no caso (b), atualize `por_categoria[esperado]`, que e um dicionario
`{"total": ..., "acertos": ...}`: some `1` em `"total"`, e `1` em `"acertos"` se acertou.

(d) ainda no caso (b), atualize `matriz[esperado][previsto_chave]`, somando `1`. `matriz` e um
dicionario de dicionarios. Use `setdefault` para criar as chaves que faltam.

PASSO 3 -- depois do laco, para CADA categoria de `por_categoria`, acrescente
`"acuracia": acertos / total`.

PASSO 4 -- devolva ESTE dicionario, com ESTAS chaves:

```python
    return {
        "avaliados": avaliados,
        "acertos": acertos,
        "acuracia": acertos / avaliados if avaliados else None,
        "taxa_no_bucket": no_bucket / avaliados if avaliados else None,
        "por_categoria": por_categoria,
        "matriz": matriz,
        "fora_da_taxonomia": {"total": fora_total, "no_bucket": fora_no_bucket},
    }
```


REGRA 1 -- `avaliados` NAO conta as linhas de `esperado` `None`. E por isso que o passo 2(a) faz
`continue`. Essas linhas so aparecem em `"fora_da_taxonomia"`.


REGRA 2 -- NENHUMA CHAVE `None` EM DICIONARIO. Previsao `None` entra na matriz como `BUCKET`, que e a
string `"uncategorized"`. O resultado tem de passar por `json.dumps`.


REGRA 3 -- NENHUM LIMIAR. NENHUMA APROVACAO. A funcao NAO decide se o resultado e bom: ela so conta.
NAO escreva `if acuracia > ...`, NAO escreva `"aprovado"`, NAO escreva nenhum numero alem de `0` e `1`.


O QUE NAO PODE ENTRAR

NAO importe nada alem de `csv`. NAO acesse banco de dados. NAO chame o Ollama: o `llm` chega pronto,
por parametro. NAO escreva `print`, `if __name__ == "__main__"` nem argparse.

NAO altere nenhum outro arquivo do projeto, e NAO altere teste nenhum. O unico arquivo que voce
escreve e `src/nfe_parser/eval_llm.py`. Se qualquer outro arquivo aparecer nesta conversa, DEIXE-O
EXATAMENTE COMO ESTA.

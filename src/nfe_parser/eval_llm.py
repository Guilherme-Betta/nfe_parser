"""O harness de eval: medir o LLM contra um conjunto rotulado por uma pessoa.

Implementa o invariante do eval da spec 02 (§6): acuracia por categoria, matriz
de confusao e fracao que caiu no bucket.

🔴 ⛔ ESTE MODULO NAO TEM LIMIAR DE APROVACAO, e nao deve ganhar um. A spec diz
"Bar de aprovacao: chamada do Gui apos ver os numeros". O harness e um
instrumento de medida; quem decide se o LLM e ligado e uma pessoa.

⭐ O gold (o "gabarito") e um CSV com `descricao;esperado`. ⛔ Ele nao mora neste
repositorio, que e publico: sao compras reais. O harness le um CAMINHO. Os
testes usam gold sintetico, porque o que o kit verifica e a ARITMETICA.

⚠️ `esperado` vazio quer dizer "a taxonomia nao tem lugar para isto" — e essas
linhas ficam FORA da acuracia. O LLM nao tem como acertar uma categoria que nao
recebeu; conta-las mediria a taxonomia, e nao o LLM. Elas saem num numero
proprio, `fora_da_taxonomia`.

⚠️ O acerto e EXATO: esperado `mercado-laticinios` e previsto `mercado` e erro.
"Acerto no grupo" seria outra metrica, e nao foi inventada aqui.
"""

import csv

# O slug que a spec 02 fixou para o bucket. Previsao `None` entra na matriz com
# este nome, porque chave `None` em dicionario nao sobrevive ao JSON com sentido.
BUCKET = "uncategorized"


def carregar_gold(caminho):
    """Le o gold: CSV com cabecalho `descricao;esperado`. Vazio vira `None`.

    `;` e nao `,` porque e o que o Excel em portugues grava. `utf-8-sig` porque
    o Excel poe BOM no comeco — e com `utf-8` puro o cabecalho viraria
    `"\\ufeffdescricao"` e a primeira coluna nao seria achada pelo nome.
    """

    with open(caminho, encoding="utf-8-sig", newline="") as arquivo:
        leitor = csv.DictReader(arquivo, delimiter=";")
        return [(linha["descricao"], linha["esperado"] or None) for linha in leitor]


def prever(gold, llm, slugs):
    """Pergunta ao `llm` por cada linha do gold. Devolve slug ou `None`, em ordem.

    ⭐ O `llm` e o MESMO que a producao usa (`llm.criar_llm`), com o mesmo limiar:
    o eval mede o que de fato iria para o banco, e nao uma versao de laboratorio.
    """

    predicoes = []
    for descricao, _esperado in gold:
        resposta = llm(descricao, slugs)
        predicoes.append(resposta[0] if resposta is not None else None)
    return predicoes


def avaliar(gold, predicoes):
    """Conta. Devolve um dicionario que serializa em JSON; nao julga nada.

    | Chave | O que e |
    | ----- | ------- |
    | `avaliados` | linhas com `esperado` preenchido |
    | `acertos`, `acuracia` | sobre os `avaliados`; `None` se nao ha nenhum |
    | `taxa_no_bucket` | fracao dos `avaliados` que o LLM mandou ao bucket |
    | `por_categoria` | `{esperado: {"total", "acertos", "acuracia"}}` |
    | `matriz` | `{esperado: {previsto: contagem}}`, bucket como `"uncategorized"` |
    | `fora_da_taxonomia` | `{"total", "no_bucket"}` das linhas de `esperado` vazio |

    ⚠️ `por_categoria` agrupa pelo ESPERADO: responde "quando o certo era X,
    quantas vezes o LLM acertou". A matriz e quem mostra para onde foram os erros.

    ⛔ Tamanhos diferentes levantam `ValueError`. `zip` pararia no menor em
    silencio, e o eval mediria menos linhas do que o gold tem.
    """

    if len(gold) != len(predicoes):
        raise ValueError("O tamanho de gold e predicoes deve ser igual")

    avaliados = 0
    acertos = 0
    no_bucket = 0
    fora_total = 0
    fora_no_bucket = 0
    por_categoria = {}
    matriz = {}

    for (descricao, esperado), previsto in zip(gold, predicoes):
        if esperado is None:
            fora_total += 1
            if previsto is None:
                fora_no_bucket += 1
            continue

        avaliados += 1
        previsto_chave = previsto if previsto is not None else BUCKET
        if previsto is None:
            no_bucket += 1

        if previsto_chave == esperado:
            acertos += 1

        if esperado not in por_categoria:
            por_categoria[esperado] = {"total": 0, "acertos": 0}
        por_categoria[esperado]["total"] += 1
        if previsto_chave == esperado:
            por_categoria[esperado]["acertos"] += 1

        matriz.setdefault(esperado, {}).setdefault(previsto_chave, 0)
        matriz[esperado][previsto_chave] += 1

    for contagem in por_categoria.values():
        contagem["acuracia"] = contagem["acertos"] / contagem["total"]

    return {
        "avaliados": avaliados,
        "acertos": acertos,
        "acuracia": acertos / avaliados if avaliados else None,
        "taxa_no_bucket": no_bucket / avaliados if avaliados else None,
        "por_categoria": por_categoria,
        "matriz": matriz,
        "fora_da_taxonomia": {"total": fora_total, "no_bucket": fora_no_bucket},
    }

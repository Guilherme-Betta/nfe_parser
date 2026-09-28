import csv

BUCKET = "uncategorized"

def carregar_gold(caminho):
    with open(caminho, encoding="utf-8-sig", newline="") as arquivo:
        leitor = csv.DictReader(arquivo, delimiter=";")
        return [(linha["descricao"], linha["esperado"] or None) for linha in leitor]

def prever(gold, llm, slugs):
    predicoes = []
    for descricao, _esperado in gold:
        resposta = llm(descricao, slugs)
        predicoes.append(resposta[0] if resposta is not None else None)
    return predicoes

def avaliar(gold, predicoes):
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

    for categoria in por_categoria:
        por_categoria[categoria]["acuracia"] = por_categoria[categoria]["acertos"] / por_categoria[categoria]["total"]

    return {
        "avaliados": avaliados,
        "acertos": acertos,
        "acuracia": acertos / avaliados if avaliados else None,
        "taxa_no_bucket": no_bucket / avaliados if avaliados else None,
        "por_categoria": por_categoria,
        "matriz": matriz,
        "fora_da_taxonomia": {"total": fora_total, "no_bucket": fora_no_bucket},
    }

"""
rodar_eval.py -- roda o harness da story 012 contra um gold REAL e um Ollama de verdade.

===========================================================================
 O QUE ESTE ARQUIVO E
===========================================================================

As quatro pecas da story 012 (`llm.py`, o degrau, a varredura, `eval_llm.py`)
tem oraculo, e nenhum deles fala com um Ollama: e de proposito, porque um teste
que depende de servico rodando nao e oraculo. Este script e a cola que falta
para USAR o harness de verdade -- e por isso nao tem teste: sem Ollama, nao ha o
que testar; com Ollama, o resultado depende do modelo.

  ⛔ Ele NAO decide nada. Imprime numeros. Quem decide se o LLM e ligado, com
  que modelo e a partir de que limiar, e uma pessoa (spec 02, §6).

---------------------------------------------------------------------------
 COMO SE USA
---------------------------------------------------------------------------
    $env:OLLAMA_URL    = "http://localhost:11434"
    $env:OLLAMA_MODELO = "qwen2.5-coder:14b"
    $env:LLM_LIMIAR    = "0"
    python scripts/rodar_eval.py <caminho do gold.csv>

  ⭐ `LLM_LIMIAR=0` aceita toda resposta valida, e a saida traz a confianca de
  cada item. E a rodada para ESCOLHER o limiar: olhando quais erros vieram com
  confianca alta e quais acertos com baixa. Um limiar maior mede o que de fato
  iria para o banco com ele.

  ⛔ O gold NAO mora neste repositorio, que e publico: sao compras reais.

---------------------------------------------------------------------------
 A TAXONOMIA USADA
---------------------------------------------------------------------------
A do seed padrao, carregada num banco em memoria. E a lista que um banco novo
teria -- ⚠️ nao a de um banco em que alguem ja editou categorias.
"""

import argparse
import json
import sys

from nfe_parser.banco import abrir_banco
from nfe_parser.eval_llm import avaliar, carregar_gold, prever
from nfe_parser.llm import llm_do_ambiente
from nfe_parser.seed import carregar_seed_padrao


def slugs_da_taxonomia_padrao():
    """A mesma consulta do degrau: sem o bucket, em ordem."""
    conexao = abrir_banco(":memory:")
    try:
        carregar_seed_padrao(conexao)
        return [
            linha[0]
            for linha in conexao.execute(
                "SELECT slug FROM categorias WHERE is_bucket = 0 ORDER BY slug"
            ).fetchall()
        ]
    finally:
        conexao.close()


def main() -> int:
    ap = argparse.ArgumentParser(description="Roda o eval do LLM contra um gold real.")
    ap.add_argument("gold", help="caminho do CSV `descricao;esperado`")
    args = ap.parse_args()

    llm = llm_do_ambiente()
    if llm is None:
        print("ERRO: OLLAMA_URL nao definida -- o LLM esta desligado.", file=sys.stderr)
        return 1

    # Anota a resposta crua de cada chamada, para a saida trazer a confianca.
    # `prever` so devolve o slug, e e o que `avaliar` precisa; quem escolhe o
    # limiar precisa ver o numero.
    respostas = []

    def llm_que_anota(descricao, slugs):
        resposta = llm(descricao, slugs)
        respostas.append(resposta)
        return resposta

    gold = carregar_gold(args.gold)
    predicoes = prever(gold, llm_que_anota, slugs_da_taxonomia_padrao())

    resultado = avaliar(gold, predicoes)
    resultado["itens"] = [
        {
            "descricao": descricao,
            "esperado": esperado,
            "previsto": previsto,
            "confianca": resposta[1] if resposta is not None else None,
            "acertou": None if esperado is None else (previsto or "uncategorized") == esperado,
        }
        for (descricao, esperado), previsto, resposta in zip(gold, predicoes, respostas)
    ]

    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

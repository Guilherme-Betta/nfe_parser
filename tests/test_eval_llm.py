"""Testes do harness de eval — story 012, tarefa 4.

🔴 O PORQUE de cada criterio mora em `specs/012-llm-eval/spec.md` §4 (bloco C4)
e §3 (decisoes D10, D11). ⛔ Nao o repita aqui: aquela spec NAO e enviada ao
modelo local, e este arquivo e.

Congelados por commit ANTES da implementacao; o modelo local le (`--read`).

⭐ O gold daqui e SINTETICO, e e de proposito: o que o kit verifica e a
ARITMETICA do harness. ⛔ Se os numeros de um gold real sao bons, o kit nao
verifica — e o harness nao tem limiar nenhum.
"""

import json

import pytest

from nfe_parser.eval_llm import avaliar, carregar_gold, prever

# Premissa dos literais abaixo: 5 linhas avaliadas e 1 fora da taxonomia.
#   frutas:  2 linhas, 1 acerto, 1 foi para o bucket
#   bebidas: 3 linhas, 2 acertos, 1 previu frutas
#   fora:    1 linha, que o LLM mandou para o bucket
GOLD = [
    ("BANANA KG", "mercado-frutas"),
    ("UVA 500G", "mercado-frutas"),
    ("REFRIG 2L", "bebidas"),
    ("SUCO 1L", "bebidas"),
    ("AGUA 500ML", "bebidas"),
    ("ITEM SEM LUGAR", None),
]
PREDICOES = ["mercado-frutas", None, "bebidas", "bebidas", "mercado-frutas", None]


# --- C4.1 -------------------------------------------------------------------
def test_carregar_gold_le_ponto_e_virgula_tolera_bom_e_vazio_vira_none(tmp_path):
    caminho = tmp_path / "gold.csv"
    caminho.write_text(
        "descricao;esperado\nMACA FUJI KG;mercado-frutas\nITEM SEM LUGAR 1UN;\n",
        encoding="utf-8-sig",
    )

    assert carregar_gold(caminho) == [
        ("MACA FUJI KG", "mercado-frutas"),
        ("ITEM SEM LUGAR 1UN", None),
    ]


# --- C4.2 -------------------------------------------------------------------
def test_prever_chama_o_llm_por_linha_e_guarda_so_o_slug():
    chamadas = []
    respostas = {"BANANA KG": ("mercado-frutas", 0.9), "UVA 500G": None}

    def llm(descricao, slugs):
        chamadas.append((descricao, slugs))
        return respostas[descricao]

    gold = [("BANANA KG", "mercado-frutas"), ("UVA 500G", "mercado-frutas")]
    slugs = ["bebidas", "mercado-frutas"]

    assert prever(gold, llm, slugs) == ["mercado-frutas", None]
    assert chamadas == [("BANANA KG", slugs), ("UVA 500G", slugs)]


# --- C4.3 -------------------------------------------------------------------
def test_acertos_e_acuracia():
    resultado = avaliar(GOLD, PREDICOES)

    assert resultado["avaliados"] == 5
    assert resultado["acertos"] == 3
    assert resultado["acuracia"] == pytest.approx(3 / 5)


# --- C4.4 -------------------------------------------------------------------
def test_por_categoria_conta_pelo_esperado():
    por_categoria = avaliar(GOLD, PREDICOES)["por_categoria"]

    assert por_categoria["mercado-frutas"]["total"] == 2
    assert por_categoria["mercado-frutas"]["acertos"] == 1
    assert por_categoria["mercado-frutas"]["acuracia"] == pytest.approx(1 / 2)
    assert por_categoria["bebidas"]["total"] == 3
    assert por_categoria["bebidas"]["acertos"] == 2
    assert por_categoria["bebidas"]["acuracia"] == pytest.approx(2 / 3)


# --- C4.5 -------------------------------------------------------------------
def test_matriz_de_confusao_com_o_bucket_como_string_e_serializavel():
    resultado = avaliar(GOLD, PREDICOES)

    assert resultado["matriz"] == {
        "mercado-frutas": {"mercado-frutas": 1, "uncategorized": 1},
        "bebidas": {"bebidas": 2, "mercado-frutas": 1},
    }
    json.dumps(resultado)


# --- C4.6 -------------------------------------------------------------------
def test_taxa_no_bucket():
    assert avaliar(GOLD, PREDICOES)["taxa_no_bucket"] == pytest.approx(1 / 5)


# --- C4.7 -------------------------------------------------------------------
def test_linha_sem_categoria_na_taxonomia_fica_fora_da_acuracia():
    """🔴 O LLM nao tem como acertar uma categoria que nao recebeu. Contar essas
    linhas na acuracia mediria a TAXONOMIA, e nao o LLM."""
    resultado = avaliar(GOLD, PREDICOES)

    assert resultado["fora_da_taxonomia"] == {"total": 1, "no_bucket": 1}
    assert None not in resultado["por_categoria"]
    assert None not in resultado["matriz"]

    # ⭐ Acrescentado no P4 (spec §8): a cobertura de ramos mostrou que nenhuma
    # linha fora da taxonomia tinha RESPOSTA do LLM. Sem isto, `no_bucket` podia
    # contar todas as linhas de fora, e nada acendia.
    respondida = avaliar([("OUTRO ITEM SEM LUGAR", None)], ["bebidas"])
    assert respondida["fora_da_taxonomia"] == {"total": 1, "no_bucket": 0}


# --- C4.8 -------------------------------------------------------------------
def test_tamanhos_diferentes_levantam_e_nada_avaliado_da_acuracia_none():
    with pytest.raises(ValueError):
        avaliar(GOLD, PREDICOES[:-1])

    resultado = avaliar([("ITEM SEM LUGAR", None)], [None])
    assert resultado["avaliados"] == 0
    assert resultado["acuracia"] is None
    assert resultado["taxa_no_bucket"] is None

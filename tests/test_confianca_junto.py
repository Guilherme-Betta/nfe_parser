"""Categoria, origem e confianca sao gravadas JUNTAS — nunca sobra confianca velha.

🔴 `confianca` so tem sentido para `origem = 'llm'`. Antes do passo 3 da
refatoracao, so o degrau do LLM escrevia essa coluna; a cascata, a categoria
manual e o `apagar_categoria` gravavam categoria e origem e deixavam a confianca
como estava. Um produto que o LLM classificou e depois saiu dessa decisao
continuava exibindo a confianca dela — um numero que nao descreve mais nada.

⭐ Os quatro testes partem do mesmo estado: um produto classificado pelo LLM com
confianca 0.87. Cada um tira o produto dessa decisao por um caminho diferente.
"""

import pytest

from nfe_parser.banco import abrir_banco
from nfe_parser.categorizacao import classificar_produto, definir_categoria_manual
from nfe_parser.taxonomia import apagar_categoria

QUEIJO, BEBIDAS, BUCKET = 3, 4, 9
NCM = "04039000"


def _llm(resposta):
    return lambda descricao, slugs: resposta


@pytest.fixture
def conexao(tmp_path):
    con = abrir_banco(tmp_path / "nfe.db")
    con.executemany(
        "INSERT INTO categorias (id, slug, nome, is_bucket) VALUES (?, ?, ?, ?)",
        [
            (QUEIJO, "queijo-minas", "Queijo Minas", 0),
            (BEBIDAS, "bebidas", "Bebidas", 0),
            (BUCKET, "uncategorized", "Nao Classificado", 1),
        ],
    )
    yield con
    con.close()


@pytest.fixture
def produto_do_llm(conexao):
    """Um produto que o LLM mandou para `bebidas` com confianca 0.87."""
    produto_id = conexao.execute(
        "INSERT INTO produtos (identidade_origem, gtin, descricao_exemplo, criado_em,"
        " atualizado_em) VALUES ('gtin', '7891111111111', 'REFRIG COLA PET 2L', 'x', 'x')"
    ).lastrowid
    classificar_produto(conexao, produto_id, NCM, _llm(("bebidas", 0.87)))
    assert _estado(conexao, produto_id) == (BEBIDAS, "llm", pytest.approx(0.87))
    return produto_id


def _estado(conexao, produto_id):
    return conexao.execute(
        "SELECT categoria_id, origem, confianca FROM produtos WHERE id = ?", (produto_id,)
    ).fetchone()


def test_reclassificado_pelo_ncm_perde_a_confianca(conexao, produto_do_llm):
    conexao.execute("INSERT INTO ncm_ancora (prefixo, categoria_id) VALUES (?, ?)", (NCM, QUEIJO))

    classificar_produto(conexao, produto_do_llm, NCM)

    assert _estado(conexao, produto_do_llm) == (QUEIJO, "ncm", None)


def test_devolvido_ao_bucket_perde_a_confianca(conexao, produto_do_llm):
    classificar_produto(conexao, produto_do_llm, NCM, _llm(None))

    assert _estado(conexao, produto_do_llm) == (BUCKET, None, None)


def test_categoria_manual_perde_a_confianca(conexao, produto_do_llm):
    definir_categoria_manual(conexao, produto_do_llm, QUEIJO)

    assert _estado(conexao, produto_do_llm) == (QUEIJO, "manual", None)


def test_categoria_apagada_manda_ao_bucket_sem_confianca(conexao, produto_do_llm):
    apagar_categoria(conexao, "bebidas")

    assert _estado(conexao, produto_do_llm) == (BUCKET, None, None)

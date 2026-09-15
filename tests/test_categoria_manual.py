"""Testes de `definir_categoria_manual` — story 009, tarefa 3. Criterios: spec §4, C3.

Congelados por commit ANTES da implementacao. O modelo local le (`--read`).
⭐ A assimetria e o ponto da story: a MAO sobrescreve a MAQUINA, e a maquina
nunca sobrescreve a mao.
"""

import sqlite3

import pytest

from nfe_parser.banco import abrir_banco
from nfe_parser.categorizacao import classificar_produto, definir_categoria_manual
from nfe_parser.produtos import resolver_produto_por_gtin

MERCADO, LATICINIOS, QUEIJO, BEBIDAS, BUCKET = 1, 2, 3, 4, 9

CATEGORIAS = [
    (MERCADO, "mercado", "Mercado", None, 0),
    (LATICINIOS, "laticinios", "Laticinios", MERCADO, 0),
    (QUEIJO, "queijo-minas", "Queijo Minas", LATICINIOS, 0),
    (BEBIDAS, "bebidas", "Bebidas", None, 0),
    (BUCKET, "uncategorized", "Nao Classificado", None, 1),
]
ANCORAS = [("04", MERCADO), ("0403", LATICINIOS), ("04039000", QUEIJO)]

NCM_QUE_CASA = "04039000"  # aponta para QUEIJO -- discorda da mao de proposito
GTIN = "7891111111111"
ANTIGO = "2000-01-01T00:00:00+00:00"


@pytest.fixture
def conexao(tmp_path):
    con = abrir_banco(tmp_path / "nfe.db")
    con.executemany(
        "INSERT INTO categorias (id, slug, nome, parent_id, is_bucket) VALUES (?, ?, ?, ?, ?)",
        CATEGORIAS,
    )
    con.executemany("INSERT INTO ncm_ancora (prefixo, categoria_id) VALUES (?, ?)", ANCORAS)
    yield con
    con.close()


def _criar_produto(con):
    cursor = con.execute(
        """
        INSERT INTO produtos (identidade_origem, gtin, descricao_exemplo,
                              criado_em, atualizado_em)
        VALUES ('gtin', ?, 'QUEIJO MINAS 500G', ?, ?)
        """,
        (GTIN, ANTIGO, ANTIGO),
    )
    return cursor.lastrowid


def _campo(con, produto_id, coluna):
    return con.execute(f"SELECT {coluna} FROM produtos WHERE id = ?", (produto_id,)).fetchone()[0]


# --- C3.1 -------------------------------------------------------------------
def test_grava_a_categoria_a_origem_manual_e_o_carimbo(conexao):
    produto_id = _criar_produto(conexao)

    assert definir_categoria_manual(conexao, produto_id, BEBIDAS) is None
    assert _campo(conexao, produto_id, "categoria_id") == BEBIDAS
    assert _campo(conexao, produto_id, "origem") == "manual"
    assert _campo(conexao, produto_id, "atualizado_em") != ANTIGO


# --- C3.2 -------------------------------------------------------------------
def test_a_mao_sobrescreve_o_que_o_ncm_tinha_decidido(conexao):
    """⛔ Sem pedir licenca: o humano tem a palavra final."""
    produto_id = _criar_produto(conexao)
    classificar_produto(conexao, produto_id, NCM_QUE_CASA)

    definir_categoria_manual(conexao, produto_id, BEBIDAS)

    assert _campo(conexao, produto_id, "categoria_id") == BEBIDAS
    assert _campo(conexao, produto_id, "origem") == "manual"


# --- C3.3 -------------------------------------------------------------------
def test_a_cascata_nao_sobrescreve_a_mao_nem_com_ncm_discordante(conexao):
    """🔴 O criterio que da nome a story: NCM diz QUEIJO, a mao disse BEBIDAS."""
    produto_id = _criar_produto(conexao)
    definir_categoria_manual(conexao, produto_id, BEBIDAS)
    carimbo = _campo(conexao, produto_id, "atualizado_em")

    assert classificar_produto(conexao, produto_id, NCM_QUE_CASA) == BEBIDAS
    assert _campo(conexao, produto_id, "categoria_id") == BEBIDAS
    assert _campo(conexao, produto_id, "atualizado_em") == carimbo


# --- C3.4 -------------------------------------------------------------------
def test_a_realimentacao_alcanca_os_proximos_itens_do_mesmo_produto(conexao):
    """⭐ A realimentacao do §4 sai de graca da identidade da 008.

    Dois itens do mesmo GTIN resolvem para a MESMA linha: a decisao ja esta la
    quando o segundo chega, e nada e escrito de novo.
    """
    primeiro = resolver_produto_por_gtin(conexao, GTIN, "QUEIJO MINAS 500G")
    definir_categoria_manual(conexao, primeiro, BEBIDAS)
    carimbo = _campo(conexao, primeiro, "atualizado_em")

    segundo = resolver_produto_por_gtin(conexao, GTIN, "QJ MINAS 500G PCT")

    assert segundo == primeiro
    assert classificar_produto(conexao, segundo, NCM_QUE_CASA) == BEBIDAS
    assert _campo(conexao, segundo, "atualizado_em") == carimbo


# --- C3.5 -------------------------------------------------------------------
def test_produto_inexistente_levanta_lookup_error(conexao):
    """D5: `WHERE id = NULL` nao casa com nada, e `id = 999` tambem nao."""
    with pytest.raises(LookupError):
        definir_categoria_manual(conexao, 999, BEBIDAS)

    with pytest.raises(LookupError):
        definir_categoria_manual(conexao, None, BEBIDAS)


# --- C3.6 -------------------------------------------------------------------
def test_categoria_inexistente_e_recusada_pela_chave_estrangeira(conexao):
    """⛔ Quem valida `categoria_id` e o banco, nao a funcao.

    Um `SELECT` a mais trocaria esta excecao por outra. Este teste tambem e o
    que prova que o `PRAGMA foreign_keys = ON` do `abrir_banco` esta de pe.
    """
    produto_id = _criar_produto(conexao)

    with pytest.raises(sqlite3.IntegrityError):
        definir_categoria_manual(conexao, produto_id, 777)

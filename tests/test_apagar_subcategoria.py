"""Apagar subcategoria: os produtos sobem para a mae — spec 02 §4 e §7.2.

Decisao do Gui de 2026-10-16 (rodada 02). Antes, iam todos para o bucket com a
origem zerada: a decisao manual de quem usa o programa era jogada fora, e o NCM so
recuperava parte deles na importacao seguinte. Agora a decisao so fica menos
especifica — o `manual` continua `manual` — e as ancoras NCM da subcategoria passam
a apontar para a mae.

Categoria de NIVEL 1 nao tem mae e continua mandando para o bucket; isso ja esta
em `test_taxonomia_apagar.py`.
"""

import pytest

from nfe_parser.banco import abrir_banco
from nfe_parser.taxonomia import apagar_categoria

DH = "2026-04-01T13:00:00+00:00"


@pytest.fixture
def con(tmp_path):
    """Mercado com a filha Laticinios, e o bucket; o NCM 0403 aponta para a filha."""
    conexao = abrir_banco(tmp_path / "nfe.db")
    conexao.executescript(
        "INSERT INTO categorias (id, slug, nome, parent_id, is_bucket) VALUES"
        " (1, 'mercado', 'Mercado', NULL, 0),"
        " (2, 'mercado-laticinios', 'Laticinios', 1, 0),"
        " (9, 'uncategorized', 'Nao Classificado', NULL, 1);"
        "INSERT INTO ncm_ancora (prefixo, categoria_id) VALUES ('0403', 2), ('04', 1);"
    )
    yield conexao
    conexao.close()


def _produto(con, n, origem, confianca=None):
    return con.execute(
        "INSERT INTO produtos (identidade_origem, gtin, categoria_id, origem, confianca,"
        " criado_em, atualizado_em) VALUES ('gtin', ?, 2, ?, ?, ?, ?)",
        (f"789000000000{n}", origem, confianca, DH, DH),
    ).lastrowid


def _estado(con, produto_id):
    return con.execute(
        "SELECT categoria_id, origem, confianca FROM produtos WHERE id = ?", (produto_id,)
    ).fetchone()


@pytest.mark.parametrize(
    ("origem", "confianca"),
    [("manual", None), ("ncm", None), ("llm", 0.9)],
    ids=["manual", "ncm", "llm"],
)
def test_produtos_sobem_para_a_mae_mantendo_origem_e_confianca(con, origem, confianca):
    produto_id = _produto(con, 1, origem, confianca)

    apagar_categoria(con, "mercado-laticinios")

    assert _estado(con, produto_id) == (1, origem, confianca)


def test_ancoras_da_subcategoria_passam_a_apontar_para_a_mae(con):
    apagar_categoria(con, "mercado-laticinios")

    ancoras = con.execute("SELECT prefixo, categoria_id FROM ncm_ancora ORDER BY prefixo")
    assert ancoras.fetchall() == [("04", 1), ("0403", 1)]


def test_a_subcategoria_some_e_ganha_lapide(con):
    """Guarda: o resto de "apagar" nao muda."""
    apagar_categoria(con, "mercado-laticinios")

    assert con.execute("SELECT COUNT(*) FROM categorias WHERE id = 2").fetchone()[0] == 0
    lapides = con.execute("SELECT slug FROM categorias_apagadas").fetchall()
    assert lapides == [("mercado-laticinios",)]

"""`mover_categoria` nao pode criar um terceiro nivel — spec 02 §4 e §6.

⭐ `criar_categoria` ja recusa terceiro nivel; sem a mesma regra no mover, a
arvore chegaria la por outro caminho, e a arvore de 2 niveis da API (spec 03 §4)
deixaria de mostrar uma categoria.
"""

import pytest

from nfe_parser.taxonomia import mover_categoria


def _pai(con, slug):
    return con.execute("SELECT parent_id FROM categorias WHERE slug = ?", (slug,)).fetchone()[0]


def _id(con, slug):
    return con.execute("SELECT id FROM categorias WHERE slug = ?", (slug,)).fetchone()[0]


@pytest.fixture
def con(conexao):
    """`raiz` > `meio`; `vazia` (nivel 1, sem filhas); o bucket."""
    for slug, pai, bucket in (
        ("raiz", None, 0),
        ("meio", "raiz", 0),
        ("vazia", None, 0),
        ("uncategorized", None, 1),
    ):
        conexao.execute(
            "INSERT INTO categorias (slug, nome, parent_id, is_bucket) VALUES (?, ?, ?, ?)",
            (slug, slug.upper(), None if pai is None else _id(conexao, pai), bucket),
        )
    return conexao


def test_mover_para_dentro_de_uma_subcategoria_levanta(con):
    with pytest.raises(ValueError):
        mover_categoria(con, "vazia", "meio")

    assert _pai(con, "vazia") is None


def test_mover_categoria_com_filhas_para_dentro_de_outra_levanta(con):
    """As filhas de `raiz` virariam terceiro nivel."""
    with pytest.raises(ValueError):
        mover_categoria(con, "raiz", "vazia")

    assert _pai(con, "raiz") is None


def test_mover_para_dentro_do_bucket_levanta(con):
    with pytest.raises(ValueError):
        mover_categoria(con, "vazia", "uncategorized")


def test_subcategoria_para_outro_nivel_1_continua_valendo(con):
    mover_categoria(con, "meio", "vazia")

    assert _pai(con, "meio") == _id(con, "vazia")


def test_categoria_com_filhas_para_none_continua_valendo(con):
    mover_categoria(con, "raiz", None)

    assert _pai(con, "raiz") is None
    assert _pai(con, "meio") == _id(con, "raiz")

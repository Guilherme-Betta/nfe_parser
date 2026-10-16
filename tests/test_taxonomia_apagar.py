"""Oraculo da tarefa 1 da story 011: `apagar_categoria`. Criterios C3 da spec.

⭐ A taxonomia e montada aqui, com INSERT direto — ⛔ nenhum teste chama o seed.
"""

import pytest

from nfe_parser.banco import abrir_banco
from nfe_parser.taxonomia import apagar_categoria

DH = "2026-01-02T10:00:00-03:00"


def _categoria(con, slug, parent_id=None, is_bucket=0):
    cur = con.execute(
        "INSERT INTO categorias (slug, nome, parent_id, is_bucket) VALUES (?, ?, ?, ?)",
        (slug, slug.upper(), parent_id, is_bucket),
    )
    return cur.lastrowid


def _produto(con, categoria_id, origem=None):
    cur = con.execute(
        "INSERT INTO produtos (identidade_origem, gtin, categoria_id, origem,"
        " criado_em, atualizado_em) VALUES ('gtin', ?, ?, ?, ?, ?)",
        (str(categoria_id) + (origem or "x"), categoria_id, origem, DH, DH),
    )
    return cur.lastrowid


def _id(con, slug):
    linha = con.execute("SELECT id FROM categorias WHERE slug = ?", (slug,)).fetchone()
    return None if linha is None else linha[0]


@pytest.fixture
def con(tmp_path):
    """Um pai com filha, uma categoria solta, e o bucket. `categorias` nasce
    vazia da migracao v1."""
    conexao = abrir_banco(tmp_path / "nfe.db")
    pai = _categoria(conexao, "pai")
    _categoria(conexao, "filha", parent_id=pai)
    _categoria(conexao, "solta")
    _categoria(conexao, "uncategorized", is_bucket=1)
    conexao.execute(
        "INSERT INTO ncm_ancora (prefixo, categoria_id) VALUES ('1234', ?)",
        (_id(conexao, "solta"),),
    )
    yield conexao
    conexao.close()


# C3.1
def test_os_produtos_da_categoria_vao_para_o_bucket(con):
    produto = _produto(con, _id(con, "solta"))

    apagar_categoria(con, "solta")

    categoria = con.execute(
        "SELECT categoria_id FROM produtos WHERE id = ?", (produto,)
    ).fetchone()[0]
    assert categoria == _id(con, "uncategorized")


# C3.2
def test_produto_manual_perde_a_origem_ao_cair_no_bucket(con):
    """🔴 `'manual'` preservado prenderia o produto DENTRO do bucket."""
    produto = _produto(con, _id(con, "solta"), origem="manual")

    apagar_categoria(con, "solta")

    origem = con.execute("SELECT origem FROM produtos WHERE id = ?", (produto,)).fetchone()[0]
    assert origem is None


# C3.3
def test_as_ancoras_ncm_da_categoria_somem(con):
    apagar_categoria(con, "solta")

    assert con.execute("SELECT COUNT(*) FROM ncm_ancora").fetchone()[0] == 0


# C3.4 e C3.5
def test_a_categoria_some_e_a_lapide_registra_o_slug(con):
    apagar_categoria(con, "solta")

    assert _id(con, "solta") is None
    assert con.execute("SELECT slug FROM categorias_apagadas").fetchall() == [("solta",)]


# C3.9
def test_apagar_o_mesmo_slug_duas_vezes_nao_levanta(con):
    """A categoria pode voltar por um seed antigo e ser apagada de novo."""
    apagar_categoria(con, "solta")
    _categoria(con, "solta")

    apagar_categoria(con, "solta")

    assert _id(con, "solta") is None


# C3.6
def test_categoria_com_filhas_e_recusada_e_continua_la(con):
    with pytest.raises(ValueError):
        apagar_categoria(con, "pai")

    assert _id(con, "pai") is not None


# C3.7
def test_apagar_o_bucket_e_recusado_e_ele_continua_la(con):
    with pytest.raises(ValueError):
        apagar_categoria(con, "uncategorized")

    assert _id(con, "uncategorized") is not None


# C3.8
def test_slug_inexistente_levanta(con):
    with pytest.raises(LookupError):
        apagar_categoria(con, "nao-existe")

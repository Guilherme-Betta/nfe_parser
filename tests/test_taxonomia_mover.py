"""Oraculo da tarefa 3 da story 011: `mover_categoria`. Criterios C2 da spec.

⭐ Mover tambem preserva o `id`, entao produtos e ancoras seguem de graca. O que
a funcao tem de impedir e o CICLO, que a chave estrangeira ⛔ nao pega.
"""

import pytest

from nfe_parser.banco import abrir_banco
from nfe_parser.taxonomia import mover_categoria


def _linha(con, slug):
    return con.execute("SELECT id, parent_id FROM categorias WHERE slug = ?", (slug,)).fetchone()


@pytest.fixture
def con(tmp_path):
    """Tres niveis (`raiz` > `meio` > `folha`) e uma categoria solta."""
    conexao = abrir_banco(tmp_path / "nfe.db")
    for slug, pai in (("raiz", None), ("meio", "raiz"), ("folha", "meio"), ("outra", None)):
        conexao.execute(
            "INSERT INTO categorias (slug, nome, parent_id) VALUES (?, ?, ?)",
            (slug, slug.upper(), None if pai is None else _linha(conexao, pai)[0]),
        )
    yield conexao
    conexao.close()


# C2.1 e C2.2
def test_mover_troca_o_pai_e_preserva_o_id(con):
    antes = _linha(con, "folha")

    mover_categoria(con, "folha", "outra")

    depois = _linha(con, "folha")
    assert depois[0] == antes[0]
    assert depois[1] == _linha(con, "outra")[0]


# C2.3
def test_mover_para_none_vira_nivel_1(con):
    mover_categoria(con, "folha", None)

    assert _linha(con, "folha")[1] is None


# C2.4 e C2.5
@pytest.mark.parametrize(("slug", "novo_pai"), [("nao-existe", "raiz"), ("folha", "nao-existe")])
def test_mover_com_slug_inexistente_levanta(con, slug, novo_pai):
    with pytest.raises(LookupError):
        mover_categoria(con, slug, novo_pai)


# C2.6 e C2.7
@pytest.mark.parametrize("novo_pai", ["raiz", "meio", "folha"])
def test_mover_para_dentro_de_si_ou_de_descendente_levanta(con, novo_pai):
    """🔴 `folha` esta DOIS niveis abaixo — um teste de um nivel so nao pega."""
    with pytest.raises(ValueError):
        mover_categoria(con, "raiz", novo_pai)

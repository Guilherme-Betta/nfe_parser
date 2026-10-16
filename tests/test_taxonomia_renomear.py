"""Oraculo da tarefa 2 da story 011: `renomear_categoria`. Criterios C1 da spec.

⭐ Renomear e o caso em que o vinculo SOBREVIVE sozinho: o `id` nao muda, e nada
em outra tabela precisa ser reescrito.
"""

import pytest

from nfe_parser.banco import abrir_banco
from nfe_parser.taxonomia import renomear_categoria

DH = "2026-01-02T10:00:00-03:00"


def _linha(con, slug):
    return con.execute("SELECT id, slug, nome FROM categorias WHERE slug = ?", (slug,)).fetchone()


@pytest.fixture
def con(tmp_path):
    conexao = abrir_banco(tmp_path / "nfe.db")
    conexao.execute("INSERT INTO categorias (slug, nome) VALUES ('leite', 'Laticinios')")
    yield conexao
    conexao.close()


# C1.1
def test_renomear_troca_o_nome(con):
    renomear_categoria(con, "leite", "Leite e derivados")

    assert _linha(con, "leite")[2] == "Leite e derivados"


# C1.2 e C1.3
def test_renomear_preserva_id_slug_e_os_vinculos(con):
    antes = _linha(con, "leite")
    con.execute(
        "INSERT INTO produtos (identidade_origem, gtin, categoria_id, criado_em,"
        " atualizado_em) VALUES ('gtin', '789', ?, ?, ?)",
        (antes[0], DH, DH),
    )

    renomear_categoria(con, "leite", "Outro Nome")

    assert _linha(con, "leite")[:2] == antes[:2]
    assert con.execute("SELECT categoria_id FROM produtos").fetchone()[0] == antes[0]


# C1.4
def test_renomear_slug_inexistente_levanta(con):
    with pytest.raises(LookupError):
        renomear_categoria(con, "nao-existe", "X")


# C1.5
@pytest.mark.parametrize("nome", ["", None])
def test_renomear_com_nome_vazio_levanta(con, nome):
    """`nome TEXT NOT NULL` ⛔ nao pega string vazia — a coluna nao defende."""
    with pytest.raises(ValueError):
        renomear_categoria(con, "leite", nome)

"""Testes de `carregar_ncm_ancora` — story 010, tarefa 2.

O PORQUE de cada criterio mora em `specs/010-seed-taxonomia/spec.md` §4 (C2) e
§2 (D4, D7). Nao o repita aqui: a spec NAO e enviada ao modelo local, e este
arquivo e.

Congelado por commit ANTES da implementacao; o modelo local le (`--read`).
A fixture semeia so DUAS categorias: a arvore e dona do outro modulo.
"""

import pytest

from nfe_parser.banco import abrir_banco
from nfe_parser.seed import carregar_ncm_ancora

MERCADO, BEBIDAS = 1, 2

ANCORAS = [
    {"prefixo": "08", "categoria": "mercado"},
    {"prefixo": "22021000", "categoria": "bebidas"},
]


@pytest.fixture
def conexao(tmp_path):
    con = abrir_banco(tmp_path / "nfe.db")
    con.executemany(
        "INSERT INTO categorias (id, slug, nome) VALUES (?, ?, ?)",
        [(MERCADO, "mercado", "Mercado"), (BEBIDAS, "bebidas", "Bebidas")],
    )
    yield con
    con.close()


def _categoria(con, prefixo):
    linha = con.execute(
        "SELECT categoria_id FROM ncm_ancora WHERE prefixo = ?", (prefixo,)
    ).fetchone()
    return linha[0] if linha else None


def _quantas(con):
    return con.execute("SELECT COUNT(*) FROM ncm_ancora").fetchone()[0]


# --- C2.1 -------------------------------------------------------------------
def test_grava_os_prefixos_com_o_id_do_slug(conexao):
    carregar_ncm_ancora(conexao, ANCORAS)
    assert _categoria(conexao, "08") == MERCADO
    assert _categoria(conexao, "22021000") == BEBIDAS


# --- C2.2 -------------------------------------------------------------------
def test_rodar_duas_vezes_nao_duplica(conexao):
    carregar_ncm_ancora(conexao, ANCORAS)
    carregar_ncm_ancora(conexao, ANCORAS)
    assert _quantas(conexao) == 2


# --- C2.3 -------------------------------------------------------------------
def test_o_mesmo_prefixo_reaponta_para_a_categoria_nova(conexao):
    carregar_ncm_ancora(conexao, ANCORAS)
    carregar_ncm_ancora(conexao, [{"prefixo": "08", "categoria": "bebidas"}])
    assert _categoria(conexao, "08") == BEBIDAS
    assert _quantas(conexao) == 2


# --- C2.4 -------------------------------------------------------------------
def test_slug_inexistente_levanta_lookup_error(conexao):
    with pytest.raises(LookupError):
        carregar_ncm_ancora(conexao, [{"prefixo": "04", "categoria": "nao-existe"}])


# --- C2.5 -------------------------------------------------------------------
@pytest.mark.parametrize("prefixo", ["0", "040", "04039", "040390001"])
def test_largura_de_prefixo_impossivel_levanta_value_error(conexao, prefixo):
    """Quem le a tabela so consulta as fatias [:8], [:4] e [:2] do NCM."""
    with pytest.raises(ValueError):
        carregar_ncm_ancora(conexao, [{"prefixo": prefixo, "categoria": "mercado"}])


# --- C2.5 (o contraste) -----------------------------------------------------
@pytest.mark.parametrize("prefixo", ["04", "0403", "04039000"])
def test_as_tres_larguras_legitimas_passam(conexao, prefixo):
    carregar_ncm_ancora(conexao, [{"prefixo": prefixo, "categoria": "mercado"}])
    assert _categoria(conexao, prefixo) == MERCADO

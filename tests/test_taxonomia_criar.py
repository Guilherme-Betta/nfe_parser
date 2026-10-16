"""`criar_categoria` — spec 02 §4 e §6 (decisao do Gui de 2026-10-15).

⭐ O slug NASCE do nome, prefixado pelo do pai, e dali em diante e dado: renomear
nao o muda (ver `test_taxonomia_renomear.py`). A arvore tem no maximo 2 niveis.
"""

import pytest

from nfe_parser.taxonomia import criar_categoria


def _linha(con, slug):
    return con.execute(
        "SELECT id, nome, parent_id, is_bucket FROM categorias WHERE slug = ?", (slug,)
    ).fetchone()


def _conta(con):
    return con.execute("SELECT COUNT(*) FROM categorias").fetchone()[0]


@pytest.fixture
def con(conexao):
    """`mercado` > `mercado-frutas`, e o bucket."""
    conexao.execute("INSERT INTO categorias (slug, nome) VALUES ('mercado', 'Mercado')")
    conexao.execute(
        "INSERT INTO categorias (slug, nome, parent_id) VALUES ('mercado-frutas', 'Frutas',"
        " (SELECT id FROM categorias WHERE slug = 'mercado'))"
    )
    conexao.execute(
        "INSERT INTO categorias (slug, nome, is_bucket) VALUES ('uncategorized', 'Nao Class.', 1)"
    )
    return conexao


def test_criar_nivel_1_devolve_o_slug_e_grava(con):
    slug = criar_categoria(con, "Molhos")

    assert slug == "molhos"
    _, nome, parent_id, is_bucket = _linha(con, "molhos")
    assert (nome, parent_id, is_bucket) == ("Molhos", None, 0)


def test_criar_subcategoria_prefixa_o_slug_do_pai(con):
    slug = criar_categoria(con, "Molhos", "mercado")

    assert slug == "mercado-molhos"
    assert _linha(con, "mercado-molhos")[2] == _linha(con, "mercado")[0]


@pytest.mark.parametrize(
    ("nome", "esperado"),
    [
        ("Pão & Café  Especial", "pao-cafe-especial"),
        ("  Item p/ Mochila! ", "item-p-mochila"),
        ("Cerveja 600ml", "cerveja-600ml"),
    ],
)
def test_slug_sem_acento_minusculo_e_com_um_hifen_entre_palavras(con, nome, esperado):
    assert criar_categoria(con, nome) == esperado


def test_o_nome_e_gravado_sem_espacos_nas_pontas(con):
    criar_categoria(con, "  Molhos ")

    assert _linha(con, "molhos")[1] == "Molhos"


@pytest.mark.parametrize("nome", ["", "   ", "!!!", None])
def test_nome_vazio_ou_sem_letra_nem_digito_levanta(con, nome):
    """🔴 `!!!` passaria por `NOT NULL` e daria slug vazio — dano mudo."""
    antes = _conta(con)

    with pytest.raises(ValueError):
        criar_categoria(con, nome)

    assert _conta(con) == antes


@pytest.mark.parametrize(("nome", "pai"), [("Mercado", None), ("Frutas", "mercado")])
def test_slug_que_ja_existe_levanta_e_nao_grava(con, nome, pai):
    """O slug e UNIQUE no banco; aqui o erro tem de ser `ValueError`, com mensagem clara."""
    antes = _conta(con)

    with pytest.raises(ValueError):
        criar_categoria(con, nome, pai)

    assert _conta(con) == antes


def test_pai_que_e_subcategoria_levanta(con):
    """Seria um terceiro nivel — roadmap."""
    with pytest.raises(ValueError):
        criar_categoria(con, "Morango", "mercado-frutas")


def test_bucket_nunca_e_pai(con):
    with pytest.raises(ValueError):
        criar_categoria(con, "Diversos", "uncategorized")


def test_pai_inexistente_levanta_lookup_error(con):
    with pytest.raises(LookupError):
        criar_categoria(con, "Molhos", "nao-existe")

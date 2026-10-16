"""O seed e base default: insere o que falta e NAO desfaz edicao de gente.

Escrito no PASSO 4 da story 011, fora do loop — o alvo (`seed.py`, 8,6 KB) nao
cabe na janela de 8192 do modelo local nem sozinho.

⚠️ Este modulo NAO faz parte do oraculo de nenhuma tarefa. Ele guarda o contrato
C4 da spec da 011, que e a traducao em codigo da decisao do Gui de 15/09/2026.

⭐ A taxonomia e passada a mao, em listas pequenas. ⛔ Nenhum teste chama
`carregar_seed_padrao`: amarrar o oraculo as 44 categorias reais faria a curadoria
do dado quebrar a suite.
"""

import pytest

from nfe_parser.banco import abrir_banco
from nfe_parser.seed import carregar_categorias, carregar_ncm_ancora
from nfe_parser.taxonomia import apagar_categoria, mover_categoria, renomear_categoria

SEED = [
    {"slug": "mercado", "nome": "Mercado"},
    {"slug": "mercado-leite", "nome": "Laticinios", "parent": "mercado"},
    {"slug": "casa", "nome": "Casa"},
    {"slug": "uncategorized", "nome": "Nao Classificado", "is_bucket": True},
]


@pytest.fixture
def con(tmp_path):
    conexao = abrir_banco(tmp_path / "nfe.db")
    carregar_categorias(conexao, SEED)
    yield conexao
    conexao.close()


def _cat(con, slug):
    return con.execute(
        "SELECT id, nome, parent_id FROM categorias WHERE slug = ?", (slug,)
    ).fetchone()


# C4.1
def test_rodar_o_seed_de_novo_nao_desfaz_o_renomear(con):
    renomear_categoria(con, "mercado-leite", "Leite e derivados")

    carregar_categorias(con, SEED)

    assert _cat(con, "mercado-leite")[1] == "Leite e derivados"


# C4.2
def test_rodar_o_seed_de_novo_nao_desfaz_o_mover(con):
    mover_categoria(con, "mercado-leite", "casa")

    carregar_categorias(con, SEED)

    assert _cat(con, "mercado-leite")[2] == _cat(con, "casa")[0]


# C4.3
def test_rodar_o_seed_de_novo_nao_ressuscita_o_que_foi_apagado(con):
    apagar_categoria(con, "mercado-leite")

    carregar_categorias(con, SEED)

    assert _cat(con, "mercado-leite") is None


# C4.4
def test_slug_novo_no_arquivo_de_dados_entra_normalmente(con):
    carregar_categorias(con, [*SEED, {"slug": "lazer", "nome": "Lazer"}])

    assert _cat(con, "lazer") is not None


# C4.5
def test_ancora_de_categoria_sepultada_e_pulada_sem_erro(con):
    apagar_categoria(con, "mercado-leite")

    carregar_ncm_ancora(con, [{"prefixo": "0403", "categoria": "mercado-leite"}])

    assert con.execute("SELECT COUNT(*) FROM ncm_ancora").fetchone()[0] == 0


# C4.6
def test_ancora_de_slug_que_nunca_existiu_continua_levantando(con):
    """🔴 A lapide distingue remocao deliberada de erro de digitacao."""
    with pytest.raises(LookupError):
        carregar_ncm_ancora(con, [{"prefixo": "0403", "categoria": "nunca-existiu"}])


# C4.7
def test_o_mapa_ncm_das_categorias_vivas_continua_se_atualizando(con):
    """⭐ A D6 da 010 sobrevive: e assim que produto preso no bucket e resgatado."""
    carregar_ncm_ancora(con, [{"prefixo": "0403", "categoria": "mercado"}])

    carregar_ncm_ancora(con, [{"prefixo": "0403", "categoria": "mercado-leite"}])

    apontado = con.execute("SELECT categoria_id FROM ncm_ancora").fetchone()[0]
    assert apontado == _cat(con, "mercado-leite")[0]


# C4.8
def test_categoria_nova_sob_um_pai_sepultado_e_pulada(con):
    """⛔ O galho foi removido de proposito; levantar quebraria o seed para sempre."""
    apagar_categoria(con, "mercado-leite")
    apagar_categoria(con, "mercado")

    carregar_categorias(
        con, [*SEED, {"slug": "mercado-frios", "nome": "Frios", "parent": "mercado"}]
    )

    assert _cat(con, "mercado-frios") is None

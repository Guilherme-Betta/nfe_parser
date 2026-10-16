"""Testes de `carregar_categorias` — story 010, tarefa 1.

O PORQUE de cada criterio mora em `specs/010-seed-taxonomia/spec.md` §4 (C1) e
§2 (D2, D4, D8). Nao o repita aqui: a spec NAO e enviada ao modelo local, e
este arquivo e.

Congelado por commit ANTES da implementacao; o modelo local le (`--read`).
"""

import pytest

from nfe_parser.seed import carregar_categorias

# O filho vem ANTES do pai de proposito: a ordem da lista nao pode importar.
SEED = [
    {"slug": "mercado-frutas", "nome": "Frutas", "parent": "mercado"},
    {"slug": "mercado", "nome": "Mercado"},
    {"slug": "vestuario", "nome": "Vestuario"},
    {"slug": "uncategorized", "nome": "Nao Classificado", "is_bucket": True},
]


def _linha(con, slug):
    """Devolve (id, nome, parent_id, is_bucket) do slug."""
    return con.execute(
        "SELECT id, nome, parent_id, is_bucket FROM categorias WHERE slug = ?", (slug,)
    ).fetchone()


def _ids(con):
    return dict(con.execute("SELECT slug, id FROM categorias").fetchall())


# --- C1.1 -------------------------------------------------------------------
def test_grava_as_quatro_com_nome_e_bucket(conexao):
    carregar_categorias(conexao, SEED)
    assert len(_ids(conexao)) == 4
    assert _linha(conexao, "mercado")[1] == "Mercado"
    assert _linha(conexao, "uncategorized")[3] == 1
    assert _linha(conexao, "mercado-frutas")[3] == 0


# --- C1.2 -------------------------------------------------------------------
def test_o_parent_e_resolvido_com_o_filho_antes_do_pai(conexao):
    """Duas passadas: na lista, `mercado-frutas` vem antes de `mercado`."""
    carregar_categorias(conexao, SEED)
    assert _linha(conexao, "mercado-frutas")[2] == _linha(conexao, "mercado")[0]
    assert _linha(conexao, "mercado")[2] is None


# --- C1.3 -------------------------------------------------------------------
def test_rodar_duas_vezes_nao_duplica(conexao):
    carregar_categorias(conexao, SEED)
    carregar_categorias(conexao, SEED)
    assert len(_ids(conexao)) == 4


# --- C1.4 -------------------------------------------------------------------
def test_o_id_sobrevive_a_segunda_rodada(conexao):
    carregar_categorias(conexao, SEED)
    antes = _ids(conexao)
    carregar_categorias(conexao, SEED)
    assert _ids(conexao) == antes


# --- C1.5 -------------------------------------------------------------------
def test_parent_inexistente_levanta_lookup_error(conexao):
    orfa = [{"slug": "orfa", "nome": "Orfa", "parent": "ninguem"}, SEED[3]]
    with pytest.raises(LookupError):
        carregar_categorias(conexao, orfa)


# --- C1.6 (INVERTIDO na story 011 — ver a docstring) -------------------------
def test_nome_mudado_no_dado_nao_atualiza_e_o_id_nao_muda(conexao):
    """🔴 Este caso afirmava o CONTRARIO ate a 011, e a mudanca e de produto.

    A D4 da 010 mandava `ON CONFLICT(slug) DO UPDATE SET nome = excluded.nome`, e
    este teste provava que corrigir o nome no arquivo de dados chegava ao banco.
    Estava certo enquanto o arquivo era o UNICO autor de `categorias`.

    A story 011 deu a quem usa o programa um segundo teclado sobre a mesma
    tabela, e o Gui decidiu quem ganha: *"o seed serve so como base default (...)
    um helpful placeholder"*. Um seed que atualiza o nome desfaz, calado, todo
    `renomear_categoria` — medido em banco real antes de mudar.

    ⭐ O que se perde: corrigir nome pelo arquivo de dados. ⭐ O que entra no
    lugar: `taxonomia.renomear_categoria`.

    ⚠️ A segunda metade do caso — o `id` NAO muda — continua valendo, e continua
    sendo o que impede `produtos.categoria_id` de apontar para o nada.
    """
    carregar_categorias(conexao, SEED)
    antes = _linha(conexao, "mercado")[0]
    carregar_categorias(conexao, [dict(SEED[1], nome="Supermercado"), SEED[3]])
    depois = _linha(conexao, "mercado")
    assert depois[1] == "Mercado"
    assert depois[0] == antes


# --- C1.7 -------------------------------------------------------------------
@pytest.mark.parametrize("quantos", [0, 2])
def test_o_banco_precisa_ficar_com_exatamente_um_bucket(conexao, quantos):
    lista = [SEED[1]] if quantos == 0 else [SEED[3], dict(SEED[2], is_bucket=True)]
    with pytest.raises(ValueError):
        carregar_categorias(conexao, lista)


# --- C1.7 (o caso que so a contagem NO BANCO pega) --------------------------
def test_dois_seeds_com_um_bucket_cada_ainda_e_recusado(conexao):
    """Cada lista traz UM bucket; o banco fica com dois."""
    carregar_categorias(conexao, SEED)
    with pytest.raises(ValueError):
        carregar_categorias(conexao, [{"slug": "outro", "nome": "Outro", "is_bucket": True}])

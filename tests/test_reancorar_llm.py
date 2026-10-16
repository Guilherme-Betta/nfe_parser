"""O NCM vence o LLM quando a ancora chega depois — spec 02 §4 e §7.3 item 2.

Decisao do Gui de 2026-10-16. O LLM so responde por um produto porque, naquele
dia, o mapa NCM nao tinha ancora para ele. Quando uma versao nova do seed traz a
ancora, o produto fica como se chegasse hoje: NCM, sem confianca. O LLM nao e
chamado de novo.
"""

import pytest

from nfe_parser.banco import abrir_banco
from nfe_parser.varredura import reancorar_produtos_do_llm

QUEIJO, BEBIDAS, BUCKET = 3, 4, 9
NCM_QUEIJO = "04069000"
NCM_SEM_ANCORA = "22021000"
CHAVE = "35260411111111000111550010000000011000000017"


@pytest.fixture
def conexao(tmp_path):
    con = abrir_banco(tmp_path / "nfe.db")
    con.executemany(
        "INSERT INTO categorias (id, slug, nome, is_bucket) VALUES (?, ?, ?, ?)",
        [
            (QUEIJO, "queijo", "Queijo", 0),
            (BEBIDAS, "bebidas", "Bebidas", 0),
            (BUCKET, "uncategorized", "Nao Classificado", 1),
        ],
    )
    con.execute(
        "INSERT INTO ncm_ancora (prefixo, categoria_id) VALUES (?, ?)", (NCM_QUEIJO, QUEIJO)
    )
    con.execute(
        "INSERT INTO notas (chave, modelo, serie, numero, dh_emi, emit_nome, emit_cnpj,"
        " emit_municipio, emit_uf, valor_total, forma_pagamento, xml_raw, criado_em)"
        " VALUES (?, 55, 1, 1, '2026-04-01T10:00:00-03:00', 'LOJA', '11111111000111',"
        " 'Sao Paulo', 'SP', 1000, '01', '<xml/>', '2026-04-01T13:00:00+00:00')",
        (CHAVE,),
    )
    yield con
    con.close()


def _produto(con, n, ncm, categoria_id, origem, confianca=None):
    """Um produto ja classificado, com UM item de NCM `ncm`."""
    produto_id = con.execute(
        "INSERT INTO produtos (identidade_origem, gtin, descricao_exemplo, categoria_id, origem,"
        " confianca, criado_em, atualizado_em) VALUES ('gtin', ?, ?, ?, ?, ?,"
        " '2000-01-01T00:00:00+00:00', '2000-01-01T00:00:00+00:00')",
        (f"789000000000{n}", f"PRODUTO {n}", categoria_id, origem, confianca),
    ).lastrowid
    con.execute(
        "INSERT INTO itens (nota_chave, n_item, descricao, cprod, ncm, gtin, quantidade,"
        " unidade, valor_unitario, valor_linha, criado_em, produto_id)"
        " VALUES (?, ?, 'X', 'C', ?, NULL, '1.0000', 'UN', '10.00', 1000,"
        " '2026-04-01T13:00:00+00:00', ?)",
        (CHAVE, n, ncm, produto_id),
    )
    return produto_id


def _estado(con, produto_id):
    return con.execute(
        "SELECT categoria_id, origem, confianca FROM produtos WHERE id = ?", (produto_id,)
    ).fetchone()


def test_produto_do_llm_com_ancora_nova_passa_para_o_ncm(conexao):
    produto_id = _produto(conexao, 1, NCM_QUEIJO, BEBIDAS, "llm", 0.9)

    reancorados = reancorar_produtos_do_llm(conexao)

    assert reancorados == 1
    assert _estado(conexao, produto_id) == (QUEIJO, "ncm", None)


def test_produto_do_llm_sem_ancora_fica_como_esta(conexao):
    produto_id = _produto(conexao, 1, NCM_SEM_ANCORA, BEBIDAS, "llm", 0.9)

    assert reancorar_produtos_do_llm(conexao) == 0
    assert _estado(conexao, produto_id) == (BEBIDAS, "llm", 0.9)


@pytest.mark.parametrize("origem", ["manual", "ncm"])
def test_so_o_llm_e_revisitado(conexao, origem):
    """Guarda: decisao humana nunca e sobrescrita (§4, degrau 1), e o que ja e do
    NCM nao e reescrito."""
    produto_id = _produto(conexao, 1, NCM_QUEIJO, BEBIDAS, origem)

    assert reancorar_produtos_do_llm(conexao) == 0
    assert _estado(conexao, produto_id) == (BEBIDAS, origem, None)

"""Testes da varredura — story 013, tarefa 4.

🔴 O PORQUE de cada criterio mora em `specs/013-integracao/spec.md` §4 (bloco C4)
e §3 (decisoes D5, D6, D11). ⛔ Nao o repita aqui: aquela spec NAO e enviada ao
modelo local, e este arquivo e.

Congelados por commit ANTES da implementacao; o modelo local le (`--read`).

⭐ A varredura existe por uma razao so: o mapa de NCM CRESCE, e quem caiu no
bucket antes de a ancora existir tem de ser resgatado depois. E por isso que
"pendente" e `origem IS NULL` e nunca `categoria_id IS NULL` — produto no bucket
TEM categoria.

⚠️ Toda leitura nomeia a coluna (risco R1). ⛔ Nenhum teste daqui fecha o conjunto
de `origem`: a story 012 acrescenta um valor novo a ele.
"""

import pytest

from nfe_parser.banco import abrir_banco
from nfe_parser.varredura import classificar_produtos_pendentes

QUEIJO, BEBIDAS, BUCKET = 3, 4, 9

NCM_QUEIJO = "04039000"
NCM_BEBIDA = "22029900"
NCM_SEM_ANCORA = "99999999"

CHAVE = "35260411111111000111550010000000011000000017"

# Sentinela: `atualizado_em` so muda se a cascata ESCREVEU naquele produto.
ANTIGO = "2000-01-01T00:00:00+00:00"


@pytest.fixture
def conexao(tmp_path):
    con = abrir_banco(tmp_path / "nfe.db")
    con.executemany(
        "INSERT INTO categorias (id, slug, nome, is_bucket) VALUES (?, ?, ?, ?)",
        [
            (QUEIJO, "queijo-minas", "Queijo Minas", 0),
            (BEBIDAS, "bebidas", "Bebidas", 0),
            (BUCKET, "uncategorized", "Nao Classificado", 1),
        ],
    )
    con.executemany(
        "INSERT INTO ncm_ancora (prefixo, categoria_id) VALUES (?, ?)",
        [(NCM_QUEIJO, QUEIJO), (NCM_BEBIDA, BEBIDAS)],
    )
    con.execute(
        "INSERT INTO notas (chave, modelo, serie, numero, dh_emi, emit_nome, emit_cnpj,"
        " emit_municipio, emit_uf, valor_total, forma_pagamento, xml_raw, criado_em)"
        " VALUES (?, 55, 1, 1, '2026-04-01T10:00:00-03:00', 'LOJA', '11111111000111',"
        " 'Sao Paulo', 'SP', 1000, '01', '<xml/>', '2026-04-01T13:00:00+00:00')",
        (CHAVE,),
    )
    con.commit()  # linha de base: o cenario fica fora do que o C4.8 desfaz
    yield con
    con.close()


def _produto(con, categoria_id=None, origem=None, gtin="7891111111111"):
    cursor = con.execute(
        "INSERT INTO produtos (identidade_origem, gtin, descricao_exemplo, categoria_id,"
        " origem, criado_em, atualizado_em) VALUES ('gtin', ?, 'QUEIJO 500G', ?, ?, ?, ?)",
        (gtin, categoria_id, origem, ANTIGO, ANTIGO),
    )
    return cursor.lastrowid


def _item(con, produto_id, ncm, n_item=1):
    con.execute(
        "INSERT INTO itens (nota_chave, n_item, descricao, cprod, ncm, gtin, quantidade,"
        " unidade, valor_unitario, valor_linha, criado_em, produto_id)"
        " VALUES (?, ?, 'QUEIJO 500G', 'Q1', ?, NULL, '1.0000', 'UN', '10.00', 1000,"
        " '2026-04-01T13:00:00+00:00', ?)",
        (CHAVE, n_item, ncm, produto_id),
    )


def _campo(con, produto_id, coluna):
    return con.execute(f"SELECT {coluna} FROM produtos WHERE id = ?", (produto_id,)).fetchone()[0]


# --- C4.1 -------------------------------------------------------------------
def test_pendente_com_ncm_ancorado_ganha_a_categoria(conexao):
    produto_id = _produto(conexao)
    _item(conexao, produto_id, NCM_QUEIJO)

    assert classificar_produtos_pendentes(conexao) == 1
    assert _campo(conexao, produto_id, "categoria_id") == QUEIJO
    assert _campo(conexao, produto_id, "origem") == "ncm"


# --- C4.2 -------------------------------------------------------------------
def test_produto_no_bucket_e_varrido_de_novo_e_sai_de_la(conexao):
    """🔴 O criterio-titulo. Produto no bucket TEM `categoria_id` preenchido: uma
    varredura que procurasse `categoria_id IS NULL` nunca mais olharia para ele,
    e ele ficaria preso la mesmo depois de a ancora chegar."""
    produto_id = _produto(conexao, categoria_id=BUCKET, origem=None)
    _item(conexao, produto_id, NCM_QUEIJO)

    assert classificar_produtos_pendentes(conexao) == 1
    assert _campo(conexao, produto_id, "categoria_id") == QUEIJO


# --- C4.3 -------------------------------------------------------------------
def test_produto_manual_nao_e_varrido(conexao):
    """A decisao do humano nao se toca. E o retorno e `0`, nao `1`: quem nunca
    esteve pendente nao foi resgatado de nada."""
    produto_id = _produto(conexao, categoria_id=BEBIDAS, origem="manual")
    _item(conexao, produto_id, NCM_QUEIJO)

    assert classificar_produtos_pendentes(conexao) == 0
    assert _campo(conexao, produto_id, "categoria_id") == BEBIDAS


# --- C4.4 -------------------------------------------------------------------
def test_produto_ja_resolvido_por_ncm_nao_e_varrido(conexao):
    """`atualizado_em` e a sentinela: se a cascata tivesse rodado neste produto,
    ela teria reescrito a coluna."""
    produto_id = _produto(conexao, categoria_id=QUEIJO, origem="ncm")
    _item(conexao, produto_id, NCM_QUEIJO)

    assert classificar_produtos_pendentes(conexao) == 0
    assert _campo(conexao, produto_id, "atualizado_em") == ANTIGO


# --- C4.5 -------------------------------------------------------------------
def test_pendente_sem_item_nenhum_vai_para_o_bucket_e_continua_pendente(conexao):
    """Produto sem item nao e erro: a cascata ja tem resposta pronta para NCM
    vazio, que e o bucket. E o bucket NAO conta como resgate — `origem` continua
    NULL, e ele sera varrido de novo quando o mapa crescer."""
    produto_id = _produto(conexao)

    assert classificar_produtos_pendentes(conexao) == 0
    assert _campo(conexao, produto_id, "categoria_id") == BUCKET
    assert _campo(conexao, produto_id, "origem") is None


# --- C4.6 -------------------------------------------------------------------
def test_o_ncm_que_vale_e_o_do_item_mais_recente(conexao):
    """Um produto pode ter itens com NCMs diferentes — lojas classificam
    diferente. A escolha e a informacao mais nova, que e a do item de maior `id`.
    A premissa: o item de BEBIDA e inserido DEPOIS do de QUEIJO."""
    produto_id = _produto(conexao)
    _item(conexao, produto_id, NCM_QUEIJO, n_item=1)
    _item(conexao, produto_id, NCM_BEBIDA, n_item=2)

    assert classificar_produtos_pendentes(conexao) == 1
    assert _campo(conexao, produto_id, "categoria_id") == BEBIDAS


# --- C4.7 -------------------------------------------------------------------
def test_devolve_quantos_sairam_do_pendente(conexao):
    """A premissa do literal `2`: tres pendentes entram, e o terceiro cai no
    bucket porque o NCM dele nao tem ancora."""
    for n, ncm in enumerate([NCM_QUEIJO, NCM_BEBIDA, NCM_SEM_ANCORA], start=1):
        _item(conexao, _produto(conexao, gtin=f"789111111111{n}"), ncm, n_item=n)

    assert classificar_produtos_pendentes(conexao) == 2


# --- C4.8 -------------------------------------------------------------------
def test_a_varredura_nao_commita(conexao):
    """Quem abriu a transacao e que a fecha. A fixture commitou o cenario antes,
    entao o que este `rollback` desfaz e exatamente o que a varredura escreveu."""
    produto_id = _produto(conexao)
    _item(conexao, produto_id, NCM_QUEIJO)
    conexao.commit()

    classificar_produtos_pendentes(conexao)
    conexao.rollback()

    assert _campo(conexao, produto_id, "categoria_id") is None
    assert _campo(conexao, produto_id, "origem") is None

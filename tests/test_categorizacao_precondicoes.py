"""A guarda que o PASSO 4 acrescentou — contrato C4 da story 009.

⛔ Modulo NOVO de proposito. Os tres modulos do passo 2 sao a evidencia do que
foi congelado ANTES da implementacao, e nao se mexe neles depois. Este contrato
nao estava nos criterios congelados: nasceu da revisao humana, que leu o codigo
inteiro em vez do diff. Registrado na spec §7.

🔴 O DEFEITO QUE ELE FECHA, e ele e mudo. A chave estrangeira de
`produtos.categoria_id` NAO pega categoria VAZIA: NULL em coluna anulavel e valor
legitimo. Sem esta guarda, `definir_categoria_manual(con, id, None)` gravaria
`categoria_id` NULL com `origem='manual'` -- e o passo 1 da cascata, que protege
`origem='manual'`, nunca mais tocaria naquele produto. Ele ficaria preso FORA do
bucket, para sempre, invisivel a qualquer relatorio que some por categoria.

⚠️ Nem o oraculo congelado nem a cobertura enxergavam: as linhas existem e sao
executadas. O que faltava era uma chamada com a chave vazia passando por elas.
"""

import pytest

from nfe_parser.banco import abrir_banco
from nfe_parser.categorizacao import classificar_produto, definir_categoria_manual

BEBIDAS, BUCKET = 4, 9
ANTIGO = "2000-01-01T00:00:00+00:00"


@pytest.fixture
def conexao(tmp_path):
    con = abrir_banco(tmp_path / "nfe.db")
    con.executemany(
        "INSERT INTO categorias (id, slug, nome, is_bucket) VALUES (?, ?, ?, ?)",
        [(BEBIDAS, "bebidas", "Bebidas", 0), (BUCKET, "uncategorized", "Nao Classificado", 1)],
    )
    yield con
    con.close()


def _criar_produto(con):
    cursor = con.execute(
        "INSERT INTO produtos (identidade_origem, gtin, descricao_exemplo,"
        " criado_em, atualizado_em) VALUES ('gtin', '7891111111111', 'AGUA 500ML', ?, ?)",
        (ANTIGO, ANTIGO),
    )
    return cursor.lastrowid


def _campo(con, produto_id, coluna):
    return con.execute(f"SELECT {coluna} FROM produtos WHERE id = ?", (produto_id,)).fetchone()[0]


# --- C4.1 -------------------------------------------------------------------
@pytest.mark.parametrize("vazia", [None, 0])
def test_categoria_vazia_levanta_value_error(conexao, vazia):
    """⛔ `ValueError`, e nao `LookupError`: o argumento e que esta malformado."""
    produto_id = _criar_produto(conexao)

    with pytest.raises(ValueError):
        definir_categoria_manual(conexao, produto_id, vazia)


# --- C4.2 -------------------------------------------------------------------
def test_a_recusa_nao_escreve_nada(conexao):
    """A guarda vem ANTES do UPDATE: a linha tem de sair intacta."""
    produto_id = _criar_produto(conexao)

    with pytest.raises(ValueError):
        definir_categoria_manual(conexao, produto_id, None)

    assert _campo(conexao, produto_id, "categoria_id") is None
    assert _campo(conexao, produto_id, "origem") is None
    assert _campo(conexao, produto_id, "atualizado_em") == ANTIGO


# --- C4.3 -------------------------------------------------------------------
def test_o_produto_recusado_continua_classificavel(conexao):
    """⭐ O ponto da guarda: ele NAO ficou preso fora do bucket.

    Sem ela, este produto teria `origem='manual'` e a cascata o ignoraria para
    sempre. Com ela, a chamada invalida nao deixa rastro e o passo 4 ainda o
    alcanca.
    """
    produto_id = _criar_produto(conexao)

    with pytest.raises(ValueError):
        definir_categoria_manual(conexao, produto_id, None)

    assert classificar_produto(conexao, produto_id, None) == BUCKET


# --- C4.4 -------------------------------------------------------------------
def test_categoria_valida_continua_passando(conexao):
    """⚠️ A guarda tem de recusar o vazio e SO o vazio."""
    produto_id = _criar_produto(conexao)

    definir_categoria_manual(conexao, produto_id, BEBIDAS)

    assert _campo(conexao, produto_id, "categoria_id") == BEBIDAS
    assert _campo(conexao, produto_id, "origem") == "manual"

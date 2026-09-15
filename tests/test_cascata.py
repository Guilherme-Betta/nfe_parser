"""Testes de `classificar_produto` — story 009, tarefa 2.

🔴 O PORQUE de cada criterio mora em `specs/009-cascata-deterministica/spec.md`
§4 (bloco C2) e §2 (decisoes D1-D6). ⛔ Nao o repita aqui: esta spec NAO e
enviada ao modelo local, e este arquivo e.

Congelados por commit ANTES da implementacao; o modelo local le (`--read`).
⚠️ Toda leitura nomeia a coluna (risco R1). ⭐ A precedencia entre prefixos NCM
e do `test_ncm_ancora.py`: aqui basta UMA ancora, que casa ou nao casa.
"""

import pytest

from nfe_parser.banco import abrir_banco
from nfe_parser.categorizacao import classificar_produto

QUEIJO, BEBIDAS, BUCKET = 3, 4, 9

CATEGORIAS = [
    (QUEIJO, "queijo-minas", "Queijo Minas", 0),
    (BEBIDAS, "bebidas", "Bebidas", 0),
    (BUCKET, "uncategorized", "Nao Classificado", 1),
]

NCM_QUE_CASA = "04039000"
NCM_QUE_NAO_CASA = "99999999"

# Sentinela: `atualizado_em` so muda se a funcao ESCREVEU.
ANTIGO = "2000-01-01T00:00:00+00:00"


def _semear(con, com_bucket=True):
    con.executemany(
        "INSERT INTO categorias (id, slug, nome, is_bucket) VALUES (?, ?, ?, ?)",
        [c for c in CATEGORIAS if com_bucket or c[0] != BUCKET],
    )
    con.execute(
        "INSERT INTO ncm_ancora (prefixo, categoria_id) VALUES (?, ?)", (NCM_QUE_CASA, QUEIJO)
    )


@pytest.fixture
def conexao(tmp_path):
    con = abrir_banco(tmp_path / "nfe.db")
    _semear(con)
    yield con
    con.close()


def _criar_produto(con, categoria_id=None, origem=None, gtin="7891111111111"):
    cursor = con.execute(
        "INSERT INTO produtos (identidade_origem, gtin, descricao_exemplo, categoria_id,"
        " origem, criado_em, atualizado_em) VALUES ('gtin', ?, 'QUEIJO 500G', ?, ?, ?, ?)",
        (gtin, categoria_id, origem, ANTIGO, ANTIGO),
    )
    return cursor.lastrowid


def _campo(con, produto_id, coluna):
    return con.execute(f"SELECT {coluna} FROM produtos WHERE id = ?", (produto_id,)).fetchone()[0]


# --- C2.1 -------------------------------------------------------------------
def test_ncm_que_casa_grava_a_categoria_e_a_origem_ncm(conexao):
    produto_id = _criar_produto(conexao)

    assert classificar_produto(conexao, produto_id, NCM_QUE_CASA) == QUEIJO
    assert _campo(conexao, produto_id, "categoria_id") == QUEIJO
    assert _campo(conexao, produto_id, "origem") == "ncm"
    assert _campo(conexao, produto_id, "atualizado_em") != ANTIGO


# --- C2.2 -------------------------------------------------------------------
def test_ncm_que_nao_casa_cai_no_bucket_com_origem_nula(conexao):
    produto_id = _criar_produto(conexao)

    assert classificar_produto(conexao, produto_id, NCM_QUE_NAO_CASA) == BUCKET
    assert _campo(conexao, produto_id, "categoria_id") == BUCKET
    assert _campo(conexao, produto_id, "origem") is None


# --- C2.3 -------------------------------------------------------------------
def test_produto_sem_ncm_cai_no_bucket(conexao):
    produto_id = _criar_produto(conexao)

    assert classificar_produto(conexao, produto_id, None) == BUCKET
    assert _campo(conexao, produto_id, "origem") is None


# --- C2.4 -------------------------------------------------------------------
def test_origem_manual_e_mantida_e_nada_e_escrito(conexao):
    produto_id = _criar_produto(conexao, categoria_id=BEBIDAS, origem="manual")

    assert classificar_produto(conexao, produto_id, NCM_QUE_CASA) == BEBIDAS
    assert _campo(conexao, produto_id, "categoria_id") == BEBIDAS
    assert _campo(conexao, produto_id, "origem") == "manual"
    assert _campo(conexao, produto_id, "atualizado_em") == ANTIGO


# --- C2.5 -------------------------------------------------------------------
def test_origem_memoria_e_mantida(conexao):
    produto_id = _criar_produto(conexao, categoria_id=BEBIDAS, origem="memoria")

    assert classificar_produto(conexao, produto_id, NCM_QUE_CASA) == BEBIDAS
    assert _campo(conexao, produto_id, "atualizado_em") == ANTIGO


# --- C2.6 -------------------------------------------------------------------
def test_produto_no_bucket_e_reprocessado(conexao):
    """🔴 D3: protege a ORIGEM, nao o fato de ter categoria."""
    produto_id = _criar_produto(conexao, categoria_id=BUCKET, origem=None)

    assert classificar_produto(conexao, produto_id, NCM_QUE_CASA) == QUEIJO
    assert _campo(conexao, produto_id, "origem") == "ncm"


# --- C2.7 -------------------------------------------------------------------
def test_produto_inexistente_levanta_lookup_error(conexao):
    with pytest.raises(LookupError):
        classificar_produto(conexao, 999, NCM_QUE_CASA)

    with pytest.raises(LookupError):
        classificar_produto(conexao, None, NCM_QUE_CASA)


# --- C2.8 -------------------------------------------------------------------
def test_sem_bucket_so_levanta_no_ramo_que_precisa_dele(tmp_path):
    """D6: a checagem e PREGUICOSA -- `categorias` fica vazia ate a 010."""
    con = abrir_banco(tmp_path / "sem-bucket.db")
    _semear(con, com_bucket=False)

    assert classificar_produto(con, _criar_produto(con), NCM_QUE_CASA) == QUEIJO

    with pytest.raises(LookupError):
        classificar_produto(con, _criar_produto(con, gtin="7892222222222"), NCM_QUE_NAO_CASA)

    con.close()

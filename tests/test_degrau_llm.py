"""Testes do degrau do LLM na cascata — story 012, tarefa 2.

🔴 O PORQUE de cada criterio mora em `specs/012-llm-eval/spec.md` §4 (bloco C2)
e §2-§3 (decisoes D1, D2, D7, D8). ⛔ Nao o repita aqui: aquela spec NAO e
enviada ao modelo local, e este arquivo e.

Congelados por commit ANTES da implementacao; o modelo local le (`--read`).

⭐ O `llm` destes testes e uma funcao Python que devolve o que o teste quer e
anota com que argumentos foi chamada. ⛔ Nenhum Ollama.

⚠️ Toda leitura nomeia a coluna (risco R1).
"""

import pytest

from nfe_parser.banco import abrir_banco
from nfe_parser.classificacao_llm import classificar_produto_com_llm

QUEIJO, BEBIDAS, BUCKET = 3, 4, 9

NCM_QUE_CASA = "04039000"
NCM_QUE_NAO_CASA = "99999999"

# Sentinela: `atualizado_em` so muda se alguem ESCREVEU no produto.
ANTIGO = "2000-01-01T00:00:00+00:00"


class LlmFalso:
    def __init__(self, resposta):
        self.resposta = resposta
        self.chamadas = []

    def __call__(self, descricao, slugs):
        self.chamadas.append((descricao, slugs))
        return self.resposta


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
    con.execute(
        "INSERT INTO ncm_ancora (prefixo, categoria_id) VALUES (?, ?)", (NCM_QUE_CASA, QUEIJO)
    )
    con.commit()  # linha de base: o cenario fica fora do que o C2.8 desfaz
    yield con
    con.close()


def _produto(con, categoria_id=None, origem=None, gtin="7891111111111"):
    cursor = con.execute(
        "INSERT INTO produtos (identidade_origem, gtin, descricao_exemplo, categoria_id,"
        " origem, criado_em, atualizado_em)"
        " VALUES ('gtin', ?, 'REFRIG COLA PET 2L', ?, ?, ?, ?)",
        (gtin, categoria_id, origem, ANTIGO, ANTIGO),
    )
    return cursor.lastrowid


def _campo(con, produto_id, coluna):
    return con.execute(f"SELECT {coluna} FROM produtos WHERE id = ?", (produto_id,)).fetchone()[0]


# --- C2.1 -------------------------------------------------------------------
def test_sem_llm_o_resultado_e_o_da_cascata(conexao):
    produto_id = _produto(conexao)

    assert classificar_produto_com_llm(conexao, produto_id, NCM_QUE_NAO_CASA) == BUCKET
    assert _campo(conexao, produto_id, "categoria_id") == BUCKET
    assert _campo(conexao, produto_id, "origem") is None


# --- C2.2 -------------------------------------------------------------------
def test_ncm_que_casa_nao_chama_o_llm(conexao):
    produto_id = _produto(conexao)
    llm = LlmFalso(("bebidas", 0.99))

    assert classificar_produto_com_llm(conexao, produto_id, NCM_QUE_CASA, llm) == QUEIJO
    assert _campo(conexao, produto_id, "origem") == "ncm"
    assert llm.chamadas == []


# --- C2.3 -------------------------------------------------------------------
def test_origem_manual_nao_chama_o_llm_e_nada_e_escrito(conexao):
    produto_id = _produto(conexao, categoria_id=QUEIJO, origem="manual")
    llm = LlmFalso(("bebidas", 0.99))

    assert classificar_produto_com_llm(conexao, produto_id, NCM_QUE_NAO_CASA, llm) == QUEIJO
    assert _campo(conexao, produto_id, "categoria_id") == QUEIJO
    assert _campo(conexao, produto_id, "atualizado_em") == ANTIGO
    assert llm.chamadas == []


# --- C2.4 -------------------------------------------------------------------
def test_produto_no_bucket_ganha_a_categoria_do_llm(conexao):
    """🔴 O criterio-titulo: so o que a cascata mandou para o bucket chega ao LLM."""
    produto_id = _produto(conexao)
    llm = LlmFalso(("bebidas", 0.87))

    assert classificar_produto_com_llm(conexao, produto_id, NCM_QUE_NAO_CASA, llm) == BEBIDAS
    assert _campo(conexao, produto_id, "categoria_id") == BEBIDAS
    assert _campo(conexao, produto_id, "origem") == "llm"
    assert _campo(conexao, produto_id, "confianca") == pytest.approx(0.87)


# --- C2.5 -------------------------------------------------------------------
def test_llm_que_nao_sabe_deixa_no_bucket(conexao):
    produto_id = _produto(conexao)

    assert classificar_produto_com_llm(conexao, produto_id, None, LlmFalso(None)) == BUCKET
    assert _campo(conexao, produto_id, "categoria_id") == BUCKET
    assert _campo(conexao, produto_id, "origem") is None


# --- C2.6 -------------------------------------------------------------------
def test_slug_que_nao_e_categoria_valida_nao_e_gravado(conexao):
    """🔴 O `llm` e um parametro, e pode ser QUALQUER funcao. Quem garante que
    nenhuma categoria e inventada e o degrau, conferindo no banco. E o bucket nao
    e uma resposta do LLM: `origem = 'llm'` no bucket tiraria o produto da
    varredura para sempre."""
    for n, slug in enumerate(("cafeteria", "uncategorized")):
        produto_id = _produto(conexao, gtin=f"789111111111{n}")

        resultado = classificar_produto_com_llm(conexao, produto_id, None, LlmFalso((slug, 0.99)))

        assert resultado == BUCKET, slug
        assert _campo(conexao, produto_id, "categoria_id") == BUCKET, slug
        assert _campo(conexao, produto_id, "origem") is None, slug


# --- C2.7 -------------------------------------------------------------------
def test_o_llm_recebe_a_descricao_e_os_slugs_sem_o_bucket_em_ordem(conexao):
    produto_id = _produto(conexao)
    llm = LlmFalso(None)

    classificar_produto_com_llm(conexao, produto_id, None, llm)

    assert llm.chamadas == [("REFRIG COLA PET 2L", ["bebidas", "queijo-minas"])]


# --- C2.8 -------------------------------------------------------------------
def test_o_degrau_nao_commita(conexao):
    """A fixture commitou o cenario; o produto e commitado aqui. O que o
    `rollback` desfaz e exatamente o que o degrau escreveu."""
    produto_id = _produto(conexao)
    conexao.commit()

    classificar_produto_com_llm(conexao, produto_id, None, LlmFalso(("bebidas", 0.9)))
    conexao.rollback()

    assert _campo(conexao, produto_id, "categoria_id") is None
    assert _campo(conexao, produto_id, "origem") is None

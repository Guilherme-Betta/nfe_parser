"""Testes da varredura com o LLM — story 012, tarefa 3.

🔴 O PORQUE de cada criterio mora em `specs/012-llm-eval/spec.md` §4 (bloco C3)
e §3 (decisao D9). ⛔ Nao o repita aqui: aquela spec NAO e enviada ao modelo
local, e este arquivo e.

Congelados por commit ANTES da implementacao; o modelo local le (`--read`).

⭐ A varredura SEM `llm` ja tem oraculo publicado: `test_varredura_pendentes.py`,
da story 013. Aqui so entra o que o parametro novo muda.
"""

import pytest

from nfe_parser.banco import abrir_banco
from nfe_parser.varredura import classificar_produtos_pendentes

QUEIJO, BEBIDAS, BUCKET = 3, 4, 9

NCM_QUEIJO = "04039000"

CHAVE = "35260411111111000111550010000000011000000017"


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
    con.execute("INSERT INTO ncm_ancora (prefixo, categoria_id) VALUES (?, ?)", (NCM_QUEIJO, QUEIJO))
    con.execute(
        "INSERT INTO notas (chave, modelo, serie, numero, dh_emi, emit_nome, emit_cnpj,"
        " emit_municipio, emit_uf, valor_total, forma_pagamento, xml_raw, criado_em)"
        " VALUES (?, 55, 1, 1, '2026-04-01T10:00:00-03:00', 'LOJA', '11111111000111',"
        " 'Sao Paulo', 'SP', 1000, '01', '<xml/>', '2026-04-01T13:00:00+00:00')",
        (CHAVE,),
    )
    yield con
    con.close()


def _produto_com_item(con, ncm):
    produto_id = con.execute(
        "INSERT INTO produtos (identidade_origem, gtin, descricao_exemplo, criado_em,"
        " atualizado_em) VALUES ('gtin', '7891111111111', 'REFRIG COLA PET 2L',"
        " '2000-01-01T00:00:00+00:00', '2000-01-01T00:00:00+00:00')"
    ).lastrowid
    con.execute(
        "INSERT INTO itens (nota_chave, n_item, descricao, cprod, ncm, gtin, quantidade,"
        " unidade, valor_unitario, valor_linha, criado_em, produto_id)"
        " VALUES (?, 1, 'REFRIG COLA PET 2L', 'R1', ?, NULL, '1.0000', 'UN', '10.00', 1000,"
        " '2026-04-01T13:00:00+00:00', ?)",
        (CHAVE, ncm, produto_id),
    )
    return produto_id


def _campo(con, produto_id, coluna):
    return con.execute(f"SELECT {coluna} FROM produtos WHERE id = ?", (produto_id,)).fetchone()[0]


# --- C3.1 -------------------------------------------------------------------
def test_pendente_sem_ncm_e_resgatado_pelo_llm_e_conta(conexao):
    """🔴 O criterio-titulo: sem ele, a varredura poderia ignorar o parametro e
    todo o resto desta story ficaria inalcancavel pelo fluxo real."""
    produto_id = _produto_com_item(conexao, None)

    assert classificar_produtos_pendentes(conexao, llm=LlmFalso(("bebidas", 0.9))) == 1
    assert _campo(conexao, produto_id, "categoria_id") == BEBIDAS
    assert _campo(conexao, produto_id, "origem") == "llm"


# --- C3.2 -------------------------------------------------------------------
def test_pendente_com_ncm_ancorado_nao_chama_o_llm(conexao):
    produto_id = _produto_com_item(conexao, NCM_QUEIJO)
    llm = LlmFalso(("bebidas", 0.9))

    assert classificar_produtos_pendentes(conexao, llm=llm) == 1
    assert _campo(conexao, produto_id, "categoria_id") == QUEIJO
    assert llm.chamadas == []


# --- C3.3 -------------------------------------------------------------------
def test_llm_que_nao_sabe_deixa_no_bucket_e_nao_conta(conexao):
    produto_id = _produto_com_item(conexao, None)

    assert classificar_produtos_pendentes(conexao, llm=LlmFalso(None)) == 0
    assert _campo(conexao, produto_id, "categoria_id") == BUCKET
    assert _campo(conexao, produto_id, "origem") is None

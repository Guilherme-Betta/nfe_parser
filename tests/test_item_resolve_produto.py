"""Testes da identidade no item — story 013, tarefa 1.

🔴 O PORQUE de cada criterio mora em `specs/013-integracao/spec.md` §4 (bloco C1)
e §3 (decisoes D1, D2, D3). ⛔ Nao o repita aqui: aquela spec NAO e enviada ao
modelo local, e este arquivo e.

Congelados por commit ANTES da implementacao; o modelo local le (`--read`).

⭐ O `extraido` e montado A MAO, e nao por `extrair_nota` sobre um XML de
fixture. E deliberado: os criterios daqui variam GTIN e CNPJ de proposito, e
fabricar XML para cada combinacao seria testar o extrator de novo.

⚠️ Toda leitura nomeia a coluna (risco R1). ⛔ Nenhum teste daqui compara a linha
inteira de `produtos` nem fecha o conjunto de `origem`.
"""

import pytest

from nfe_parser.banco import abrir_banco
from nfe_parser.persistencia import persistir_nota

CNPJ_A = "11111111000111"
CNPJ_B = "22222222000122"
GTIN = "7891111111111"
DESCRICAO = "ARROZ TIPO 1 5KG"

CHAVE_A = "35260411111111000111550010000000011000000017"
CHAVE_B = "35260422222222000122550010000000022000000028"


def _item(n_item=1, gtin=GTIN, descricao=DESCRICAO):
    return {
        "n_item": n_item,
        "descricao": descricao,
        "cprod": "A1",
        "ncm": "10063021",
        "gtin": gtin,
        "quantidade": "1.0000",
        "unidade": "UN",
        "valor_unitario": "10.00",
        "valor_linha": 1000,
    }


def _extraido(chave=CHAVE_A, itens=None, emit_cnpj=CNPJ_A):
    """O `dict` que `extrair_nota` devolve — a entrada exata de `persistir_nota`."""
    return {
        "nota": {
            "chave": chave,
            "modelo": 55,
            "serie": 1,
            "numero": 1,
            "dh_emi": "2026-04-01T10:00:00-03:00",
            "emit_nome": "LOJA TESTE",
            "emit_cnpj": emit_cnpj,
            "emit_municipio": "Sao Paulo",
            "emit_uf": "SP",
            "valor_total": 1000,
            "forma_pagamento": "01",
            "xml_raw": "<xml/>",
        },
        "itens": [_item()] if itens is None else itens,
    }


@pytest.fixture
def conexao(tmp_path):
    con = abrir_banco(tmp_path / "nfe.db")
    con.commit()  # linha de base: o esquema fica fora do que o C1.5 desfaz
    yield con
    con.close()


def _produto_do_item(con, chave, n_item=1):
    return con.execute(
        "SELECT produto_id FROM itens WHERE nota_chave = ? AND n_item = ?", (chave, n_item)
    ).fetchone()[0]


def _campo(con, produto_id, coluna):
    return con.execute(f"SELECT {coluna} FROM produtos WHERE id = ?", (produto_id,)).fetchone()[0]


def _conta(con, tabela):
    return con.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]


# --- C1.1 -------------------------------------------------------------------
def test_item_com_gtin_aponta_para_produto_de_identidade_gtin(conexao):
    persistir_nota(conexao, _extraido())

    produto_id = _produto_do_item(conexao, CHAVE_A)
    assert produto_id is not None
    assert _campo(conexao, produto_id, "identidade_origem") == "gtin"
    assert _campo(conexao, produto_id, "gtin") == GTIN


# --- C1.2 -------------------------------------------------------------------
def test_item_sem_gtin_aponta_para_produto_de_identidade_texto(conexao):
    """Sem codigo de barras a chave e (descricao normalizada, CNPJ da loja), e o
    CNPJ que entra e o da NOTA — nao existe outro lugar de onde tira-lo."""
    persistir_nota(conexao, _extraido(itens=[_item(gtin=None)]))

    produto_id = _produto_do_item(conexao, CHAVE_A)
    assert _campo(conexao, produto_id, "identidade_origem") == "texto"
    assert _campo(conexao, produto_id, "emit_cnpj") == CNPJ_A


# --- C1.3 -------------------------------------------------------------------
def test_o_mesmo_gtin_em_lojas_diferentes_cai_no_mesmo_produto(conexao):
    """O codigo de barras e global: duas lojas que vendem a mesma caixa mandam o
    mesmo GTIN, e o casamento entre elas vale."""
    persistir_nota(conexao, _extraido())
    persistir_nota(conexao, _extraido(chave=CHAVE_B, emit_cnpj=CNPJ_B))

    assert _produto_do_item(conexao, CHAVE_A) == _produto_do_item(conexao, CHAVE_B)
    assert _conta(conexao, "produtos") == 1


# --- C1.4 -------------------------------------------------------------------
def test_a_mesma_descricao_sem_gtin_em_lojas_diferentes_da_produtos_diferentes(conexao):
    """A assimetria que a story 008 declarou como requisito: casar por texto
    ENTRE lojas misturaria produtos diferentes no mesmo historico de preco."""
    persistir_nota(conexao, _extraido(itens=[_item(gtin=None)]))
    persistir_nota(conexao, _extraido(chave=CHAVE_B, emit_cnpj=CNPJ_B, itens=[_item(gtin=None)]))

    assert _produto_do_item(conexao, CHAVE_A) != _produto_do_item(conexao, CHAVE_B)
    assert _conta(conexao, "produtos") == 2


# --- C1.5 -------------------------------------------------------------------
def test_persistir_nota_nao_commita_e_o_rollback_desfaz_tudo(conexao):
    """🔴 A divida `a`. Resolver o produto e inserir o item tem de ser a MESMA
    transacao: com o commit dentro da funcao, um item entraria sem produto se a
    resolucao de um item posterior falhasse.

    ⭐ A fixture commita o esquema antes, entao o que este `rollback` desfaz e
    exatamente o que `persistir_nota` escreveu, e nada mais.
    """
    persistir_nota(conexao, _extraido())
    conexao.rollback()

    assert _conta(conexao, "notas") == 0
    assert _conta(conexao, "itens") == 0
    assert _conta(conexao, "produtos") == 0


# --- C1.6 -------------------------------------------------------------------
def test_nota_duplicada_nao_cria_produto_nenhum(conexao):
    """A checagem de duplicada acontece ANTES de qualquer resolucao: a segunda
    passada da mesma nota sai pela porta de cima e nao toca em `produtos`."""
    persistir_nota(conexao, _extraido())
    antes = _conta(conexao, "produtos")

    assert persistir_nota(conexao, _extraido()) == "duplicada"
    assert _conta(conexao, "produtos") == antes


# --- C1.7 -------------------------------------------------------------------
def test_o_produto_criado_nasce_sem_categoria_e_sem_origem(conexao):
    """🔴 A importacao resolve IDENTIDADE e para ai (D1). `categoria_id` e
    `origem` NULL sao exatamente o estado "pendente" que a varredura procura —
    quem classifica e outro modulo, chamado por quem tem taxonomia carregada."""
    persistir_nota(conexao, _extraido())

    produto_id = _produto_do_item(conexao, CHAVE_A)
    assert _campo(conexao, produto_id, "categoria_id") is None
    assert _campo(conexao, produto_id, "origem") is None


# --- C1.8 -------------------------------------------------------------------
def test_item_sem_gtin_em_nota_sem_cnpj_levanta(conexao):
    """O erro SOBE inteiro. Engoli-lo deixaria `produto_id` NULL em silencio, e
    a chave de texto sem loja nao identificaria nada — ela so vale DENTRO de uma
    loja."""
    with pytest.raises(ValueError):
        persistir_nota(conexao, _extraido(emit_cnpj=None, itens=[_item(gtin=None)]))

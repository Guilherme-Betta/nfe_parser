"""Testes da categoria na saida JSON — story 013, tarefa 2.

🔴 O PORQUE de cada criterio mora em `specs/013-integracao/spec.md` §4 (bloco C2)
e §3 (decisoes D7, D8, D9). ⛔ Nao o repita aqui: aquela spec NAO e enviada ao
modelo local, e este arquivo e.

Congelados por commit ANTES da implementacao; o modelo local le (`--read`).

⭐ O banco e montado com INSERT direto, e ⛔ nao por `carregar_seed_padrao`: a
taxonomia real muda quando alguem edita o seed, e um oraculo preso a ela
reprovaria por motivo alheio a esta tarefa.

⚠️ `test_itens_no_json.py` tambem afirma as chaves do item, com igualdade
estrita. Ele foi ALTERADO nesta story, de proposito, e a razao esta na D12.
"""

import json

import pytest

from nfe_parser.banco import abrir_banco
from nfe_parser.serializacao import nota_para_json

CHAVE = "35260411111111000111550010000000011000000017"

QUEIJO, BUCKET = 3, 9

# 🔒 As dez chaves publicadas pela story 006, mais as duas que ESTA tarefa
# acrescenta. A ordem faz parte do contrato, e o C2.4 a afirma inteira.
CHAVES_DO_ITEM = [
    "n_item",
    "descricao",
    "cprod",
    "ncm",
    "gtin",
    "quantidade",
    "unidade",
    "valor_unitario",
    "valor_linha_centavos",
    "valor_linha",
    "categoria_slug",
    "categoria",
]


@pytest.fixture
def conexao(tmp_path):
    con = abrir_banco(tmp_path / "nfe.db")
    con.executemany(
        "INSERT INTO categorias (id, slug, nome, is_bucket) VALUES (?, ?, ?, ?)",
        [(QUEIJO, "queijo-minas", "Queijo Minas", 0), (BUCKET, "uncategorized", "Nao Classificado", 1)],
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


def _produto(con, categoria_id=None, origem=None, gtin="7891111111111"):
    cursor = con.execute(
        "INSERT INTO produtos (identidade_origem, gtin, descricao_exemplo, categoria_id,"
        " origem, criado_em, atualizado_em) VALUES ('gtin', ?, 'QUEIJO 500G', ?, ?,"
        " '2026-04-01T13:00:00+00:00', '2026-04-01T13:00:00+00:00')",
        (gtin, categoria_id, origem),
    )
    return cursor.lastrowid


def _item(con, n_item=1, produto_id=None):
    con.execute(
        "INSERT INTO itens (nota_chave, n_item, descricao, cprod, ncm, gtin, quantidade,"
        " unidade, valor_unitario, valor_linha, criado_em, produto_id)"
        " VALUES (?, ?, 'QUEIJO 500G', 'Q1', '04039000', NULL, '1.0000', 'UN', '10.00',"
        " 1000, '2026-04-01T13:00:00+00:00', ?)",
        (CHAVE, n_item, produto_id),
    )


def _itens(con):
    return json.loads(nota_para_json(con, CHAVE))["itens"]


# --- C2.1 -------------------------------------------------------------------
def test_item_de_produto_classificado_sai_com_slug_e_nome(conexao):
    _item(conexao, produto_id=_produto(conexao, categoria_id=QUEIJO, origem="ncm"))

    item = _itens(conexao)[0]
    assert item["categoria_slug"] == "queijo-minas"
    assert item["categoria"] == "Queijo Minas"


# --- C2.2 -------------------------------------------------------------------
def test_item_sem_produto_sai_com_as_duas_chaves_em_None(conexao):
    """Item de nota importada ANTES desta story tem `produto_id` NULL, e nao ha
    backfill. A chave aparece assim mesmo: `None` ja diz "nao tem"."""
    _item(conexao, produto_id=None)

    item = _itens(conexao)[0]
    assert item["categoria_slug"] is None
    assert item["categoria"] is None


# --- C2.3 -------------------------------------------------------------------
def test_produto_sem_categoria_sai_com_as_duas_chaves_em_None(conexao):
    _item(conexao, produto_id=_produto(conexao, categoria_id=None))

    item = _itens(conexao)[0]
    assert item["categoria_slug"] is None
    assert item["categoria"] is None


# --- C2.4 -------------------------------------------------------------------
def test_as_chaves_do_item_sao_as_dez_antigas_mais_as_duas_novas(conexao):
    """🔒 Afirma a lista INTEIRA, na ordem. A premissa: a story 006 publicou dez
    chaves, e esta tarefa acrescenta `categoria_slug` e `categoria` NO FIM. Se
    este teste ficar vermelho um dia, a pergunta e "o contrato mudou?" antes de
    "como faco passar?"."""
    _item(conexao, produto_id=_produto(conexao, categoria_id=QUEIJO, origem="ncm"))

    assert list(_itens(conexao)[0]) == CHAVES_DO_ITEM


# --- C2.5 -------------------------------------------------------------------
def test_produto_no_bucket_sai_com_o_nome_do_bucket_e_nao_com_None(conexao):
    """Estar no bucket e diferente de nao ter produto: o bucket E uma categoria,
    e o JSON tem de dizer isso."""
    _item(conexao, produto_id=_produto(conexao, categoria_id=BUCKET, origem=None))

    item = _itens(conexao)[0]
    assert item["categoria_slug"] == "uncategorized"
    assert item["categoria"] == "Nao Classificado"


# --- C2.6 -------------------------------------------------------------------
def test_itens_sem_produto_continuam_saindo_na_lista(conexao):
    """🔴 O pior defeito possivel nesta tarefa. Com `INNER JOIN` os dois itens
    sem produto sumiriam, a nota perderia linhas em silencio, e a soma dos itens
    deixaria de bater com o total da nota.

    A premissa do literal `3`: a fixture insere tres itens, e so um tem produto.
    """
    _item(conexao, n_item=1, produto_id=_produto(conexao, categoria_id=QUEIJO, origem="ncm"))
    _item(conexao, n_item=2, produto_id=None)
    _item(conexao, n_item=3, produto_id=None)

    itens = _itens(conexao)
    assert len(itens) == 3
    assert [i["n_item"] for i in itens] == [1, 2, 3]


# --- C2.7 -------------------------------------------------------------------
def test_produto_id_e_origem_nao_aparecem_no_item(conexao):
    """`produto_id` e chave artificial do SQLite, pela mesma regra que ja deixa
    `id` e `nota_chave` de fora. `origem` fica de fora porque e o campo a que a
    story 012 vai acrescentar um valor novo (risco R1)."""
    _item(conexao, produto_id=_produto(conexao, categoria_id=QUEIJO, origem="ncm"))

    item = _itens(conexao)[0]
    assert "produto_id" not in item
    assert "origem" not in item

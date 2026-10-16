"""Testes de `buscar_categoria_por_ncm` — story 009, tarefa 1.

🔴 O PORQUE de cada criterio mora em `specs/009-cascata-deterministica/spec.md`
§4 (bloco C1) e §2 (decisao D1). ⛔ Nao o repita aqui: a spec NAO e enviada ao
modelo local, e este arquivo e.

Congelados por commit ANTES da implementacao; o modelo local le (`--read`).
⚠️ A fixture semeia as PROPRIAS linhas: `categorias` e `ncm_ancora` nascem
vazias da migracao v1, e o seed real e a story 010, que vem DEPOIS desta.
"""

import pytest

from nfe_parser.banco import abrir_banco
from nfe_parser.categorizacao import buscar_categoria_por_ncm

MERCADO, LATICINIOS, QUEIJO, BEBIDAS = 1, 2, 3, 4

CATEGORIAS = [
    (MERCADO, "mercado", "Mercado"),
    (LATICINIOS, "laticinios", "Laticinios"),
    (QUEIJO, "queijo-minas", "Queijo Minas"),
    (BEBIDAS, "bebidas", "Bebidas"),
]

# Tres larguras do mesmo ramo, e um prefixo de 8 sozinho no seu.
ANCORAS = [("04", MERCADO), ("0403", LATICINIOS), ("04039000", QUEIJO), ("22021000", BEBIDAS)]


@pytest.fixture
def conexao(tmp_path):
    con = abrir_banco(tmp_path / "nfe.db")
    con.executemany("INSERT INTO categorias (id, slug, nome) VALUES (?, ?, ?)", CATEGORIAS)
    con.executemany("INSERT INTO ncm_ancora (prefixo, categoria_id) VALUES (?, ?)", ANCORAS)
    yield con
    con.close()


# --- C1.1 -------------------------------------------------------------------
def test_prefixo_de_oito_digitos_casa(conexao):
    assert buscar_categoria_por_ncm(conexao, "22021000") == BEBIDAS


# --- C1.2 -------------------------------------------------------------------
def test_com_oito_quatro_e_dois_casando_vence_o_de_oito(conexao):
    """🔴 O coracao da tarefa: o prefixo MAIS LONGO ganha."""
    assert buscar_categoria_por_ncm(conexao, "04039000") == QUEIJO


# --- C1.3 -------------------------------------------------------------------
def test_sem_o_de_oito_vence_o_de_quatro(conexao):
    assert buscar_categoria_por_ncm(conexao, "04031000") == LATICINIOS


# --- C1.4 -------------------------------------------------------------------
def test_so_o_de_dois_casando_devolve_o_de_dois(conexao):
    assert buscar_categoria_por_ncm(conexao, "04991234") == MERCADO


# --- C1.5 -------------------------------------------------------------------
def test_nenhum_prefixo_casa_devolve_none(conexao):
    assert buscar_categoria_por_ncm(conexao, "99999999") is None


# --- C1.6 -------------------------------------------------------------------
@pytest.mark.parametrize("vazio", ["", None])
def test_ncm_vazio_devolve_none(conexao, vazio):
    """🔴 D1: item sem NCM e caso NORMAL em NFC-e, nao erro."""
    assert buscar_categoria_por_ncm(conexao, vazio) is None


# --- C1.7 -------------------------------------------------------------------
def test_ncm_mais_curto_que_oito_digitos_funciona(conexao):
    """O `IN` e um conjunto: prefixo repetido na lista nao atrapalha."""
    assert buscar_categoria_por_ncm(conexao, "0403") == LATICINIOS

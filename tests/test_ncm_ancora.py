"""Testes de `buscar_categoria_por_ncm` — contrato da story 009, tarefa 1.

Escritos ANTES da implementacao (passo 2 do loop) e congelados por commit. O
modelo local recebe este arquivo como LEITURA (`--read`), nunca como editavel.

Criterios em `specs/009-cascata-deterministica/spec.md` §4, bloco C1.

⚠️ A fixture semeia as PROPRIAS linhas de `categorias` e `ncm_ancora`. As duas
tabelas nascem vazias da migracao v1 e o seed real e a story 010 -- que vem
DEPOIS desta. Um teste que traz o proprio dado nao quebra quando o seed mudar.
"""

import pytest

from nfe_parser.banco import abrir_banco
from nfe_parser.categorizacao import buscar_categoria_por_ncm

# Taxonomia inventada para o teste. ⛔ NAO e o seed da 010.
MERCADO, LATICINIOS, QUEIJO, BEBIDAS = 1, 2, 3, 4

CATEGORIAS = [
    (MERCADO, "mercado", "Mercado", None),
    (LATICINIOS, "laticinios", "Laticinios", MERCADO),
    (QUEIJO, "queijo-minas", "Queijo Minas", LATICINIOS),
    (BEBIDAS, "bebidas", "Bebidas", None),
]

# Tres larguras do mesmo ramo, e um prefixo de 8 sozinho no seu.
ANCORAS = [
    ("04", MERCADO),
    ("0403", LATICINIOS),
    ("04039000", QUEIJO),
    ("22021000", BEBIDAS),
]


@pytest.fixture
def conexao(tmp_path):
    con = abrir_banco(tmp_path / "nfe.db")
    con.executemany(
        "INSERT INTO categorias (id, slug, nome, parent_id) VALUES (?, ?, ?, ?)",
        CATEGORIAS,
    )
    con.executemany("INSERT INTO ncm_ancora (prefixo, categoria_id) VALUES (?, ?)", ANCORAS)
    yield con
    con.close()


# --- C1.1 -------------------------------------------------------------------
def test_prefixo_de_oito_digitos_casa(conexao):
    """`22021000` esta no mapa e nem `22` nem `2202` estao."""
    assert buscar_categoria_por_ncm(conexao, "22021000") == BEBIDAS


# --- C1.2 -------------------------------------------------------------------
def test_com_oito_quatro_e_dois_casando_vence_o_de_oito(conexao):
    """🔴 O coracao da tarefa: o prefixo MAIS LONGO ganha.

    `04039000` casa os tres: `04` (Mercado), `0403` (Laticinios) e ele mesmo
    (Queijo Minas). A resposta certa e a mais especifica -- e sem um `ORDER BY
    LENGTH(prefixo) DESC` o SQLite devolveria qualquer uma das tres.
    """
    assert buscar_categoria_por_ncm(conexao, "04039000") == QUEIJO


# --- C1.3 -------------------------------------------------------------------
def test_sem_o_de_oito_vence_o_de_quatro(conexao):
    """`04031000` nao esta no mapa; `0403` e `04` estao."""
    assert buscar_categoria_por_ncm(conexao, "04031000") == LATICINIOS


# --- C1.4 -------------------------------------------------------------------
def test_so_o_de_dois_casando_devolve_o_de_dois(conexao):
    """`0499...` cai no pai: o mapa curado nao desce alem de `04` neste ramo."""
    assert buscar_categoria_por_ncm(conexao, "04991234") == MERCADO


# --- C1.5 -------------------------------------------------------------------
def test_nenhum_prefixo_casa_devolve_none(conexao):
    assert buscar_categoria_por_ncm(conexao, "99999999") is None


# --- C1.6 -------------------------------------------------------------------
@pytest.mark.parametrize("vazio", ["", None])
def test_ncm_vazio_devolve_none(conexao, vazio):
    """🔴 Item sem NCM e caso NORMAL em NFC-e, nao erro (D1).

    A guarda tem de vir ANTES das fatias, por dois motivos: `None[:8]` levanta
    `TypeError`, e em SQL `WHERE prefixo = NULL` nao casa com nada -- a consulta
    responderia "nao achei" pelo motivo errado, em silencio. Quem chama manda
    para o bucket, que e o passo 4 da cascata.
    """
    assert buscar_categoria_por_ncm(conexao, vazio) is None


# --- C1.7 -------------------------------------------------------------------
def test_ncm_mais_curto_que_oito_digitos_funciona(conexao):
    """`"0403"[:8]` e `"0403"[:4]` dao o mesmo valor, e o `IN` e um conjunto.

    Prefixo repetido na lista nao atrapalha, e por isso a implementacao nao
    precisa de nenhum `if` sobre o comprimento do NCM.
    """
    assert buscar_categoria_por_ncm(conexao, "0403") == LATICINIOS

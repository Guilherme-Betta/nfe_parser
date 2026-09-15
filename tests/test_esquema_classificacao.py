"""Testes da migracao v1 — contrato da story 007, tarefa 2.

Escritos ANTES da implementacao (passo 2 do loop) e congelados por commit. O
modelo local recebe este arquivo como LEITURA (`--read`), nunca como editavel.

Criterios em `specs/007-migracao-esquema/spec.md` §4, bloco C2.

⚠️ Tudo aqui e conferido por SUBCONJUNTO (`<=`), e a versao por `>=`. A tarefa 3
acrescenta a migracao v2, que cria mais um indice e leva a versao a 2 — com
igualdade estrita, este modulo ficaria vermelho na tarefa seguinte. A igualdade
mora no modulo da ultima tarefa que mexe naquela saida.
"""

import sqlite3

import pytest

from nfe_parser.banco import abrir_banco
from nfe_parser.migracoes import versao_do_banco

TABELAS_NOVAS = {"categorias", "ncm_ancora", "produtos", "tags", "produto_tags"}
INDICES_NOVOS = {"ux_produtos_gtin", "ux_produtos_texto"}
TABELAS_DA_SPEC_01 = {"importacoes", "notas", "itens", "importacao_arquivos"}

DH = "2026-01-02T10:00:00-03:00"
CNPJ = "12345678000199"


@pytest.fixture
def conexao(tmp_path):
    con = abrir_banco(tmp_path / "nfe.db")
    yield con
    con.close()


def _nomes(con, tipo):
    linhas = con.execute("SELECT name FROM sqlite_master WHERE type = ?", (tipo,))
    return {linha[0] for linha in linhas}


def _inserir_produto(con, origem, gtin=None, descricao=None, cnpj=None):
    con.execute(
        "INSERT INTO produtos (identidade_origem, gtin, descricao_normalizada,"
        " emit_cnpj, criado_em, atualizado_em) VALUES (?, ?, ?, ?, ?, ?)",
        (origem, gtin, descricao, cnpj, DH, DH),
    )


# --- C2.1 -------------------------------------------------------------------
def test_cria_as_cinco_tabelas_da_classificacao(conexao):
    assert TABELAS_NOVAS <= _nomes(conexao, "table")


# --- C2.2 -------------------------------------------------------------------
def test_cria_os_dois_indices_unicos_parciais(conexao):
    assert INDICES_NOVOS <= _nomes(conexao, "index")


# --- C2.3 -------------------------------------------------------------------
def test_as_tabelas_da_spec_01_continuam_la(conexao):
    """A migracao acrescenta; nao substitui o esquema anterior."""
    assert TABELAS_DA_SPEC_01 <= _nomes(conexao, "table")


# --- C2.4 -------------------------------------------------------------------
def test_dois_produtos_com_o_mesmo_gtin_sao_recusados(conexao):
    _inserir_produto(conexao, "gtin", gtin="7891234567890")

    with pytest.raises(sqlite3.IntegrityError):
        _inserir_produto(conexao, "gtin", gtin="7891234567890")


# --- C2.5 -------------------------------------------------------------------
def test_dois_produtos_sem_gtin_sao_aceitos(conexao):
    """E este criterio que prova que o indice foi escrito com `WHERE`.

    `ux_produtos_gtin` vale so para quem TEM gtin. Produto sem codigo de barras
    e a maioria das linhas de uma NFC-e: se o indice nao fosse parcial, o
    segundo produto sem gtin seria recusado e o app nao importaria nota nenhuma.
    """
    _inserir_produto(conexao, "texto", descricao="arroz 5kg", cnpj=CNPJ)
    _inserir_produto(conexao, "texto", descricao="feijao 1kg", cnpj=CNPJ)

    assert conexao.execute("SELECT COUNT(*) FROM produtos").fetchone()[0] == 2


# --- C2.6 -------------------------------------------------------------------
def test_mesma_descricao_e_cnpj_sem_gtin_sao_recusados(conexao):
    _inserir_produto(conexao, "texto", descricao="arroz 5kg", cnpj=CNPJ)

    with pytest.raises(sqlite3.IntegrityError):
        _inserir_produto(conexao, "texto", descricao="arroz 5kg", cnpj=CNPJ)


# --- C2.7 -------------------------------------------------------------------
def test_a_versao_do_banco_avancou(conexao):
    """`>=`, nunca `== 1`: a tarefa 3 leva a versao a 2."""
    assert versao_do_banco(conexao) >= 1

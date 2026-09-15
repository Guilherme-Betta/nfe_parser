"""Testes da migracao v2 — contrato da story 007, tarefa 3.

Escritos ANTES da implementacao e congelados por commit. Leitura (`--read`) para
o modelo local, nunca editavel.

Criterios em `specs/007-migracao-esquema/spec.md` §4, bloco C3.

⭐ Ultima tarefa que mexe na versao do banco, entao o unico modulo que pode
afirmar `== 2`. Os das tarefas 1 e 2 usam `len(MIGRACOES)` e `>= 1`.
"""

import sqlite3

import pytest

from nfe_parser.banco import abrir_banco, criar_esquema
from nfe_parser.migracoes import versao_do_banco

CHAVE = "0" * 44
DH = "2026-01-02T10:00:00-03:00"


@pytest.fixture
def conexao(tmp_path):
    con = abrir_banco(tmp_path / "nfe.db")
    yield con
    con.close()


def _colunas(con, tabela):
    return [linha[1] for linha in con.execute(f"PRAGMA table_info({tabela})")]


def _banco_legado(caminho):
    """Banco como a spec 01 o deixava: esquema antigo, dado dentro, versao 0."""
    con = sqlite3.connect(caminho)
    con.execute("PRAGMA foreign_keys = ON")
    criar_esquema(con)
    con.execute(
        "INSERT INTO notas (chave, modelo, dh_emi, valor_total, xml_raw, criado_em)"
        " VALUES (?, 55, ?, 1234, '<NFe/>', ?)",
        (CHAVE, DH, DH),
    )
    con.execute(
        "INSERT INTO itens (nota_chave, n_item, descricao, quantidade, valor_linha,"
        " criado_em) VALUES (?, 1, 'ARROZ 5KG', '1.0000', 1234, ?)",
        (CHAVE, DH),
    )
    con.commit()
    con.close()


# --- C3.1 -------------------------------------------------------------------
def test_itens_ganha_a_coluna_produto_id(conexao):
    assert "produto_id" in _colunas(conexao, "itens")


# --- C3.2 -------------------------------------------------------------------
def test_cria_o_indice_do_produto_em_itens(conexao):
    linhas = conexao.execute("SELECT name FROM sqlite_master WHERE type = 'index'")
    assert "idx_itens_produto" in {linha[0] for linha in linhas}


# --- C3.3 -------------------------------------------------------------------
def test_a_versao_final_do_banco_e_dois(conexao):
    assert versao_do_banco(conexao) == 2


# --- C3.4 -------------------------------------------------------------------
def test_reabrir_o_banco_nao_duplica_a_coluna(tmp_path):
    """Sem controle de versao a segunda abertura daria `duplicate column name`."""
    caminho = tmp_path / "nfe.db"

    abrir_banco(caminho).close()
    con = abrir_banco(caminho)
    colunas = _colunas(con, "itens")
    con.close()

    assert colunas.count("produto_id") == 1


# --- C3.5 -------------------------------------------------------------------
def test_banco_legado_migra_sem_perder_dado(tmp_path):
    """Confere o VALOR, nao so o COUNT — a licao da Fase 0."""
    caminho = tmp_path / "nfe.db"
    _banco_legado(caminho)

    con = abrir_banco(caminho)
    notas = con.execute("SELECT chave, valor_total, status FROM notas").fetchall()
    itens = con.execute("SELECT n_item, descricao, valor_linha FROM itens").fetchall()
    versao = versao_do_banco(con)
    con.close()

    assert notas == [(CHAVE, 1234, "ok")]
    assert itens == [(1, "ARROZ 5KG", 1234)]
    assert versao == 2


# --- C3.6 -------------------------------------------------------------------
def test_o_item_legado_fica_com_produto_id_nulo(tmp_path):
    """Ninguem sabe ainda qual produto e cada item. NULL e a resposta honesta."""
    caminho = tmp_path / "nfe.db"
    _banco_legado(caminho)

    con = abrir_banco(caminho)
    produto_id = con.execute("SELECT produto_id FROM itens").fetchone()[0]
    con.close()

    assert produto_id is None


# --- C3.7 (caminho de erro) -------------------------------------------------
def test_produto_id_inexistente_e_recusado(conexao):
    """O `REFERENCES produtos(id)` do ALTER TABLE tem de valer de verdade."""
    conexao.execute(
        "INSERT INTO notas (chave, modelo, dh_emi, valor_total, xml_raw, criado_em)"
        " VALUES (?, 55, ?, 1234, '<NFe/>', ?)",
        (CHAVE, DH, DH),
    )

    with pytest.raises(sqlite3.IntegrityError):
        conexao.execute(
            "INSERT INTO itens (nota_chave, n_item, descricao, quantidade,"
            " valor_linha, criado_em, produto_id) VALUES (?, 1, 'X', '1', 1, ?, 999)",
            (CHAVE, DH),
        )

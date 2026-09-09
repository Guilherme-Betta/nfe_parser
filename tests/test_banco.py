"""Testes do esquema do banco — contrato da story 001-esquema-do-banco.

Escritos ANTES da implementacao (passo 2 do loop) e congelados por commit. O
modelo local recebe este arquivo como LEITURA (`--read`), nunca como arquivo
editavel: se ele puder editar o teste, ele edita o teste para faze-lo passar,
que e o caminho mais curto para o objetivo dado.

Criterios em `specs/001-esquema-do-banco/spec.md` §4.
"""

import sqlite3

import pytest

from nfe_parser.banco import abrir_banco

TABELAS_ESPERADAS = {"importacoes", "notas", "itens", "importacao_arquivos"}
INDICES_ESPERADOS = {"idx_notas_dh_emi", "idx_itens_nota", "idx_itens_ncm", "idx_itens_gtin"}

CHAVE = "0" * 44
DH = "2026-01-02T10:00:00-03:00"


@pytest.fixture
def conexao(tmp_path):
    """Um banco novo por teste, fechado no fim."""
    con = abrir_banco(tmp_path / "nfe.db")
    yield con
    con.close()


def _nomes(con, tipo):
    linhas = con.execute("SELECT name FROM sqlite_master WHERE type = ?", (tipo,))
    return {linha[0] for linha in linhas}


def _inserir_nota(con, chave=CHAVE, status="ok"):
    con.execute(
        "INSERT INTO notas (chave, modelo, dh_emi, valor_total, status, xml_raw, criado_em)"
        " VALUES (?, 55, ?, 1234, ?, '<NFe/>', ?)",
        (chave, DH, status, DH),
    )


def _inserir_item(con, nota_chave=CHAVE, n_item=1):
    con.execute(
        "INSERT INTO itens (nota_chave, n_item, descricao, quantidade, valor_linha, criado_em)"
        " VALUES (?, ?, 'ARROZ 5KG', '1.0000', 1234, ?)",
        (nota_chave, n_item, DH),
    )


# --- criterio 1 -------------------------------------------------------------
def test_cria_o_arquivo_do_banco(tmp_path):
    caminho = tmp_path / "nfe.db"
    assert not caminho.exists()

    con = abrir_banco(caminho)
    con.close()

    assert caminho.exists()


# --- criterio 2 -------------------------------------------------------------
def test_cria_as_quatro_tabelas(conexao):
    assert TABELAS_ESPERADAS <= _nomes(conexao, "table")


# --- criterio 3 -------------------------------------------------------------
def test_cria_os_quatro_indices(conexao):
    assert INDICES_ESPERADOS <= _nomes(conexao, "index")


# --- criterio 4 -------------------------------------------------------------
def test_reabrir_o_banco_preserva_os_dados(tmp_path):
    """Idempotencia do DDL: rodar de novo nao pode zerar nem duplicar nada.

    Confere o VALOR, nao so o COUNT. Licao da Fase 0: um teste de idempotencia
    que olhava so `COUNT(*)` teria aprovado uma implementacao que sobrescrevia
    os valores.
    """
    caminho = tmp_path / "nfe.db"

    con = abrir_banco(caminho)
    _inserir_nota(con)
    con.commit()
    con.close()

    con = abrir_banco(caminho)  # segunda vez: o DDL roda de novo
    linhas = con.execute("SELECT chave, valor_total, status FROM notas").fetchall()
    con.close()

    assert linhas == [(CHAVE, 1234, "ok")]


# --- criterio 5 (caminho de erro) -------------------------------------------
def test_item_orfao_e_recusado(conexao):
    """`PRAGMA foreign_keys` vem DESLIGADO por padrao no SQLite, por conexao.

    Sem ligar o pragma, este INSERT passa em silencio mesmo com o `REFERENCES`
    escrito certo no DDL. Nada no esquema denuncia isso — so este teste.
    """
    with pytest.raises(sqlite3.IntegrityError):
        _inserir_item(conexao, nota_chave="chave-que-nao-existe")


# --- criterio 6 (caminho de erro) -------------------------------------------
def test_status_fora_do_dominio_e_recusado(conexao):
    """`duplicada` e desfecho de IMPORTACAO, nao estado de nota (spec 01 §2)."""
    with pytest.raises(sqlite3.IntegrityError):
        _inserir_nota(conexao, status="duplicada")


# --- criterio 7 (caminho de erro) -------------------------------------------
def test_item_repetido_no_mesmo_n_item_e_recusado(conexao):
    _inserir_nota(conexao)
    _inserir_item(conexao, n_item=1)

    with pytest.raises(sqlite3.IntegrityError):
        _inserir_item(conexao, n_item=1)

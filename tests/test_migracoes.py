"""Testes do executor de migracoes — story 007, tarefa 1. Criterios: spec.md C1.

Congelado por commit; o modelo local le, nao edita.

⚠️ Injeta listas de migracao proprias em vez de exercitar o conteudo de
`MIGRACOES`: as tarefas 2 e 3 fazem o registro crescer. Remedio do risco R5.
"""

import sqlite3

import pytest

from nfe_parser.banco import abrir_banco
from nfe_parser.migracoes import MIGRACOES, aplicar_migracoes, versao_do_banco

TABELAS_DA_SPEC_01 = {"importacoes", "notas", "itens", "importacao_arquivos"}


@pytest.fixture
def conexao_crua():
    """Banco em memoria SEM esquema e SEM migracao — so o executor."""
    con = sqlite3.connect(":memory:")
    yield con
    con.close()


def _que_registra(registro, nome):
    """Uma migracao de mentira: nao toca no banco, so anota que rodou."""

    def migracao(conexao):
        registro.append(nome)

    return migracao


def _tres(registro):
    """As mesmas tres migracoes de mentira usadas por dois testes."""
    return [_que_registra(registro, nome) for nome in ("v1", "v2", "v3")]


def _tabelas(con):
    linhas = con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    return {linha[0] for linha in linhas}


# --- C1.1 -------------------------------------------------------------------
def test_banco_novo_comeca_na_versao_zero(conexao_crua):
    assert versao_do_banco(conexao_crua) == 0


# --- C1.3 -------------------------------------------------------------------
def test_aplica_todas_em_ordem_e_devolve_a_versao_final(conexao_crua):
    registro = []
    migracoes = _tres(registro)

    final = aplicar_migracoes(conexao_crua, migracoes)

    assert registro == ["v1", "v2", "v3"]
    assert final == 3
    assert versao_do_banco(conexao_crua) == 3


# --- C1.4 -------------------------------------------------------------------
def test_rodar_de_novo_nao_reaplica_nada(conexao_crua):
    registro = []
    migracoes = [_que_registra(registro, "v1"), _que_registra(registro, "v2")]

    aplicar_migracoes(conexao_crua, migracoes)
    registro.clear()
    final = aplicar_migracoes(conexao_crua, migracoes)

    assert registro == []
    assert final == 2


# --- C1.3 (retomada no meio) ------------------------------------------------
def test_banco_na_versao_1_roda_so_da_2_em_diante(conexao_crua):
    registro = []
    migracoes = _tres(registro)
    conexao_crua.execute("PRAGMA user_version = 1")

    aplicar_migracoes(conexao_crua, migracoes)

    assert registro == ["v2", "v3"]


# --- C1.5 -------------------------------------------------------------------
def test_migracao_que_falha_no_meio_nao_deixa_rastro(conexao_crua):
    """Atomicidade: a excecao sobe, a versao nao avanca, o efeito some.

    Versao avancada sem a migracao ter terminado deixaria o banco meio migrado
    para sempre — a abertura seguinte pularia essa migracao.
    """

    def v1(conexao):
        conexao.execute("CREATE TABLE tabela_da_v1 (x INTEGER)")

    def v2(conexao):
        conexao.execute("CREATE TABLE tabela_da_v2 (x INTEGER)")
        raise RuntimeError("falhou no meio da migracao")

    with pytest.raises(RuntimeError):
        aplicar_migracoes(conexao_crua, [v1, v2])

    tabelas = _tabelas(conexao_crua)
    assert "tabela_da_v1" in tabelas
    assert "tabela_da_v2" not in tabelas
    assert versao_do_banco(conexao_crua) == 1


# --- C1.7 -------------------------------------------------------------------
def test_abrir_banco_deixa_o_banco_na_versao_do_registro(tmp_path):
    """`len(MIGRACOES)`, nunca um literal: o registro cresce nas tarefas 2 e 3."""
    con = abrir_banco(tmp_path / "nfe.db")
    versao = versao_do_banco(con)
    con.close()

    assert versao == len(MIGRACOES)


def test_abrir_banco_preserva_as_tabelas_da_spec_01(tmp_path):
    """Subconjunto (`<=`), nunca igualdade: o esquema cresce na tarefa 2."""
    con = abrir_banco(tmp_path / "nfe.db")
    tabelas = _tabelas(con)
    con.close()

    assert TABELAS_DA_SPEC_01 <= tabelas

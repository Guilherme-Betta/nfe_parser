"""Guarda permanente do registro real de migracoes — escrito no PASSO 4.

⚠️ Este modulo NAO faz parte do oraculo de nenhuma tarefa. Os tres modulos do
passo 2 foram congelados por commit antes da implementacao e sao a evidencia do
que o modelo local recebeu; este nasceu depois, na revisao, para tapar uma
lacuna que a revisao encontrou.

A lacuna: `test_migracoes.py` prova que o EXECUTOR e atomico, mas prova isso com
migracoes injetadas. Nada ali olha para as migracoes de verdade. Uma migracao
real que usasse `executescript` faria COMMIT implicito, destruiria a transacao
aberta pelo executor, e a suite continuaria verde — a atomicidade sumiria em
silencio.

⭐ Este teste vale para as migracoes que as stories 008–013 acrescentarem: ele
percorre `MIGRACOES`, sem afirmar quantas sao.
"""

import sqlite3

import pytest

from nfe_parser.banco import criar_esquema
from nfe_parser.migracoes import MIGRACOES


@pytest.fixture
def conexao(tmp_path):
    """Banco com o esquema da spec 01, mas sem nenhuma migracao aplicada."""
    con = sqlite3.connect(tmp_path / "nfe.db")
    con.execute("PRAGMA foreign_keys = ON")
    criar_esquema(con)
    yield con
    con.close()


def test_nenhuma_migracao_real_fecha_a_transacao(conexao):
    """Roda cada migracao dentro de um BEGIN e confere que ela nao commitou.

    `conexao.in_transaction` cai para False assim que alguem commita. E o unico
    sintoma observavel de um `executescript` dentro de uma migracao.

    As migracoes rodam CUMULATIVAMENTE, na ordem do registro, porque uma
    migracao futura pode depender do que a anterior criou.
    """
    for indice, migracao in enumerate(MIGRACOES):
        conexao.execute("BEGIN")
        migracao(conexao)

        assert conexao.in_transaction, (
            f"a migracao v{indice + 1} ({migracao.__name__}) fechou a transacao —"
            " quase certamente usou executescript, que faz COMMIT implicito"
        )

        conexao.execute("COMMIT")

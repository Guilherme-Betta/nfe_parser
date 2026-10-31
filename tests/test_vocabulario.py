"""Vocabularios fechados em string viram `StrEnum` em `vocabulario.py`.

⭐ O teste que importa e o do CHECK: cada enum tem de ter EXATAMENTE os valores
que o banco aceita. Um valor novo num lado e nao no outro e o erro que, hoje,
so apareceria em producao, na gravacao.

Os outros tres guardam a armadilha de `StrEnum` vs `Enum`: o valor tem de
atravessar banco, JSON e template como a string crua, sem `Status.OK` no meio.
"""

import json
import re

import pytest

from nfe_parser.banco import abrir_banco
from nfe_parser.tipo_xml import tipo_do_xml
from nfe_parser.vocabulario import (
    IdentidadeProduto,
    OrigemClassificacao,
    ResultadoArquivo,
    StatusNota,
    TipoXml,
)


@pytest.fixture
def conexao(tmp_path):
    con = abrir_banco(tmp_path / "v.db")
    yield con
    con.close()


def _valores_do_check(conexao, tabela, coluna):
    ddl = conexao.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?", (tabela,)
    ).fetchone()[0]
    check = re.search(rf"CHECK \({coluna} IN \((.*?)\)\)", ddl, re.DOTALL)
    assert check, f"{tabela}.{coluna} nao tem CHECK ... IN"
    return set(re.findall(r"'([^']+)'", check.group(1)))


@pytest.mark.parametrize(
    ("enum", "tabela", "coluna"),
    [
        (StatusNota, "notas", "status"),
        (ResultadoArquivo, "importacao_arquivos", "resultado"),
        (OrigemClassificacao, "produtos", "origem"),
        (IdentidadeProduto, "produtos", "identidade_origem"),
    ],
)
def test_enum_e_check_do_banco_tem_os_mesmos_valores(conexao, enum, tabela, coluna):
    assert {m.value for m in enum} == _valores_do_check(conexao, tabela, coluna)


def test_tipo_do_xml_devolve_o_enum_e_cobre_todos_os_valores():
    assert tipo_do_xml("<quebrado") is TipoXml.INVALIDA
    assert {m.value for m in TipoXml} == {"nfe", "evento", "invalida", "nao_suportado_sat"}


def test_o_valor_atravessa_como_string_crua():
    assert str(StatusNota.CANCELADA) == "cancelada"
    assert f"{StatusNota.CANCELADA}" == "cancelada"
    assert StatusNota.CANCELADA == "cancelada"
    assert json.dumps({"status": StatusNota.OK}) == '{"status": "ok"}'


def test_sqlite_grava_o_enum_como_texto(conexao):
    conexao.execute("CREATE TABLE t (v TEXT)")
    conexao.execute("INSERT INTO t VALUES (?)", (OrigemClassificacao.MANUAL,))
    (valor,) = conexao.execute("SELECT v FROM t").fetchone()

    assert valor == "manual"
    assert type(valor) is str

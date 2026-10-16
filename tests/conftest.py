"""Fixtures compartilhadas pela suite.

O pytest carrega este arquivo sozinho, antes dos testes: uma fixture definida aqui
fica disponivel em qualquer `test_*.py` desta pasta, sem import nenhum.

⚠️ Um arquivo de teste que define a SUA `conexao` sobrepoe esta. E o que fazem os
arquivos cujo cenario precisa de algo a mais — categorias ja inseridas, um commit
de "linha de base" antes do teste, um banco em memoria.
"""

import pytest

from nfe_parser.banco import abrir_banco


@pytest.fixture
def conexao(tmp_path):
    """Um banco novo num arquivo temporario, com o esquema completo, fechado no fim."""
    con = abrir_banco(tmp_path / "nfe.db")
    yield con
    con.close()

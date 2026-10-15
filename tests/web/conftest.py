"""Fixtures da camada web (spec 03). Os helpers moram em `apoio.py`."""

import pytest
from fastapi.testclient import TestClient

from nfe_parser.banco import abrir_banco
from nfe_parser.web.app import criar_app


@pytest.fixture
def caminho_banco(tmp_path):
    """Numa subpasta que ainda NAO existe: o app tem de cria-la."""
    return tmp_path / "dados" / "nfe.db"


@pytest.fixture
def cliente(caminho_banco):
    return TestClient(criar_app(caminho_banco))


@pytest.fixture
def banco(caminho_banco, cliente):
    """Uma conexao propria ao mesmo arquivo, para conferir o que o app gravou.

    ⚠️ Depende de `cliente` de proposito: o arquivo so tem esquema e seed depois
    que o app subiu.
    """
    conexao = abrir_banco(caminho_banco)
    yield conexao
    conexao.close()

"""Shell e config da camada web — spec 03 §2, criterios C1 a C3."""

import pytest
from fastapi.testclient import TestClient

from nfe_parser.banco import abrir_banco
from nfe_parser.migracoes import versao_do_banco
from nfe_parser.web.app import criar_app, criar_app_do_ambiente


def _categorias(caminho):
    conexao = abrir_banco(caminho)
    try:
        return conexao.execute("SELECT COUNT(*) FROM categorias").fetchone()[0]
    finally:
        conexao.close()


# C1
def test_subir_o_app_cria_a_pasta_aplica_esquema_e_carrega_o_seed(cliente, caminho_banco):
    resposta = cliente.get("/api/health")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert caminho_banco.exists()
    conexao = abrir_banco(caminho_banco)
    try:
        assert corpo["schema_version"] == versao_do_banco(conexao)
    finally:
        conexao.close()
    assert corpo["status"] == "ok"
    assert corpo["llm_ativo"] is False
    assert corpo["contagens"]["categorias"] == _categorias(caminho_banco) > 0
    assert corpo["contagens"]["notas"] == 0


# C2
def test_subir_duas_vezes_nao_duplica_nem_erra(caminho_banco):
    criar_app(caminho_banco)
    depois_da_primeira = _categorias(caminho_banco)

    criar_app(caminho_banco)

    assert _categorias(caminho_banco) == depois_da_primeira


# C3
def test_do_ambiente_le_app_db_path_e_llm_desligado_por_padrao(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_DB_PATH", str(tmp_path / "env.db"))
    monkeypatch.delenv("OLLAMA_URL", raising=False)

    corpo = TestClient(criar_app_do_ambiente()).get("/api/health").json()

    assert (tmp_path / "env.db").exists()
    assert corpo["llm_ativo"] is False


def test_sem_app_db_path_o_app_nao_sobe(monkeypatch):
    monkeypatch.delenv("APP_DB_PATH", raising=False)
    monkeypatch.delenv("OLLAMA_URL", raising=False)

    with pytest.raises(ValueError, match="APP_DB_PATH"):
        criar_app_do_ambiente()


def test_llm_configurado_pela_metade_o_app_nao_sobe(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_DB_PATH", str(tmp_path / "env.db"))
    monkeypatch.setenv("OLLAMA_URL", "http://ollama.invalido:11434")
    monkeypatch.delenv("OLLAMA_MODELO", raising=False)

    with pytest.raises(ValueError, match="OLLAMA_MODELO"):
        criar_app_do_ambiente()


def test_llm_configurado_inteiro_aparece_ativo(tmp_path, monkeypatch):
    """Construir o `llm` nao chama a rede: subir com Ollama fora do ar funciona."""
    monkeypatch.setenv("APP_DB_PATH", str(tmp_path / "env.db"))
    monkeypatch.setenv("OLLAMA_URL", "http://ollama.invalido:11434")
    monkeypatch.setenv("OLLAMA_MODELO", "modelo-de-teste")
    monkeypatch.setenv("LLM_LIMIAR", "0.7")

    corpo = TestClient(criar_app_do_ambiente()).get("/api/health").json()

    assert corpo["llm_ativo"] is True

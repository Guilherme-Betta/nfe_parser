"""Artefatos de deploy — spec 06 §6, criterios D1 a D5 (estaticos, sem Docker).

⭐ O que precisa de um daemon Docker (D6 a D8: montar, subir, imagem limpa,
persistencia) roda no workflow `imagem.yml`. Aqui fica o que da para provar lendo
os arquivos — e e o que roda em todo CI, inclusive nesta maquina sem Docker.
"""

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).parent.parent


def _ler(nome):
    return (RAIZ / nome).read_text(encoding="utf-8")


def _env_vars_lidas_pelo_codigo():
    """Os nomes que `src/` le de `os.environ` — a lista que a documentacao tem de cobrir."""
    nomes = set()
    for arquivo in (RAIZ / "src").rglob("*.py"):
        nomes.update(
            re.findall(r'os\.environ(?:\.get)?[\(\[]\s*"([A-Z_]+)"', arquivo.read_text("utf-8"))
        )
    return nomes


# --- D1 Dockerfile ----------------------------------------------------------------


@pytest.fixture
def dockerfile():
    return _ler("Dockerfile")


def test_imagem_parte_do_python_do_ci(dockerfile):
    assert re.search(r"^FROM python:3\.11-slim\b", dockerfile, re.MULTILINE)


def test_copia_so_a_lista_branca(dockerfile):
    """🔴 `COPY . .` levaria para a imagem tudo o que o .dockerignore esquecesse."""
    origens = set()
    for linha in re.findall(r"^COPY\s+(.+)$", dockerfile, re.MULTILINE):
        *fontes, _destino = linha.split()
        origens.update(fonte.rstrip("/") for fonte in fontes if not fonte.startswith("--"))

    assert origens <= {"pyproject.toml", "README.md", "LICENSE", "src"}
    assert "src" in origens


def test_roda_sem_root(dockerfile):
    usuarios = re.findall(r"^USER\s+(\S+)", dockerfile, re.MULTILINE)

    assert usuarios
    assert usuarios[-1] not in {"root", "0"}


def test_banco_no_volume_e_fuso_definido(dockerfile):
    assert "APP_DB_PATH=/dados/nfe.db" in dockerfile
    assert re.search(r"^VOLUME\s+.*?/dados", dockerfile, re.MULTILINE)
    assert "tzdata" in dockerfile
    assert "TZ=America/Sao_Paulo" in dockerfile


def test_sobe_pela_factory_com_healthcheck(dockerfile):
    assert "nfe_parser.web.app:criar_app_do_ambiente" in dockerfile
    assert "--factory" in dockerfile
    assert re.search(r"^HEALTHCHECK\b.*?/api/health", dockerfile, re.MULTILINE | re.DOTALL)


# --- D2 .dockerignore -------------------------------------------------------------


def test_dockerignore_barra_segredo_banco_e_nota():
    linhas = {linha.strip() for linha in _ler(".dockerignore").splitlines()}

    assert {".env", "*.db", "*.sqlite*", "*.xml", "*.zip", ".git"} <= linhas


# --- D3 env vars documentadas -------------------------------------------------------


def test_o_codigo_le_as_env_vars_esperadas():
    """Ancora do D3: se a busca nao achasse nada, os dois testes abaixo passariam no vazio."""
    assert {"APP_DB_PATH", "OLLAMA_URL", "OLLAMA_MODELO", "LLM_LIMIAR"} <= (
        _env_vars_lidas_pelo_codigo()
    )


@pytest.mark.parametrize("arquivo", [".env.example", "docker-compose.yml"])
def test_toda_env_var_lida_pelo_codigo_esta_documentada(arquivo):
    texto = _ler(arquivo)

    faltando = {nome for nome in _env_vars_lidas_pelo_codigo() if nome not in texto}

    assert not faltando, f"{arquivo} nao menciona {sorted(faltando)}"


# --- D4 docker-compose ------------------------------------------------------------


@pytest.fixture
def compose():
    return _ler("docker-compose.yml")


def test_compose_persiste_em_volume_nomeado(compose):
    assert re.search(r"^\s+-\s+(\w[\w-]*):/dados\s*$", compose, re.MULTILINE)
    assert re.search(r"^volumes:\s*$", compose, re.MULTILINE)


def test_compose_alcanca_o_host_em_linux_e_publica_a_porta(compose):
    assert "host.docker.internal:host-gateway" in compose
    assert "8000:8000" in compose
    assert "TZ" in compose


def test_compose_nao_liga_o_llm_por_padrao(compose):
    """`${OLLAMA_URL:-}` vira string vazia sem `.env` — e vazio e LLM desligado."""
    assert re.search(r"OLLAMA_URL:\s*\$\{OLLAMA_URL:-\}", compose)


def test_compose_usa_a_imagem_publicada(compose):
    assert "ghcr.io/guilherme-betta/nfe-parser" in compose


# --- D5 docs e workflow -------------------------------------------------------------


def test_readme_ensina_a_subir_ligar_o_ollama_e_fazer_backup():
    readme = _ler("README.md")

    assert "docker compose up" in readme
    assert "OLLAMA_URL" in readme
    assert "backup" in readme.lower()


def test_workflow_monta_confere_e_publica_em_tag():
    workflow = _ler(".github/workflows/imagem.yml")

    assert "ghcr.io/guilherme-betta/nfe-parser" in workflow
    assert re.search(r"tags:\s*\n\s*-\s*[\"']?v\*", workflow)
    assert "imagem limpa" in workflow.lower()

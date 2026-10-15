# Imagem oficial do NF-e Despesas (spec 06). Sobe o app web; o banco mora no volume /dados.
#
# ⛔ LISTA BRANCA: so entram pyproject.toml, README.md, LICENSE e src/. Nunca `COPY . .`:
# o repositorio e publico, e banco, .env ou nota real nao podem entrar na imagem nem se o
# .dockerignore esquecer algum padrao.

FROM python:3.11-slim

# tzdata: sem os arquivos de fuso, TZ seria ignorado e o container ficaria em UTC calado —
# e o "mes corrente" do orcamento viraria as 21h do ultimo dia, no horario de Brasilia.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_DB_PATH=/dados/nfe.db \
    TZ=America/Sao_Paulo

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install . \
    && useradd --create-home --uid 1000 app \
    && mkdir -p /dados \
    && chown app /dados

USER app
VOLUME ["/dados"]
EXPOSE 8000

# A imagem slim nao tem curl: o proprio Python consulta o health.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import sys, urllib.request; sys.exit(urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status != 200)"

CMD ["uvicorn", "nfe_parser.web.app:criar_app_do_ambiente", "--factory", "--host", "0.0.0.0", "--port", "8000"]

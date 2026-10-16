# Spec — `deploy`

Empacota o app pra rodar **self-hosted em Docker** e o publica pro público. Lê `docs/historico/report_projeto_nfe.md` (§8, §10) como contexto; esta spec é o contrato. Não implementa feature nenhuma — só embala, configura, persiste e publica o que os outros componentes entregam. Faça o mais simples que funcione (§6); pare nas fronteiras (§5).

Decisões travadas (§8 do report): **web app em Docker**; **publicar `docker-compose` + imagem oficial**; instância do Gui roda no **`juicey`** (Windows), e a classificação alcança o **Ollama do host** via `host.docker.internal:11434`, **URL por env var**. Stack fixada: **Python + FastAPI + SQLite + Docker**. **Repo público** (§0): nenhum dado pessoal ou segredo na imagem, no compose ou em fixtures.

> Revisada em 2026-10-15, antes dos artefatos: env vars do LLM decididas pelo Gui (spec 03 §2), fuso
> horário (o "mês corrente" do orçamento usa o fuso da máquina) e imagem montada por lista branca.

## 1. Escopo

Dockerfile da imagem oficial, `docker-compose.yml` de referência, config por env, **persistência do SQLite em volume**, conectividade com o Ollama do host, e o **CI/publicação** (GitHub Actions + GHCR). Entrega roda o app existente; **não** cria tabelas, endpoints nem lógica.

## 2. Artefatos

- **`Dockerfile`** — base `python:3.11-slim` (a versão do CI); instala o pacote; roda **uvicorn** com `nfe_parser.web.app:criar_app_do_ambiente --factory` na porta 8000.
  - **Lista branca:** copia só `pyproject.toml`, `README.md`, `LICENSE` e `src/`. ⛔ Nunca `COPY . .` — assim banco, `.env` e nota real não entram nem se o `.dockerignore` falhar.
  - Roda como **usuário sem privilégio**; o banco mora em `/dados` (`APP_DB_PATH=/dados/nfe.db`), declarado como `VOLUME`.
  - `tzdata` instalado e `TZ` com padrão `America/Sao_Paulo` (sobrescrevível): sem os arquivos de fuso, o container cairia em UTC calado, e o mês corrente viraria às 21h do último dia.
  - `HEALTHCHECK` bate em `/api/health` com o próprio Python (a imagem slim não tem `curl`).
- **`docker-compose.yml`** — serviço `app` com a imagem do GHCR (e `build: .` para quem quiser montar local); **volume nomeado** em `/dados`; porta `8000`; env vars (§3); `extra_hosts: ["host.docker.internal:host-gateway"]` pra o mesmo compose funcionar **em Linux**.
- **`.env.example`** — documenta todas as env vars que o código lê, sem valor real.
- **`.dockerignore`** — barra `.env`, `*.db`/`*.sqlite*`, `*.xml`/`*.zip`, `.git`, `.venv`, caches — defesa em profundidade além da lista branca.
- **Docs** — `README` (subir via compose, ligar o Ollama, backup), `CONTRIBUTING`, `LICENSE` (já existem; o README é atualizado).

## 3. Config, persistência e Ollama

- **Só env var**: `APP_DB_PATH`, `OLLAMA_URL` (presente liga o LLM; ausente = **desligado**, o default), `OLLAMA_MODELO` e `LLM_LIMIAR` (obrigatórias quando `OLLAMA_URL` existe, sem valor padrão), e `TZ` — as mesmas que a `ingestão/UI` lê no boot (spec 03 §2).
- **Migração no startup** (runner versionado da spec 02, chamado pela spec 03): sobe → aplica schema/seed → serve. Deploy só garante que roda; não redefine.
- **Persistência:** SQLite é 1 arquivo no **volume nomeado** → reiniciar/atualizar o container **não perde dados**; backup = copiar o arquivo.
- **Ollama (juicey):** LLM off por default, então a imagem sobe **sem Ollama**. Ligado, `OLLAMA_URL=http://host.docker.internal:11434` alcança o Ollama do host Windows; o `extra_hosts` cobre Linux.

## 4. CI e publicação

- **`.github/workflows/ci.yml`** (existe): a cada push e PR, **lint + suíte de testes** no Python 3.11.
- **`.github/workflows/imagem.yml`**: a cada push e PR, **monta a imagem** e roda a **checagem de imagem limpa** (§6) — sem publicar. Em **tag `v*`**, além disso **publica no GHCR** (`ghcr.io/guilherme-betta/nfe-parser`) com a versão da tag e `latest`. `amd64` no mínimo (o `juicey` e o `lil` são x86); `arm64` = roadmap.

## 5. Fronteiras (não fazer aqui)

Qualquer feature (parser/classificação/orçamento/visualização/UI) · schema/migração (é da spec 02, chamada pela 03) · SEFAZ/QR · **rede do servidor** — Tailscale, Funnel, Cloudflare Tunnel, reverse proxy, TLS, domínio público são **infra do host self-hoster**, **não** da imagem · **roadmap:** Postgres, multi-arch garantido, orquestração além de compose.

## 6. Pronto = verde

Na suíte (estático, roda no CI comum):
- D1. O `Dockerfile` copia só a lista branca, roda sem root, aponta o banco para o volume, sobe pela factory e tem `HEALTHCHECK`.
- D2. O `.dockerignore` barra `.env`, banco, nota (`*.xml`, `*.zip`) e `.git`.
- D3. **Toda env var que o código lê** (`os.environ` em `src/`) aparece no `.env.example` e no `docker-compose.yml` — teste que se mantém sozinho quando surgir uma variável nova.
- D4. O `docker-compose.yml` tem volume nomeado, `extra_hosts` com `host-gateway`, porta e `TZ`; nenhum valor de LLM ligado por padrão.
- D5. O `README` explica `docker compose up`, como ligar o Ollama e o backup.

No Docker (workflow `imagem.yml`, e à mão quando houver daemon):
- D6. A imagem monta; o container sobe sem Ollama e `/api/health` responde verde.
- D7. **Imagem limpa:** dentro de `/app` e `/dados` da imagem publicada não há `.env`, `*.db`/`*.sqlite`, `*.xml` nem `*.zip`.
- D8. **Persistência:** importar, recriar o container sobre o mesmo volume, e a nota continua lá.
- Nenhum dado pessoal real em fixtures, compose, docs ou imagem.

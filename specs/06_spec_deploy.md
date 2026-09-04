# Spec — `deploy`

Empacota o app pra rodar **self-hosted em Docker** e o publica pro público. Lê `report_projeto_nfe.md` (§8, §10) como contexto; esta spec é o contrato. Não implementa feature nenhuma — só embala, configura, persiste e publica o que os outros componentes entregam. Faça o mais simples que funcione (§6); pare nas fronteiras (§5).

Decisões travadas (§8 do report): **web app em Docker**; **publicar `docker-compose` + imagem oficial**; instância do Gui roda no **`juicey`** (Windows), e a classificação alcança o **Ollama do host** via `host.docker.internal:11434`, **URL por env var**. Stack fixada: **Python + FastAPI + SQLite + Docker**. **Repo público** (§0): nenhum dado pessoal ou segredo na imagem, no compose ou em fixtures.

## 1. Escopo

Dockerfile da imagem oficial, `docker-compose.yml` de referência, config por env, **persistência do SQLite em volume**, conectividade com o Ollama do host, e o **CI/publicação** (GitHub Actions + registry). Entrega roda o app existente; **não** cria tabelas, endpoints nem lógica.

## 2. Artefatos

- **`Dockerfile`** — base Python slim; instala deps; roda **uvicorn** servindo o app FastAPI. **Não** copia banco, `.env` nem dado real pra dentro da imagem.
- **`docker-compose.yml`** — serviço `app`; **volume nomeado** pro arquivo SQLite (persistência); porta publicada; env vars (§3); `healthcheck` batendo em `/api/health`; `extra_hosts: ["host.docker.internal:host-gateway"]` pra o mesmo compose funcionar **em Linux** (no Docker Desktop/Windows do `juicey` já resolve nativo).
- **`.env.example`** — documenta todas as env vars, sem valor real.
- **`.dockerignore`** — barra `.env`, `*.db`/`*.sqlite`, notas/zip reais, `.git` — evita vazar dado local pro build público.
- **Docs mínimas** — `README` (subir via compose, setar Ollama), `.env.example`, `CONTRIBUTING`, `LICENSE` (§1/§10 do report — licença batida na criação do repo).

## 3. Config, persistência e Ollama

- **Só env var** (imagem pública não pode grudar no host do Gui): `APP_DB_PATH`, `LLM_ATIVO` (**default off**), `OLLAMA_URL`, `OLLAMA_MODEL`, `LLM_LIMIAR_CONFIANCA` — as mesmas que a `ingestão/UI` lê no boot.
- **Migração no startup** (runner versionado já definido na `ingestão/UI`): sobe → aplica schema/seed → serve. Deploy só garante que roda; não redefine.
- **Persistência:** SQLite é 1 arquivo em **volume nomeado** → reiniciar/atualizar o container **não perde dados**; backup = copiar o arquivo.
- **Ollama (juicey):** LLM off por default, então a imagem sobe **sem Ollama**. Ligado, `OLLAMA_URL=http://host.docker.internal:11434` alcança o Ollama do host Windows; documentar no README (e o `extra_hosts` cobre Linux).

## 4. CI e publicação

- **GitHub Actions** (§10): a cada push, **lint + suíte de testes** (as invariantes dos outros componentes); PR só entra verde.
- **Build da imagem** no CI; **publica no registry** (GHCR) em **release/tag versionada** + `latest`. `amd64` no mínimo (o `juicey` e o `lil` são x86); `arm64` opcional/roadmap.
- Imagem publicada é **limpa** — sem `.env`, sem `*.db`, sem nota real (garantido por `.dockerignore` + teste do §6).

## 5. Fronteiras (não fazer aqui)

Qualquer feature (parser/classificação/orçamento/visualização/UI) · schema/migração (é da `ingestão/UI`) · SEFAZ/QR · **rede do servidor** — Tailscale, Funnel, Cloudflare Tunnel, reverse proxy, TLS, domínio público são **infra do host self-hoster** (escolha de quem sobe), **não** da imagem · **roadmap:** Postgres, multi-arch garantido, orquestração além de compose.

## 6. Pronto = verde

- **`docker compose up`** sobe o app; **`/api/health` verde**; banco persiste no volume (**reiniciar o container não perde dados**).
- **LLM off por default** → sobe **sem Ollama**; com `OLLAMA_URL` setada, alcança `host.docker.internal` (documentado); base determinística funciona sem nada disso.
- **Imagem limpa:** teste/checagem confirma que a imagem publicada **não** contém `.env`, `*.db`/`*.sqlite` nem nota real (`.dockerignore` cobre).
- **CI verde:** lint + testes a cada push; build da imagem; publish no GHCR em release/tag.
- **`.env.example`** lista todas as env vars; **README** tem o passo de subir + setar Ollama.
- Nenhum dado pessoal real em fixtures, compose, docs ou imagem.

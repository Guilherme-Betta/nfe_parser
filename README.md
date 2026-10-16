# NF-e Despesas

Ferramenta self-hosted pra **visualizar despesas a partir de notas fiscais eletronicas** (NF-e/NFC-e), com granularidade de **item** (produto a produto), classificacao automatica e orcamento. Nasce publica porque a granularidade que a NF-e carrega e subaproveitada pelas ferramentas prontas.

> **Status:** os seis componentes das specs estao implementados e testados: **parser** (01),
> **classificacao** (02), **app web** com importacao, revisao e taxonomia (03), **orcamento** (04),
> **relatorios com graficos** (05) e **deploy em Docker** (06). Versoes publicadas como imagem
> Docker a cada tag `v*` — a lista esta na pagina do pacote no GitHub (Packages).

## O que e (MVP)

- Movido por **nota fiscal**: os gastos vem dos XMLs, sem lancamento manual.
- **NF-e (55) + NFC-e (65)**; CF-e/SAT marcado como nao suportado (nao quebra o lote).
- Classificacao **por produto** (cascata deterministica: memoria → NCM → bucket; LLM opcional, opt-in).
- **Orcamento** por categoria/mes e **visualizacao** que o usuario monta (gasto por mes/categoria/loja, top produtos, preco no tempo).
- So despesas, so BRL.

Fora do MVP (roadmap): entrada manual, multiusuario, EN, download via SEFAZ, scan de QR, comparativo planejado×real. Ver `specs/` e o report de design original em `docs/historico/`.

## Stack

Python · FastAPI · Jinja2/HTMX · SQLite · Docker. Parsing com `nfelib`. Libs menores ficam a criterio da implementacao.

## Rodando em dev

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python scripts/verify.py   # testes + lint + formato; o mesmo que o CI cobra

# subir o app (http://localhost:8000)
APP_DB_PATH=./data/nfe.db uvicorn nfe_parser.web.app:criar_app_do_ambiente --factory
```

Config **so** por variavel de ambiente — a lista completa, sem valores reais, esta em `.env.example`.
`APP_DB_PATH` e obrigatoria; o resto e opcional.

## Rodando via Docker

```bash
docker compose up -d       # http://localhost:8000
```

Sobe a imagem oficial (`ghcr.io/guilherme-betta/nfe-parser`) com o banco num **volume nomeado**
(`nfe-dados`): reiniciar ou atualizar o container nao perde dados. Para montar a imagem a partir
deste repositorio, `docker compose build` antes. O fuso padrao e `America/Sao_Paulo` (troque com
`TZ` no `.env`): ele decide qual e o "mes corrente" no orcamento.

**Classificacao por LLM (opcional).** Desligada por padrao — a base deterministica (memoria → NCM →
bucket) funciona sem nada. Para ligar com um Ollama rodando no host, crie um `.env` ao lado do
`docker-compose.yml`:

```bash
OLLAMA_URL=http://host.docker.internal:11434
OLLAMA_MODELO=<o modelo que voce baixou no Ollama>
LLM_LIMIAR=<confianca minima entre 0 e 1>
```

As tres juntas, ou o app nao sobe (configuracao pela metade e erro). No Docker Desktop (Windows/Mac)
`host.docker.internal` ja resolve; no Linux, o `extra_hosts` do compose cuida disso. O LLM nunca
roda na importacao: ele e disparado em **Revisar → Sugerir com o LLM**.

**Backup.** O banco inteiro e um arquivo SQLite. Com o app parado:

```bash
docker compose stop
docker run --rm -v nfe_parser_nfe-dados:/dados -v "$PWD":/backup alpine cp /dados/nfe.db /backup/
docker compose start
```

(O nome do volume leva o nome da pasta do projeto na frente; `docker volume ls` mostra o seu.)

## Estrutura

```
specs/                 # o contrato — uma spec por componente (01→06 = ordem de build)
specs/NNN-nome/        #   ...e as stories 001-013, registro de como os nucleos foram feitos
src/nfe_parser/        # pacote da aplicacao (nucleos + web/)
tests/                 # testes + fixtures ANONIMIZADAS
scripts/               # verify.py (portao de commit: testes + lint + formato) e o eval do LLM
steering/              # regras vigentes: stack, convencoes, o que o verify checa
docs/historico/        # fotos antigas: reports de design e o experimento com o modelo local
.github/workflows/     # CI (lint + testes) e a imagem Docker (monta, confere, publica em tag)
```

## Privacidade

Repositorio **publico**: **nunca** commitar nota fiscal real. `.xml`, `.zip`, `.db` e `.env` sao ignorados por padrao; so fixtures **anonimizadas** entram em `tests/fixtures/`.

## Contribuindo

Ver `CONTRIBUTING.md`. As specs em `specs/` sao a fonte da verdade.

## Licenca

GPL-3.0. Ver `LICENSE`.

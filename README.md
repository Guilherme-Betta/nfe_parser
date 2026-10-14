# NF-e Despesas

Ferramenta self-hosted pra **visualizar despesas a partir de notas fiscais eletronicas** (NF-e/NFC-e), com granularidade de **item** (produto a produto), classificacao automatica e orcamento. Nasce publica porque a granularidade que a NF-e carrega e subaproveitada pelas ferramentas prontas.

> ⚠️ **Status: em construcao — ainda sem app pra rodar.** Os dois nucleos estao prontos e testados: o **parser** (spec 01) e a **classificacao** (spec 02), entregues story a story em `specs/001-*` … `specs/013-*`. Falta a camada que vira app: **API/UI web** (spec 03), **orcamento** (04), **visualizacao** (05) e **deploy** (06). Por enquanto e uma biblioteca Python exercitada pela suite de testes.
>
> Ja funciona (como codigo, sem tela): importar `.zip` ou `.xml` de NF-e 55 / NFC-e 65 pro SQLite, com dedup por chave e cancelamento; saida em JSON; identidade de produto; classificacao deterministica (memoria → NCM → bucket) com taxonomia seed editavel; LLM opt-in via Ollama, com harness de eval.

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
pytest
ruff check .
```

Config por variavel de ambiente (ver `.env.example`): caminho do banco e Ollama (opcional) pra classificacao por LLM.

## Rodando via Docker (quando implementado)

`docker compose up` — imagem oficial + volume pro SQLite. A classificacao por LLM e opt-in e alcanca um Ollama no host via `host.docker.internal`. Detalhes em `specs/06_spec_deploy.md`.

## Estrutura

```
specs/                 # o contrato — uma spec por componente (01→06 = ordem de build)
specs/NNN-nome/        #   ...e cada componente fatiado em stories (spec + plano + tarefas)
src/nfe_parser/        # pacote da aplicacao
tests/                 # testes + fixtures ANONIMIZADAS
scripts/               # verify.py (roda a suite), eval do LLM, automacao do workflow
steering/              # regras vigentes: stack, convencoes, o que o verify checa
docs/historico/        # reports de design originais — fotos antigas, nao atualizadas
.github/workflows/     # CI (lint + testes)
```

## Privacidade

Repositorio **publico**: **nunca** commitar nota fiscal real. `.xml`, `.zip`, `.db` e `.env` sao ignorados por padrao; so fixtures **anonimizadas** entram em `tests/fixtures/`.

## Contribuindo

Ver `CONTRIBUTING.md`. As specs em `specs/` sao a fonte da verdade.

## Licenca

GPL-3.0. Ver `LICENSE`.

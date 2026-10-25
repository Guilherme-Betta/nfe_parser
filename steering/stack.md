# Stack — NF-e Despesas (`nfe_parser`)

> O que este projeto usa, e o que ele NAO faz. Consultar antes de escrever spec, teste ou codigo:
> e o que evita dependencia nova e funcionalidade alem do pedido.

## Linguagem e runtime

- **Linguagem:** Python. `pyproject.toml` exige `>=3.11`; o CI roda **3.11**.
- **Nesta maquina (juicey):** Python **3.14.2** — e a unica versao instalada.
  A divergencia com o CI e conhecida e aceita por ora. Codigo que dependa de
  detalhe de 3.12+ e defeito: passa aqui e quebra no CI.
- **Como rodar em dev:**

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
python scripts/verify.py
```

## Dependencias

Nenhum pacote fora desta tabela. Ela e copia fiel do `pyproject.toml`.

| Pacote | Para que | Versao |
| ------ | -------- | ------ |
| `nfelib` | parsing schema-aware dos XMLs de NF-e/NFC-e | livre (nao pinada) |
| `xsdata` | base do `nfelib`; importado direto (`ParserError`, `XmlParser`) em `extrator.py`, `eventos.py` e `cancelamento.py` | livre |
| `fastapi` | HTTP dos componentes 03+ | livre |
| `uvicorn[standard]` | servidor ASGI | livre |
| `jinja2` | templates da UI (componente 03+) | livre |
| `python-multipart` | upload de arquivo na UI | livre |
| `pytest` (dev) | suite de testes | livre |
| `pytest-cov` (dev) | cobertura, sob demanda (`pytest --cov`); o verify nao a usa | livre |
| `ruff` (dev) | lint e formato, `line-length = 100` | livre |
| `httpx` (dev) | client de teste da API | livre |

> `xsdata` ja vinha como dependencia do `nfelib`; esta declarado por conta propria porque o codigo
> o importa direto. ⚠️ Pacote que `src/` importa tem de estar nesta tabela, mesmo que outro pacote
> ja o traga: dependencia transitiva pode sumir numa versao nova sem nenhum aviso antes.

**Da biblioteca padrao**, o que `src/` usa: `sqlite3`, `zipfile`, `hashlib`, `pathlib`,
`datetime`, `decimal`, `dataclasses`, `json`, `csv`, `os`, `re`, `unicodedata`, `urllib.request`,
`tempfile`, `contextlib`, `typing` e `xml.etree.ElementTree`.

**JavaScript de front (componente 03+)** — copiado em `src/nfe_parser/web/static/`, com versao,
licenca e hash SRI na `LEIA-ME.md` de la. ⛔ Sem CDN: o app self-hosted tem de funcionar sem
internet (decisao do Gui de 2026-10-15). Hoje: `htmx` 2.0.4 e `chart.js` 4.4.1.

### O modelo de arquivo do SQLite — tres fatos que confundem quem vem de outro banco

1. **O banco inteiro e UM arquivo.** Tabelas, indices e dados vivem todos dentro dele. Nao ha
   servidor, nao ha "banco" em outro lugar recebendo arquivos. Quando uma funcao recebe um
   `caminho`, esse caminho **e** o banco.
2. **Conexao e o canal aberto com esse arquivo**, e ela carrega configuracao propria. `PRAGMA
   foreign_keys` e o exemplo que morde: vem **DESLIGADO** por padrao, vale **por conexao** e
   **nao fica gravado no arquivo** — quem abrir o banco sem ligar de novo perde a checagem.
3. **Nao confundir com os XMLs.** O app importa arquivos de nota fiscal *para dentro* do banco —
   isso e `importador.py`. No `banco.py` nao entra arquivo nenhum: ele so abre o banco e garante o
   formato das tabelas.

> ⚠️ **O nucleo `parser` (spec 01) usa APENAS `nfelib` + stdlib.** FastAPI,
> Jinja2 e `python-multipart` existem no projeto para os componentes 03 em
> diante. Um diff do nucleo que importe FastAPI esta fora de escopo — e a
> fronteira "sem UI/HTTP" do §4 da spec, violada.

> ⚠️ **Dependencia nova exige decisao do dono do projeto.** Se um diff trouxer
> import de algo que nao esta nesta tabela, ele para ate essa decisao existir.

## Fronteiras — o que este projeto NAO faz

Do `specs/01_spec_parser_modelo.md` §4, o nucleo `parser` **nao** faz:

- classificacao, NCM semantico, qualquer chamada a LLM;
- identidade e normalizacao de produto (tabela `produtos`);
- orcamento e agregacoes analiticas;
- UI, HTTP, upload;
- rede: **nada de SEFAZ**, nada de download, nada de QR code.

(Classificacao e identidade de produto existem no pacote, mas em modulos proprios — spec 02.)

E, no projeto inteiro: so **despesas**, so **BRL**, sem lancamento manual,
sem multiusuario.

> Fronteira explicita e o que impede quem implementa de "ajudar" alem do pedido.

## Privacidade — restricao dura

Repositorio **publico**. Nunca commitar nota fiscal real: sem CPF, CNPJ, nome
ou chave de verdade. `.xml`, `.zip`, `.db` e `.env` sao ignorados pelo git; so
fixtures **anonimizadas** entram em `tests/fixtures/`.

## Layout

```
specs/                 # o contrato — uma spec por componente (01→06 = ordem de build)
specs/NNN-nome/        #   ...e as stories 001-013, registro de como os nucleos foram feitos
src/nfe_parser/        # pacote: parser (spec 01) e classificacao (spec 02)
src/nfe_parser/consultas.py  # leituras da camada web (SQL puro, sem FastAPI)
src/nfe_parser/operacoes.py  # quem abre e fecha cada transacao do app web
src/nfe_parser/gastos.py     # o gasto realizado com rollup — motor das specs 04 e 05
src/nfe_parser/orcamento.py  # teto por categoria e mes (spec 04)
src/nfe_parser/relatorios.py # as analises da visualizacao (spec 05), so leitura
src/nfe_parser/web/    # app FastAPI (spec 03): api.py, paginas.py, templates/, static/
tests/                 # testes + fixtures ANONIMIZADAS; fixtures comuns em conftest.py
scripts/verify.py      # o portao de commit (pytest + ruff check + ruff format)
scripts/rodar_eval.py  # mede o LLM contra um gold rotulado
steering/              # este diretorio: stack, convencoes, verificacao
docs/historico/        # fotos antigas: reports de design e o experimento com o modelo local
.github/workflows/     # CI (ruff check + pytest, Python 3.11)
```

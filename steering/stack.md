# Stack — NF-e Despesas (`nfe_parser`)

> Preenchido no bootstrap. Isto e o que o Claude injeta no contexto quando
> precisa escrever spec ou teste, e o que evita que o modelo local invente
> dependencia nova (item 4 da rubrica de qualidade).

## Linguagem e runtime

- **Linguagem:** Python. `pyproject.toml` exige `>=3.11`; o CI roda **3.11**.
- **Nesta maquina (juicey):** Python **3.14.2** — e a unica versao instalada.
  A divergencia com o CI e conhecida e aceita: o shakedown mede o modelo local,
  nao a matriz de versoes. Codigo que dependa de detalhe de 3.14 e defeito.
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
| `fastapi` | HTTP dos componentes 03+ | livre |
| `uvicorn[standard]` | servidor ASGI | livre |
| `jinja2` | templates da UI (componente 03+) | livre |
| `python-multipart` | upload de arquivo na UI | livre |
| `pytest` (dev) | suite de testes | livre |
| `ruff` (dev) | lint, `line-length = 100` | livre |
| `httpx` (dev) | client de teste da API | livre |

**Da biblioteca padrao**, e o que o nucleo `parser` de fato usa: `sqlite3`,
`zipfile`, `hashlib`, `pathlib`, `datetime`, `decimal`, `dataclasses`, `json`.

### O modelo de arquivo do SQLite — tres fatos que confundem quem vem de outro banco

1. **O banco inteiro e UM arquivo.** Tabelas, indices e dados vivem todos dentro dele. Nao ha
   servidor, nao ha "banco" em outro lugar recebendo arquivos. Quando uma funcao recebe um
   `caminho`, esse caminho **e** o banco.
2. **Conexao e o canal aberto com esse arquivo**, e ela carrega configuracao propria. `PRAGMA
   foreign_keys` e o exemplo que morde: vem **DESLIGADO** por padrao, vale **por conexao** e
   **nao fica gravado no arquivo** — quem abrir o banco sem ligar de novo perde a checagem.
3. **Nao confundir com os XMLs.** O app vai importar arquivos de nota fiscal *para dentro* do
   banco — mas isso e a story 004. No `banco.py` nao entra arquivo nenhum: ele so abre o banco e
   garante o formato das tabelas.

> ⚠️ **O nucleo `parser` (spec 01) usa APENAS `nfelib` + stdlib.** FastAPI,
> Jinja2 e `python-multipart` existem no projeto para os componentes 03 em
> diante. Um diff do nucleo que importe FastAPI esta fora de escopo — e a
> fronteira "sem UI/HTTP" do §4 da spec, violada.

> ⚠️ **Dependencia nova exige decisao humana.** O modelo local nao adiciona
> pacote por conta propria; se um diff trouxer import de algo que nao esta
> nesta tabela, isso reprova no item 4 da rubrica de qualidade da Fase 2.

## Fronteiras — o que este projeto NAO faz

Do `specs/01_spec_parser_modelo.md` §4, o nucleo **nao** faz:

- classificacao, NCM semantico, qualquer chamada a LLM;
- identidade e normalizacao de produto (tabela `produtos`);
- orcamento e agregacoes analiticas;
- UI, HTTP, upload;
- rede: **nada de SEFAZ**, nada de download, nada de QR code.

E, no projeto inteiro: so **despesas**, so **BRL**, sem lancamento manual,
sem multiusuario.

> Fronteira explicita e o que impede o modelo de "ajudar" alem do pedido.

## Privacidade — restricao dura

Repositorio **publico**. Nunca commitar nota fiscal real: sem CPF, CNPJ, nome
ou chave de verdade. `.xml`, `.zip`, `.db` e `.env` sao ignorados pelo git; so
fixtures **anonimizadas** entram em `tests/fixtures/`.

## Layout

```
specs/                 # o contrato — uma spec por componente (01→06 = ordem de build)
src/nfe_parser/        # pacote da aplicacao (hoje: so __init__.py)
tests/                 # testes + fixtures ANONIMIZADAS
scripts/verify.py      # o oraculo
steering/              # este diretorio: stack, convencoes, verificacao
.github/workflows/     # CI (ruff + pytest, Python 3.11)
```

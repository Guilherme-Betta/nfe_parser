# Convencoes — NF-e Despesas (`nfe_parser`)

> Nomes em portugues ou ingles tanto faz; o que importa e que sejam UMA lingua so, consistente com o
> resto do repo. Este arquivo fixa qual.

## Idioma do codigo

- **Nomes (funcoes, variaveis, tabelas, colunas):** **portugues**, sem acento
  (ASCII). E o que o DDL da `specs/01_spec_parser_modelo.md` ja fixou:
  `notas`, `itens`, `importacoes`, `valor_total`, `nota_chave`, `criado_em`.
- **Comentarios e docstrings:** **portugues**.
- **Mensagens de commit:** **portugues**.

> O `CONTRIBUTING.md` diz que codigo e commits "podem misturar PT/EN". Aqui a
> regra e mais apertada de proposito: **portugues, so**. Quem escreve codigo —
> pessoa ou modelo — imita o exemplo mais proximo, e dar duas opcoes produz um
> repo com metade de cada.

## Estilo

- **Linter:** `ruff check`, `line-length = 100` (do `pyproject.toml`).
- **Formatador:** `ruff format`. Os dois rodam dentro do `verify`, entao nao sao
  sugestao: sao portao de commit.
- **Tamanho maximo de funcao:** ~50 linhas.
- **Sem dependencia nova** fora da tabela de `steering/stack.md`.
- **Sem `print` em codigo de biblioteca** — o nucleo devolve dados, quem
  imprime e a borda.
- **Comentario explica o PORQUE e a ARMADILHA**, nunca a historia: qual story,
  quem decidiu e quando moram nas specs e no git. No codigo, a historia envelhece
  sem ninguem perceber e vira frase falsa com cara de verdadeira.

## Padroes especificos deste projeto

Estas sao as regras que, **se nao virarem assercao num teste, quem implementa
viola em silencio**. A Fase 0 pegou exatamente isso: a spec pedia exatidao
decimal, nenhum teste cobriu, a implementacao truncou e passou.

| Regra | Onde vale |
| ----- | --------- |
| Dinheiro = **inteiro em centavos**, nunca `float` | `valor_total`, `valor_linha` |
| Quantidade e valor unitario = **string decimal exata** do XML | `quantidade`, `valor_unitario` (qCom fracionario, vUnCom com muitas casas) |
| Identificadores com zero a esquerda = **TEXT** | `chave`, `emit_cnpj`, `ncm`, `gtin` |
| Datas = **ISO-8601 com offset**, como no XML | `dh_emi`, `cancelado_em`, `criado_em` |
| GTIN ausente ("SEM GTIN") = **NULL**, nao string vazia | `itens.gtin` |
| `xProd` guardado **cru** | `itens.descricao` — normalizar e da classificacao |
| **Nenhum arquivo derruba o lote** | invalido/incompleto/orfao/SAT viram linha no log, nao excecao |
| **O lote e uma transacao** | `importar` commita no fim e desfaz tudo se algo levantar; ninguem abaixo dele commita |
| DDL **idempotente** (`CREATE TABLE IF NOT EXISTS`) | reprocessar o mesmo zip deixa o banco identico |
| Vocabulario fechado = **`StrEnum` em `vocabulario.py`**, nunca string solta no Python | `status`, tipo de XML, `resultado` do log, `origem`, `identidade_origem`. O valor e a string crua (banco, JSON, template nao mudam); SQL literal (`WHERE status = 'ok'`) pode ficar, e `test_vocabulario.py` confere enum × CHECK |

## Privacidade — regra dura, repo publico

**Nunca** commitar nota fiscal real: sem CPF, CNPJ, nome ou chave de verdade.
Fixtures so **anonimizadas**, em `tests/fixtures/`.

> ⚠️ O `verify` **nao verifica isto** — nenhum comando dele sabe distinguir um
> CNPJ real de um fake. E buraco conhecido, registrado em `verificacao.md`, e a
> defesa e o `.gitignore` mais revisao humana.

## Commits

- Um commit por unidade logica, com o `verify` verde.
- A mensagem explica o PORQUE da mudanca, nao so o que mudou.
- Teste novo de comportamento e commitado ANTES (ou junto, mas provado vermelho
  no codigo anterior) da implementacao que o faz passar.

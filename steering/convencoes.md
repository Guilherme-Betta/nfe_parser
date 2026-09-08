# Convencoes — NF-e Despesas (`nfe_parser`)

> Preenchido no bootstrap. Serve ao item 3 da rubrica de qualidade da Fase 2:
> "nomes em portugues ou ingles, mas CONSISTENTES com o resto do repo".
> O kit nao tem opiniao sobre qual — so exige que seja uma so.

## Idioma do codigo

- **Nomes (funcoes, variaveis, tabelas, colunas):** **portugues**, sem acento
  (ASCII). E o que o DDL da `specs/01_spec_parser_modelo.md` ja fixou:
  `notas`, `itens`, `importacoes`, `valor_total`, `nota_chave`, `criado_em`.
- **Comentarios e docstrings:** **portugues**.
- **Mensagens de commit:** **portugues**.

> O `CONTRIBUTING.md` diz que codigo e commits "podem misturar PT/EN". Aqui a
> regra e mais apertada de proposito: **portugues, so**. Misturar e legitimo
> para humanos, mas o modelo local escolhe pelo exemplo mais proximo — dar
> duas opcoes produz um repo com metade de cada.

## Estilo

- **Linter:** `ruff`, `line-length = 100` (do `pyproject.toml`). Roda dentro do
  `verify`, entao nao e sugestao: e portao.
- **Tamanho maximo de funcao:** ~50 linhas (item 2 da rubrica de qualidade).
- **Sem dependencia nova** fora da tabela de `steering/stack.md`.
- **Sem `print` em codigo de biblioteca** — o nucleo devolve dados, quem
  imprime e a borda.

## Padroes especificos deste projeto

Estas sao as regras que, **se nao virarem assercao num teste, o modelo viola em
silencio**. A Fase 0 pegou exatamente isso: a spec pedia exatidao decimal,
nenhum teste cobriu, o modelo truncou e passou.

| Regra | Onde vale |
| ----- | --------- |
| Dinheiro = **inteiro em centavos**, nunca `float` | `valor_total`, `valor_linha` |
| Quantidade e valor unitario = **string decimal exata** do XML | `quantidade`, `valor_unitario` (qCom fracionario, vUnCom com muitas casas) |
| Identificadores com zero a esquerda = **TEXT** | `chave`, `emit_cnpj`, `ncm`, `gtin` |
| Datas = **ISO-8601 com offset**, como no XML | `dh_emi`, `cancelado_em`, `criado_em` |
| GTIN ausente ("SEM GTIN") = **NULL**, nao string vazia | `itens.gtin` |
| `xProd` guardado **cru** | `itens.descricao` — normalizar e da classificacao |
| **Nenhum arquivo derruba o lote** | invalido/orfao/SAT viram linha no log, nao excecao |
| DDL **idempotente** (`CREATE TABLE IF NOT EXISTS`) | reprocessar o mesmo zip deixa o banco identico |

## Privacidade — regra dura, repo publico

**Nunca** commitar nota fiscal real: sem CPF, CNPJ, nome ou chave de verdade.
Fixtures so **anonimizadas**, em `tests/fixtures/`.

> ⚠️ O `verify` **nao verifica isto** — nenhum comando dele sabe distinguir um
> CNPJ real de um fake. E buraco conhecido, registrado em `verificacao.md`, e a
> defesa e o `.gitignore` mais revisao humana do passo 4 do loop.

## Commits

- Um commit por unidade logica.
- Os commits do modelo local saem assinados como `Aider (qwen2.5-coder:14b)` —
  isso e proposital e obrigatorio (ver `bootstrap.md`, portao 4).
- ⚠️ Neste clone, `git config user.name` **e o Aider**. Um commit feito por voce
  ou pelo Claude aqui sai assinado como o modelo, e ai a autoria fica errada no
  histórico. Para commitar como humano, sobrescreva na hora:

```powershell
git -c user.name="Guilherme Betta" -c user.email="gbetta.guilherme@gmail.com" commit -m "..."
```

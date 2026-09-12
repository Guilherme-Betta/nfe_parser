# Plan — 002 · Extrair uma NF-e 55 de 1 item

> **Sprint backlog: a spec fatiada em tarefas que cabem no modelo local.**
> Uma linha = uma invocacao do Aider.

## Regras de fatiamento (nao sao sugestoes)

| # | Regra | Vem de |
| - | ----- | ------ |
| 1 | Cada tarefa cabe em **~300 linhas** de codigo relevante | orcamento de 8192 tokens |
| 2 | **Um pedido, um defeito** | Fase 0: dois defeitos no mesmo pedido -> blocos SEARCH/REPLACE sobrepostos -> arquivo corrompido |
| 3 | Cada tarefa cabe em **3 tentativas** do `--auto-test` | e o teto do Aider (`Only 3 reflections allowed`) |
| 4 | **`/clear` entre tarefas** | 3 turnos ja estouram os 8k, em silencio |
| 5 | **>6k tokens no turno 1 condena o laco** | story 001: o turno 1 saiu a 7,0k e as 3 reflexoes rodaram truncadas, em silencio |

> Estourar a regra 3 nao e sinal de repetir o pedido — e sinal de que a tarefa
> era grande demais. Quebre e refaca.

## Tarefas

| # | Tarefa | Arquivos | `edit-format` | Status |
| - | ------ | -------- | ------------- | ------ |
| 1 | `para_centavos(texto) -> int`: exato ao centavo, **rejeita** mais de 2 casas em vez de truncar | `src/nfe_parser/extrator.py` (novo) | `diff` | ⬜ |
| 2 | `extrair_nota(xml_texto) -> dict`: le o `nfeProc` com `nfelib` e devolve `{"nota": ..., "itens": [...]}` | `src/nfe_parser/extrator.py` | `diff` | ⬜ |

**Status:** ⬜ nao iniciada · 🔄 no modelo local · 👀 aguardando revisao · ✅ aceita

### ⭐ Por que DUAS tarefas aqui, se a story 001 foi uma so

A story 001 cabia em uma invocacao e mesmo assim mandou **7,0k no turno 1**, contra um `num_ctx` de
8192 — e as tres reflexoes seguintes rodaram com contexto **truncado em silencio** (Achado B do
`offload-log.md`). Esta story tem mais contexto obrigatorio que aquela: a spec traz a tabela da
API do `nfelib` (§4), que nao da para cortar sem devolver o modelo a adivinhacao.

Entao o fatiamento aqui nao e zelo, e aritmetica de orcamento:

- **Tarefa 1 nao precisa do `nfelib` em lugar nenhum.** E `Decimal` e nada mais. Da para invocar
  com `--read` so no §5 da spec, e o turno 1 sai pequeno.
- **Tarefa 2 precisa do §4 inteiro**, mas ja encontra `para_centavos` pronto no arquivo — nao
  precisa raciocinar sobre dinheiro, so chamar.

E a regra 2 (um pedido, um defeito) fica satisfeita de quebra: "converter dinheiro" e "ler XML"
sao dois objetivos, nao um.

### Como invocar

O modelo **le** os testes e nao os edita (`--read`). Isso nao e estilo: se ele puder editar o
teste, ele edita o teste para faze-lo passar — e o caminho mais curto para o objetivo dado.

```powershell
# de dentro de nfe_parser-shakedown, com a .venv ATIVADA

# --- tarefa 1 -------------------------------------------------------------
aider --model ollama_chat/qwen2.5-coder:14b `
      --read tests/test_extrator.py `
      --read specs/002-extrair-nfe-55/spec.md `
      --file src/nfe_parser/extrator.py `
      --yes-always `
      --message "..."

# /clear entre as duas   <- regra 4

# --- tarefa 2 -------------------------------------------------------------
aider --model ollama_chat/qwen2.5-coder:14b `
      --read tests/test_extrator.py `
      --read specs/002-extrair-nfe-55/spec.md `
      --read tests/fixtures/nfe_55_1item.xml `
      --file src/nfe_parser/extrator.py `
      --yes-always `
      --message "..."
```

> ⚠️ A `.venv` **precisa** estar ativada. O `verify` usa `sys.executable`, entao ele herda o
> interpretador de quem o chamou — e quem o chama e o Aider.

> ⚠️ **Medir o turno 1.** O Aider imprime os tokens enviados. Se a tarefa 2 sair acima de **6k**,
> pare e quebre de novo (por exemplo: `extrair_nota` so com o bloco `"nota"`, e os `"itens"` numa
> terceira invocacao). Rodar assim mesmo desperdica as 3 reflexoes em silencio.

### Coluna `edit-format` — como preencher

| Situacao | Use |
| -------- | --- |
| escrever codigo novo; modificar no lugar; arquivo acima de ~120 linhas | **`diff`** (padrao) |
| **reorganizar** (mover/reordenar/renomear) em arquivo de ate ~120 linhas | **`whole`**, via `--edit-format whole` |
| mudanca **so de espaco em branco** | ⛔ nao delegue — `ruff format` / `ruff check --fix` |
| qualquer caso | **nunca `udiff`** |

## ⛔ Antes do primeiro `aider`, sempre

```powershell
git rev-parse --abbrev-ref HEAD    # scrum, nunca main
git status --porcelain             # vazio
python scripts/verify.py           # verde
```

## ⛔ No passo 4, o lint e com `--no-cache`

```powershell
ruff check --fix --no-cache .
```

Dois motivos, os dois medidos e os dois no `steering/verificacao.md`:

1. O `ruff` classifica import conforme os arquivos que existem no disco **naquele momento**, e o
   cache dele nao invalida quando um modulo novo aparece. Como o passo 2 commita os testes **antes**
   da implementacao, esse descompasso e estrutural no kit.
2. O CI roda **Linux** e a juicey e **Windows**. Ha regra que so dispara la (`EXE001` le o bit de
   execucao, que no Windows nao existe). **Verde local nao prova CI verde** — confira o run.

## Rastro (invariante 3: `git log` e a fonte da verdade)

```bash
git log --author="Aider"  --oneline    # o que o modelo local escreveu
git log --author="Betta"  --oneline    # o que saiu do par com o Claude
```

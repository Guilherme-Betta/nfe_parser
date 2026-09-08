# Plan — 001 · Esquema do banco

> **Sprint backlog: a spec fatiada em tarefas que cabem no modelo local.**
> Uma linha = uma invocacao do Aider.

## Regras de fatiamento (nao sao sugestoes)

| # | Regra | Vem de |
| - | ----- | ------ |
| 1 | Cada tarefa cabe em **~300 linhas** de codigo relevante | orcamento de 8192 tokens |
| 2 | **Um pedido, um defeito** | Fase 0: dois defeitos no mesmo pedido -> blocos SEARCH/REPLACE sobrepostos -> arquivo corrompido |
| 3 | Cada tarefa cabe em **3 tentativas** do `--auto-test` | e o teto do Aider (`Only 3 reflections allowed`) |
| 4 | **`/clear` entre tarefas** | 3 turnos ja estouram os 8k, em silencio |

> Estourar a regra 3 nao e sinal de repetir o pedido — e sinal de que a tarefa
> era grande demais. Quebre e refaca.

## Tarefas

| # | Tarefa | Arquivos | `edit-format` | Status |
| - | ------ | -------- | ------------- | ------ |
| 1 | Criar `banco.py` com `abrir_banco` e `criar_esquema`, aplicando o DDL do §2 da spec 01 e ligando `PRAGMA foreign_keys` | `src/nfe_parser/banco.py` (novo) | `diff` | ⬜ |

**Status:** ⬜ nao iniciada · 🔄 no modelo local · 👀 aguardando revisao · ✅ aceita

**Uma tarefa so, de proposito.** A story inteira cabe em ~70 linhas e num unico
arquivo novo. Fatiar mais gastaria mais orcamento em context switch do que
economizaria em complexidade — e a regra 2 (um pedido, um defeito) ja esta
satisfeita: o pedido tem um objetivo so.

### Como invocar

O modelo **le** os testes e nao os edita (`--read`). Isso nao e estilo: se ele
puder editar o teste, ele edita o teste para faze-lo passar — e o caminho mais
curto para o objetivo dado.

```powershell
# de dentro de nfe_parser-shakedown, com a .venv ATIVADA
aider --model ollama_chat/qwen2.5-coder:14b `
      --read tests/test_banco.py `
      --read specs/001-esquema-do-banco/spec.md `
      --read specs/01_spec_parser_modelo.md `
      --file src/nfe_parser/banco.py `
      --yes-always `
      --message "..."
```

> ⚠️ A `.venv` **precisa** estar ativada. O `verify` usa `sys.executable`, entao
> ele herda o interpretador de quem o chamou — e quem o chama e o Aider.

### Coluna `edit-format` — como preencher

| Situacao | Use |
| -------- | --- |
| escrever codigo novo; modificar no lugar; arquivo acima de ~120 linhas | **`diff`** (padrao) |
| **reorganizar** (mover/reordenar/renomear) em arquivo de ate ~120 linhas | **`whole`**, via `--edit-format whole` |
| qualquer caso | **nunca `udiff`** |

Medido na Fase 0 (secao 9), nos dois pedidos de reorganizacao que falharam:
`diff` 0/2, `udiff` 0/2, **`whole` 2/2 no primeiro turno**. E `whole` saiu mais
BARATO: 1 turno com 2,3k tokens, contra 4 turnos e ~19,4k do `diff` sem convergir.

`udiff` e proibido porque falha **em silencio** — nao gera erro de match, entao
o Aider acha que aplicou e nada mudou.

## Rastro (invariante 3: `git log` e a fonte da verdade)

Nada de arquivo `.status` paralelo — ele diverge se a maquina dormir no meio do
loop. Esta tabela e conveniencia de leitura; a verdade esta no historico:

```bash
git log --author="Aider"  --oneline    # o que o modelo local escreveu
git log --author="Betta"  --oneline    # o que saiu do par com o Claude
```

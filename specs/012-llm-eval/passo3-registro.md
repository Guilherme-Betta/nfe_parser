# Passo 3 — registro — 012-llm-eval

> ⚠️ **Registro reconstruído à mão no P4.** O computador caiu no meio da tarefa 3 da primeira
> rodada, e o `rodar_passo3.py` só grava o registro **no fim**: as tarefas 1 e 2 não chegaram ao
> `registro.json`. Os números delas vêm da saída de terminal da primeira rodada, guardada antes de
> retomar. As tarefas 3 e 4 são o registro automático das rodadas seguintes.

Rodado em 2026-09-28 por `scripts/rodar_passo3.py`, em **três execuções**:

| Execução | Manifesto | Formato | Tarefas |
| -------- | --------- | ------- | ------- |
| 1 | `tarefas.json` | `whole` | 1 ✅, 2 ✅, 3 ⚡ *interrompida pelo crash, sem commit* |
| 2 | `tarefas.json --a-partir-de 3` | `whole` | 3 ❌ — ver abaixo |
| 3 | `tarefas-so-3.json` | **`diff`** | 3 ✅ |
| 4 | `tarefas.json --a-partir-de 4` | `whole` | 4 ✅, e a suíte completa verde |

- **Tarefas verdes:** 4 de 4
- **Invocações do Aider:** 6 *(1 + 1 + 3 + 1; uma delas cortada pelo crash)*
- **Commits do modelo local:** 7
- **Tempo de máquina medido:** ~4,2 min *(sem o trecho da invocação cortada, que não tem registro)*
- **CONTEXT do Ollama:** 8192

| # | Tarefa | Verde? | Invocações | Tempo | `sent` real / previsto | Commits | Quem resolveu |
| - | ------ | ------ | ---------- | ----- | ---------------------- | ------- | ------------- |
| 1 | `llm.py` | ✅ | 1 | 81,8s | 3,5k / 3,39k | 2 | 🤖 |
| 2 | `classificacao_llm.py` | ✅ | 1 | 30,0s | 3,6k / 3,55k | 2 | 🤖 |
| 3 | a varredura passa o `llm` | ✅ | 3 | 80,5s + ⚡ | whole: 3,7k → **17k**; diff: 5,5k / 3,54k | 1 | 🤖 *(o código veio certo nas duas rodadas completas; a re-especificação trocou o formato, ⛔ não o raciocínio)* |
| 4 | `eval_llm.py` | ✅ | 1 | 57,4s | 3,2k / 3,11k | 2 | 🤖 |

## 🔴 O que parou a tarefa 3 na execução 2

O modelo devolveu o arquivo **certo**: import trocado, parâmetro novo, chamada trocada e as duas
docstrings publicadas de volta palavra por palavra. ⛔ O Aider não aplicou.

Com `whole`, a resposta traz o arquivo inteiro, e a docstring publicada da varredura cita cinco
arquivos do projeto pelo nome (`categorizacao.py`, `persistencia.py`, `produtos.py`, `seed.py`,
`taxonomia.py`). O Aider leu os nomes **na resposta**, adicionou os cinco à conversa com
`--yes-always`, e fez uma segunda chamada com **17k tokens** — o dobro da janela. A edição da
primeira resposta foi descartada.

⭐ **É o Achado AD com o gatilho no próprio alvo.** A 013 não o viu porque criou a varredura
**vazia**; as docstrings só entraram no P4 dela.

📋 **Remédio:** a execução 3 rodou só a tarefa 3 com `--edit-format diff` — o modelo devolve apenas os
blocos que mudam, e a docstring não volta. A mensagem perdeu a frase "devolva o arquivo INTEIRO";
o resto ficou igual. Verde na primeira, 3 linhas de diff.

⚠️ **`sent` com `diff` foi 5,5k contra 3,54k previstos** — o *system prompt* do formato `diff` é
~2k maior que o do `whole`, e a fórmula do kit foi medida só com `whole`.

---

## Commits brutos do modelo local

Registrados aqui porque a transferência para o repo oficial usa histórico curado.

**Tarefa 1 — `llm.py`**

- `e414761 feat: adicionar módulo de parser de NFe com LLM`
- `8b796ec feat: Adiciona arquivo src/nfe_parser/llm.py com funções para classificação de produtos de notas fiscais.`

**Tarefa 2 — `classificacao_llm.py`**

- `1f3d55d feat: adicionar classificação LLM para NFE`
- `9d157e5 feat: Implementa função classificar_produto_com_llm para classificação de produtos com LLM`

**Tarefa 3 — a varredura passa o `llm` adiante**

- `44fabea refactor: Atualiza import e parâmetro na função classificar_produtos_pendentes`

**Tarefa 4 — `eval_llm.py`**

- `fa524a6 feat: adicionar script de avaliação do LLM para parser de NFe`
- `64c56b1 feat: Adiciona arquivo eval_llm.py com funções carregar_gold, prever e avaliar`

⚠️ O commit **humano** `341d122` (a re-especificação da tarefa 3) fica entre os commits do modelo.

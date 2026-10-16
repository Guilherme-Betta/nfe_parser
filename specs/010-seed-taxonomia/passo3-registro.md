# Passo 3 — registro automatico — 010-seed-taxonomia

Rodado em 2026-09-15 14:55 por `scripts/rodar_passo3.py`.

- **Tarefas verdes:** 2 de 2
- **Invocacoes do Aider:** 2
- **Commits do modelo local:** 3
- **Tempo total no passo 3:** 1.3 min
- **CONTEXT do Ollama:** 8192

| # | Tarefa | Verde? | Invocacoes | Tempo | Commits | Quem resolveu |
| - | ------ | ------ | ---------- | ----- | ------- | ------------- |
| 1 | carregar_categorias: upsert por slug em duas passadas, e o invariante do bucket | ✅ | 1 | 43.7s | 2 | 🤖 |
| 2 | carregar_ncm_ancora: upsert por prefixo, resolvendo o slug e recusando largura impossivel | ✅ | 1 | 32.4s | 1 | 🤖 |

> ⚠️ A coluna **Quem resolveu** NAO e preenchivel por script. Marque a mao:
> 🤖 modelo local · 👤 Claude ditou o codigo · 🤝 misto. Sem ela, "N/N tarefas verdes" e "N/N resolvidas pelo modelo local" viram a mesma linha — e na medicao 5 nao eram (Achado M).

---

## Commits brutos do modelo local

Registrados aqui porque a transferencia para o repo oficial usa historico curado.
Esta e a evidencia do que o modelo local produziu, tarefa a tarefa — o `git log`
do repo oficial nao a tem mais, e o clone do shakedown e descartavel.

**Tarefa 1 — carregar_categorias: upsert por slug em duas passadas, e o invariante do bucket**

- `34662d6 feat: Adiciona função `carregar_categorias` para inserir e configurar categorias no banco de dados.`
- `b1c35d4 feat: adicionar script de seed para parser de NFe`

**Tarefa 2 — carregar_ncm_ancora: upsert por prefixo, resolvendo o slug e recusando largura impossivel**

- `bea2ed9 feat: Adiciona função `carregar_ncm_ancora` para processar ancas NCM`



---

## Como esta coluna foi preenchida

📋 **2/2 🤖 — o codigo das duas funcoes e do modelo local, integralmente.** ⛔ Nenhuma
re-especificacao, nenhuma reversao, e nenhuma linha ditada por Claude no passo 3. Uma invocacao por
tarefa, as duas verdes de primeira.

⚠️ **3 commits para 2 invocacoes** — a tarefa 1 saiu com dois. Commit do modelo nao e invocacao
(Achado do P3 da 009, que se repetiu aqui).

### ⭐ O risco do `whole` nao se materializou

Com `--edit-format whole` o modelo reescreve o arquivo INTEIRO a cada tarefa, entao a tarefa 2 podia
ter devolvido `seed.py` sem a `carregar_categorias`. Nao aconteceu: a mensagem abria dizendo, com
todas as letras, que a funcao existente nao se altera e tem de vir inteira na resposta.

### 🔴 O `Tokens: sent`, e a calibracao do plan errou 4% — para MENOS

| Tarefa | alvo | teste | mensagem | soma (B) | previsto | **medido** |
| ------ | ---- | ----- | -------- | -------- | -------- | ---------- |
| 1 | 0 | 3.890 | 3.922 | 7.812 | 7,76k | **8,1k** |
| 2 | **1.216** | 3.093 | 3.489 | 7.798 | 7,75k | **8,1k** |

⭐ **O coeficiente por byte (1 token por 3,7 B) se manteve**; o que mudou foi o piso fixo:

| | constante implicita |
| - | ------------------- |
| story 009 (3 pontos) | **~5,65k** |
| story 010 (2 pontos) | **~5,99k** |

⚠️ **Dentro de uma story a constante e estavel a ponto de os dois pontos darem 5.989 e 5.992** — tres
tokens de diferenca. ⛔ **Entre stories ela andou 340 tokens em um dia.** Entao parte do que o kit
chama de "overhead fixo" nao e fixo: cresce com o repositorio, mesmo com `--map-tokens 0`.

⛔ **A causa nao esta isolada** e nao se deve fingir que esta. ⭐ O que tem lastro: a formula do kit
(3,0k + bytes/4) teria previsto **4,95k** contra os 8,1k reais; a calibrada previu **7,76k**. Errar
4% e outra coisa que errar 39%.

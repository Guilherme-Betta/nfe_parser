# Passo 3 — registro automatico — 008-identidade-produto

Rodado em 2026-09-15 10:28 por `scripts/rodar_passo3.py`.

- **Tarefas verdes:** 3 de 3
- **Invocacoes do Aider:** 3
- **Commits do modelo local:** 4
- **Tempo total no passo 3:** 1.5 min
- **CONTEXT do Ollama:** 8192

| # | Tarefa | Verde? | Invocacoes | Tempo | Commits | Quem resolveu |
| - | ------ | ------ | ---------- | ----- | ------- | ------------- |
| 1 | normalizar_descricao: minuscula, sem acento, pontuacao vira espaco, espacos colapsados | ✅ | 1 | 29.0s | 2 | 🤖 |
| 2 | resolver_produto_por_gtin: casa ou cria em produtos com identidade_origem 'gtin' | ✅ | 1 | 28.7s | 1 | 🤖 |
| 3 | resolver_produto_por_texto: casa ou cria por descricao_normalizada + emit_cnpj | ✅ | 1 | 31.5s | 1 | 🤖 |

> ⚠️ A coluna **Quem resolveu** NAO e preenchivel por script. Marque a mao:
> 🤖 modelo local · 👤 Claude ditou o codigo · 🤝 misto. Sem ela, "N/N tarefas verdes" e "N/N resolvidas pelo modelo local" viram a mesma linha — e na medicao 5 nao eram (Achado M).

---

## Commits brutos do modelo local

Registrados aqui porque a transferencia para o repo oficial usa historico curado.
Esta e a evidencia do que o modelo local produziu, tarefa a tarefa — o `git log`
do repo oficial nao a tem mais, e o clone do shakedown e descartavel.

**Tarefa 1 — normalizar_descricao: minuscula, sem acento, pontuacao vira espaco, espacos colapsados**

- `582ad8e feat: Adiciona função `normalizar_descricao` em `produtos.py``
- `87ac52b feat: adicionar módulo para parsing de produtos`

**Tarefa 2 — resolver_produto_por_gtin: casa ou cria em produtos com identidade_origem 'gtin'**

- `48e4a45 feat: Adiciona função resolver_produto_por_gtin ao produtos.py`

**Tarefa 3 — resolver_produto_por_texto: casa ou cria por descricao_normalizada + emit_cnpj**

- `3513010 feat: Adiciona função resolver_produto_por_texto ao produtos.py`


---

## Preenchido a mao no passo 4

**Quem resolveu: 🤖 modelo local nas tres.** Uma invocacao por tarefa, sem
re-especificacao, sem reversao. O passo 4 nao mudou logica nenhuma: entraram docstrings, e uma
guarda de precondicao que os testes congelados nao cobriam (ver o commit do passo 4).

⚠ A tarefa 1 tem DOIS commits do modelo local e mesmo assim uma invocacao so: ele criou o
modulo num commit e a funcao no outro, dentro da mesma sessao do Aider. ⭐ Nao e o Achado R --
nao houve copia duplicada, e a revisao do passo 4 leu o arquivo inteiro e nao achou linha morta.

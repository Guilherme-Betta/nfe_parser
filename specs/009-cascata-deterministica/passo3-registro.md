# Passo 3 — registro automatico — 009-cascata-deterministica

Rodado em 2026-09-15 11:04 por `scripts/rodar_passo3.py`.

- **Tarefas verdes:** 3 de 3
- **Invocacoes do Aider:** 5
- **Commits do modelo local:** 4
- **Tempo total no passo 3:** 2.1 min
- **CONTEXT do Ollama:** 8192

| # | Tarefa | Verde? | Invocacoes | Tempo | Commits | Quem resolveu |
| - | ------ | ------ | ---------- | ----- | ------- | ------------- |
| 1 | buscar_categoria_por_ncm: prefixo mais longo em ncm_ancora (8, 4 ou 2 digitos) | ✅ | 3 | 64.5s | 2 | 🤖 |
| 2 | classificar_produto: a cascata memoria > NCM > bucket, e grava o resultado | ✅ | 1 | 33.5s | 1 | 🤖 |
| 3 | definir_categoria_manual: a decisao humana, que a cascata nunca sobrescreve | ✅ | 1 | 28.6s | 1 | 🤖 |

> ⚠️ A coluna **Quem resolveu** NAO e preenchivel por script. Marque a mao:
> 🤖 modelo local · 👤 Claude ditou o codigo · 🤝 misto. Sem ela, "N/N tarefas verdes" e "N/N resolvidas pelo modelo local" viram a mesma linha — e na medicao 5 nao eram (Achado M).

---

## Commits brutos do modelo local

Registrados aqui porque a transferencia para o repo oficial usa historico curado.
Esta e a evidencia do que o modelo local produziu, tarefa a tarefa — o `git log`
do repo oficial nao a tem mais, e o clone do shakedown e descartavel.

**Tarefa 1 — buscar_categoria_por_ncm: prefixo mais longo em ncm_ancora (8, 4 ou 2 digitos)**

- `75d7466 feat: Adiciona função buscar_categoria_por_ncm em categorizacao.py`
- `f4b2fea feat: adiciona módulo de categorização para NFE`

**Tarefa 2 — classificar_produto: a cascata memoria > NCM > bucket, e grava o resultado**

- `3077122 feat: adiciona funções `_categoria_do_bucket` e `classificar_produto` para classificação de produtos`

**Tarefa 3 — definir_categoria_manual: a decisao humana, que a cascata nunca sobrescreve**

- `1b46268 feat: adiciona função para definir categoria manual de produto`


---

## Como esta coluna foi preenchida, e a ressalva da tarefa 1

📋 **3/3 🤖 — o codigo das tres funcoes e do modelo local, integralmente.** ⛔ Nenhuma
re-especificacao de conteudo, nenhuma reversao, e nenhuma linha ditada por Claude no passo 3.

⚠️ **Mas a tarefa 1 gastou 3 invocacoes, e a ressalva importa.** As duas primeiras falharam por
**formato, nao por logica**: com `edit-format: diff`, o prompt passou de 8192 tokens, o Ollama
truncou, e o modelo perdeu as instrucoes de bloco SEARCH/REPLACE. Nas duas ele **acertou o algoritmo
inteiro** — o `ORDER BY LENGTH(prefixo) DESC` e a guarda de NCM vazio nos lugares certos — e o Aider
nao teve o que aplicar.

⭐ **Por isso as tres contam como 🤖.** O que mudou entre a falha e o verde foi o **kit** (a opcao
`--edit-format whole`) e o **tamanho** dos insumos, ⛔ nao a especificacao da tarefa: nenhuma REGRA
saiu da mensagem, e nenhuma assercao saiu do oraculo.

⚠️ **O `Tokens: sent` merece ficar registrado, porque contraria a leitura simples:**

| Tarefa | formato | sent | resultado |
| ------ | ------- | ---- | --------- |
| 1 | `diff` | **9,6k** | ⛔ bloco malformado |
| 1 | `diff`, insumos 1.834 B menores | **9,0k** | ⛔ bloco malformado |
| 1 | **`whole`** | **7,2k** | ✅ |
| 2 | `whole` | **8,6k** | ✅ |
| 3 | `whole` | **8,4k** | ✅ |

🔴 **As tarefas 2 e 3 passaram de 8192 e mesmo assim converteram.** ⛔ Entao "passou do num_ctx"
**nao** e, sozinho, explicacao suficiente para a falha — a contagem do Aider e estimativa com
tokenizador generico, nao com o do Qwen. ⭐ O que tem lastro e mais simples: **o `whole` custa ~1,8k
a menos que o `diff` na mesma tarefa**, e foi essa margem que separou o vermelho do verde.

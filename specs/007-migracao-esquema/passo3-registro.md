# Passo 3 — registro automatico — 007-migracao-esquema

Rodado em 2026-09-15 10:01 por `scripts/rodar_passo3.py`.

- **Tarefas verdes:** 0 de 1
- **Invocacoes do Aider:** 1
- **Commits do modelo local:** 4
- **Tempo total no passo 3:** 1.1 min
- **CONTEXT do Ollama:** 8192

| # | Tarefa | Verde? | Invocacoes | Tempo | Commits | Quem resolveu |
| - | ------ | ------ | ---------- | ----- | ------- | ------------- |
| 1 | executor de migracoes por PRAGMA user_version, atomico por migracao, e o fio em abrir_banco | ❌ | 1 | 63.1s | 4 | ⏳ *preencher a mao — Achado M* |

> ⚠️ A coluna **Quem resolveu** NAO e preenchivel por script. Marque a mao:
> 🤖 modelo local · 👤 Claude ditou o codigo · 🤝 misto. Sem ela, "N/N tarefas verdes" e "N/N resolvidas pelo modelo local" viram a mesma linha — e na medicao 5 nao eram (Achado M).

---

## Commits brutos do modelo local

Registrados aqui porque a transferencia para o repo oficial usa historico curado.
Esta e a evidencia do que o modelo local produziu, tarefa a tarefa — o `git log`
do repo oficial nao a tem mais, e o clone do shakedown e descartavel.

**Tarefa 1 — executor de migracoes por PRAGMA user_version, atomico por migracao, e o fio em abrir_banco**

- `1d3f0a2 fix: Corrigir bloco SEARCH/REPLACE em src/nfe_parser/banco.py`
- `f4eda72 fix: corrigir chamada de `aplicar_migracoes` no `abrir_banco``
- `58c2924 feat: Adiciona suporte a migrações de banco de dados no módulo `nfe_parser``
- `abf76ae feat: adicionar script de migração para NFE`


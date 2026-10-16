# Passo 3 — registro automatico — 011-edicao-taxonomia

Rodado em 2026-09-15 20:56 por `scripts/rodar_passo3.py`.

- **Tarefas verdes:** 3 de 3
- **Invocacoes do Aider:** 4
- **Commits do modelo local:** 4
- **Tempo total no passo 3:** 2.8 min
- **CONTEXT do Ollama:** 8192

| # | Tarefa | Verde? | Invocacoes | Tempo | Commits | Quem resolveu |
| - | ------ | ------ | ---------- | ----- | ------- | ------------- |
| 1 | apagar_categoria: produtos ao bucket com origem zerada, ancoras fora, lapide gravada | ✅ | 2 | 92.5s | 2 | 🤖 |
| 2 | mover_categoria: o id sobrevive, None sobe para nivel 1, e a subida recusa ciclo | ✅ | 1 | 41.7s | 1 | 🤖 |
| 3 | renomear_categoria: muda o nome e NUNCA o slug; nome vazio levanta | ✅ | 1 | 33.8s | 1 | 🤖 |

> ⚠️ A coluna **Quem resolveu** NAO e preenchivel por script. Marque a mao:
> 🤖 modelo local · 👤 Claude ditou o codigo · 🤝 misto. Sem ela, "N/N tarefas verdes" e "N/N resolvidas pelo modelo local" viram a mesma linha — e na medicao 5 nao eram (Achado M).

---

## ⚠️ Esta NAO foi a primeira rodada — houve uma inteira descartada

A primeira invocacao da tarefa 1 morreu com `The LLM did not conform to the edit
format`, depois das 3 reflexoes do Aider, sem nenhum commit. O log mostrava
`Tokens: 11k sent` numa janela de 8192: o Ollama cortava o prompt, e o que mora
no comeco dele e a instrucao de formato — entao o modelo inventava a formatacao,
devolvendo o nome do arquivo DENTRO de uma cerca e o codigo em outra.

⭐ **O codigo que ele escreveu naquela tentativa ja estava certo.** O que quebrou
foi o tamanho do prompt, e a causa esta no commit `5be8f82`: nomear um arquivo do
repositorio na mensagem faz o Aider carrega-lo inteiro no contexto.

📋 **Custo real da story, entao:** 4 invocacoes uteis + 4 invocacoes perdidas
(1 tentativa + 3 reflexoes), e ~67s de maquina jogados fora.

---

## Commits brutos do modelo local

Registrados aqui porque a transferencia para o repo oficial usa historico curado.
Esta e a evidencia do que o modelo local produziu, tarefa a tarefa — o `git log`
do repo oficial nao a tem mais, e o clone do shakedown e descartavel.

**Tarefa 1 — apagar_categoria: produtos ao bucket com origem zerada, ancoras fora, lapide gravada**

- `485226d feat: Adiciona função `apagar_categoria` em `src/nfe_parser/taxonomia.py``
- `d8197a8 feat: adicionar módulo de parsing de taxonomia para NFe`

**Tarefa 2 — mover_categoria: o id sobrevive, None sobe para nivel 1, e a subida recusa ciclo**

- `debbc3e feat: adiciona função mover_categoria para manipulação de categorias`

**Tarefa 3 — renomear_categoria: muda o nome e NUNCA o slug; nome vazio levanta**

- `1b98cf9 feat: adiciona função renomear_categoria em taxonomia.py`


# Passo 3 — registro automatico — 007-migracao-esquema

Rodado em 2026-09-15 10:05 por `scripts/rodar_passo3.py`.

- **Tarefas verdes:** 3 de 3
- **Invocacoes do Aider:** 4
- **Commits do modelo local:** 9
- **Tempo total no passo 3:** 3.4 min
- **CONTEXT do Ollama:** 8192

| # | Tarefa | Verde? | Invocacoes | Tempo | Commits | Quem resolveu |
| - | ------ | ------ | ---------- | ----- | ------- | ------------- |
| 1 | executor de migracoes por PRAGMA user_version, atomico por migracao, e o fio em abrir_banco | ✅ | 2 | 88.4s | 5 | 🤝 **misto** — ver nota 1 |
| 2 | migracao v1: as 5 tabelas da spec 02 e os 2 indices unicos parciais | ✅ | 1 | 59.5s | 2 | 🤖 **modelo local**, de primeira — ver nota 2 |
| 3 | migracao v2: ALTER TABLE itens ADD COLUMN produto_id, indice, e o banco legado | ✅ | 1 | 55.6s | 2 | 🤖 **modelo local**, de primeira — ver nota 2 |

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
- `27ae426 fix: corrige retorno em `aplicar_migracoes` e adiciona import e chamada em `abrir_banco``

**Tarefa 2 — migracao v1: as 5 tabelas da spec 02 e os 2 indices unicos parciais**

- `756fe93 fix: corrige referência a função indefinida em MIGRACOES`
- `332c097 feat: Adiciona primeira migração para esquema de classificação`

**Tarefa 3 — migracao v2: ALTER TABLE itens ADD COLUMN produto_id, indice, e o banco legado**

- `93cdb09 fix: Define `_migracao_02_produto_id_em_itens` antes de usá-la em MIGRACOES`
- `128422f feat: Adiciona segunda migração para adicionar coluna produto_id em itens`

---

## Notas a mao — o que o script nao sabe

**1. A tarefa 1 conta 2 invocacoes e 5 commits, mas a primeira tentativa foi PARCIALMENTE revertida.**

A primeira invocacao parou com 5 de 7 verdes. A leitura do codigo separou tres coisas:

- ✅ o **executor** saiu correto de primeira, e e a parte dificil: `BEGIN`/`COMMIT`/`ROLLBACK` com
  `raise`, o `PRAGMA` interpolado (que nao aceita parametro ligado), o pulo por versao e o
  parametro de injecao. Nada disso precisou ser ditado;
- ⛔ `migracoes.py` tinha um defeito de raciocinio pontual: `return versao`, a variavel do `for`.
  Com `MIGRACOES` vazia o laco nunca roda e a funcao levanta `NameError`;
- ⛔ `banco.py` ficou com a chamada **tres vezes** e **sem o import**. Os dois ultimos commits da
  tentativa se chamam "corrigir bloco SEARCH/REPLACE": falha de **aplicacao** da edicao, nao de
  desenho.

Daí a decisao ter sido mista: `migracoes.py` foi **aproveitado**, `banco.py` foi **revertido** ao
estado do commit dos testes. ⚠️ O tempo e os 4 commits da tentativa revertida estao somados acima.
📋 **Custo honesto da tarefa 1: 1 tentativa parcial + 1 re-especificacao.**

⭐ A re-especificacao **encolheu** a mensagem de 3.551 para 1.727 bytes, e o turno 1 caiu de 5,67k
para 5,39k. Com o executor ja escrito, nao havia mais o que ensinar sobre transacao ou PRAGMA — e
"pedir so o que falta" custou menos contexto, nao mais.

**2. 🔴 As tarefas 2 e 3 ficaram verdes duplicando a funcao inteira. O oraculo nao viu.**

Repare nos commits `756fe93` ("corrige referência a função indefinida em MIGRACOES") e `93cdb09`
("Define `_migracao_02...` antes de usá-la"). O modelo local acrescenta a funcao nova **depois** da
linha `MIGRACOES = [...]`, bate em `NameError` ao rodar, e conserta **colando uma segunda copia
acima** em vez de mover a linha do registro. Nao moveu; copiou.

Resultado: `migracoes.py` chegou ao passo 4 com **as duas migracoes definidas duas vezes**, ~52
linhas mortas. `MIGRACOES` ficava amarrada ao **primeiro** par de objetos, e as segundas definicoes
apenas re-vinculavam os nomes. Como os corpos eram identicos, **os 21 testes passaram**.

📋 Quem denunciou foi a **cobertura**: 79%, com `59-98, 108-109` sem execucao. E o caso exato do
criterio do kit — linha nao-coberta e codigo morto (apagar) ou lacuna de teste (escrever). Aqui era
codigo morto. Depois da limpeza: **100%, 31 statements**.

⚠️ **Aconteceu nas duas tarefas, entao e padrao e nao acaso.** A mensagem da proxima story que
mexer num registro de funcoes precisa dizer: *a linha do registro fica no FIM do arquivo; acrescente
a funcao nova ACIMA dela*.

**3. Uma lacuna do oraculo foi encontrada na revisao, e tapada com teste novo.**

`test_migracoes.py` prova que o executor e atomico — mas com migracoes **injetadas**. Nada olhava
para as migracoes reais. Uma migracao real que usasse `executescript` faria COMMIT implicito,
destruiria a transacao do executor, e **a suite continuaria verde**: a atomicidade sumiria em
silencio.

✅ As migracoes desta story **nao** usam `executescript` — a proibicao nas mensagens funcionou. Mas
isso foi conferido por leitura, e leitura nao fica de guarda.

📁 `tests/test_migracoes_reais.py`, escrito no passo 4, percorre `MIGRACOES` e confere
`conexao.in_transaction` depois de cada uma. ⭐ Ele foi validado por **mutacao**: com
`executescript` na migracao v2, o teste fica vermelho com a mensagem certa. E vale para as
migracoes que as stories 008–013 acrescentarem, porque nao afirma quantas sao.

**4. Achado de kit: `ruff format .` mexeu nos `.md` da story 006, que ja esta PUBLICADA.**

O handoff avisava que o `ruff format .` reformata blocos de codigo dentro dos `.md` das tarefas, e
mandava restaurar com `git checkout --`. Desta vez ele alcancou tambem
`specs/006-saida-json/tarefas/tarefa-01.md` e `-02.md`.

📋 **O remedio melhor e nao deixar acontecer:** rodar `ruff format src/ tests/` em vez de `ruff
format .`. Escopado assim, ele nao toca em `.md` nenhum. Conferido nesta sessao.

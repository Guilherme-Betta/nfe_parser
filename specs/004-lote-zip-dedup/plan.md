# Plan — 004 · Lote `.zip`, dedup e o que nao derruba o lote

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

---

## Tarefas

| # | Tarefa | Arquivo alvo | Oraculo da tarefa | Criterios | Turno 1 (**medido**) | Status |
| - | ------ | ------------ | ----------------- | --------- | -------------------- | ------ |
| 1 | **Persistir**: `persistir_nota` insere a nota e os N itens, devolvendo `"nova"` | `src/nfe_parser/persistencia.py` (novo) | `tests/test_persistir_nota.py` (13) | C1 | ~4,9k ✅ | ⬜ |
| 2 | **Dedup idempotente**: `chave` ja presente devolve `"duplicada"` e **nao escreve nada** | `src/nfe_parser/persistencia.py` | `tests/test_dedup.py` (8) | C2 | ~4,3k ✅ | ⬜ |
| 3 | **Classificar**: raiz + `ide/mod` viram uma de 4 strings, sem nunca levantar | `src/nfe_parser/classificador.py` (novo) | `tests/test_classificador.py` (9) | C3 | ~3,5k ✅ | ⬜ |
| 4 | **Importar o `.zip`**: uma linha de log por arquivo, nenhuma excecao escapando | `src/nfe_parser/importador.py` (novo) | `tests/test_importar_lote.py` (16) | C4 | ~5,3k ✅ | ⬜ |
| 5 | **`.xml` avulso pelo MESMO caminho de codigo** | `src/nfe_parser/importador.py` | `tests/test_importar_avulso.py` (8) | C5 | ~4,8k ✅ | ⬜ |
| 6 | **Contadores**: a linha de `importacoes` fecha com os contadores batendo com o log | `src/nfe_parser/importador.py` | `tests/test_importacao_contadores.py` (7) | C6 | ~4,8k ✅ | ⬜ |

**Status:** ⬜ nao iniciada · 🔄 no modelo local · 👀 aguardando revisao · ✅ aceita

### Por que esta ordem, e nao outra

A ordem e a **das dependencias**, e ela e estrita: a 4 chama `persistir_nota` (1 e 2) e
`classificar_xml` (3); a 5 faz o `.xml` avulso desembocar na funcao por arquivo que a 4 criou; a 6
fecha a linha de `importacoes` que a 4 abriu.

⚠️ **A tarefa 1 antes da 2 nao e detalhe de gosto — e a regra 2.** Insercao e dedup sao **dois**
defeitos. Pedidos juntos, o modelo tende a resolver os dois com um `INSERT OR REPLACE`, que passa
em C2.1 e C2.2 e **reprova em C2.3**, porque reescreve o `criado_em`. Separadas, a tarefa 2 chega
com a insercao ja verde e so um problema para resolver.

---

## ⚠️ A decisao A volta a valer nesta story

A story 003 registrou uma decisao do Gui (2026-09-13, 11h48) que **nao chegou a ser aplicada**,
porque a 003 encolheu para uma tarefa so. O proprio registro dizia: *"ela volta a valer na proxima
story que fatiar em duas ou mais tarefas de verdade"*. **Esta e essa story**, com seis.

O problema: o `scripts/verify.py` roda `pytest -q` sobre a **suite inteira**, e o passo 2 commita
**todos** os testes antes de a implementacao comecar. Quando a tarefa 1 rodar, os testes das
tarefas 2 a 6 ja estarao commitados e **vermelhos**. O `--auto-test` realimenta essas falhas no
modelo, que tenta consertar cinco coisas de uma vez — exatamente a regra 2, que ja corrompeu
arquivo neste projeto, queimando as 3 reflexoes da regra 3 em trabalho que nao e da tarefa.

**Aplicacao (decisao A):** cada invocacao das tarefas **1 a 5** passa o `--test-cmd` **estreitado**:

```powershell
--test-cmd "python -m pytest -q tests\test_<modulo_da_tarefa>.py"
```

A **tarefa 6**, por ser a ultima, roda com o `scripts/verify.py` cheio — que ali e o oraculo certo,
porque a essa altura a suite inteira **tem** de estar verde.

> 🔴 **O passo 2 mostrou que aqui a decisao A e mais necessaria do que na 003, e por um motivo
> diferente do previsto.** Um `import` de modulo inexistente nao **falha** a suite: ele **interrompe
> a COLETA**. Medido agora: `pytest -q` na suite inteira devolve
> `Interrupted: 5 errors during collection`, e os 66 testes que ja passavam **nem chegam a rodar**.
> Ou seja, ate a tarefa 4 criar o `importador.py`, o `verify.py` cheio nao e so ruidoso — ele nao
> produz informacao nenhuma sobre a tarefa em curso. O `--test-cmd` estreitado nao e conveniencia,
> e a unica forma de o modelo local ver o proprio resultado.

> ⚠️ Isto contraria a letra do §5 do protocolo, que lista `test-cmd` entre os campos a nao repassar
> na linha de comando. O motivo do §5 e **nao repetir a toa** o que a config ja diz; aqui o campo
> nao esta sendo repetido, esta sendo **estreitado de proposito**, para fazer valer a regra de
> fatiamento que o proprio kit escreveu. Registrado como desvio consciente, com a decisao do Gui
> por tras.

⛔ **O que NAO e saida:** marcar os testes das outras tarefas com `skip` ou `xfail`. Isso e mexer no
oraculo durante a implementacao — a coisa que o passo 2 existe para impedir.

---

## Orcamento de contexto (regra 5)

Somado **antes** de invocar, nao depois. ⛔ **As fixtures XML NAO entram no `--read`** — o modelo
nao precisa ver o XML para implementar contra o teste, e uma NF-e inteira sozinha comeria o
orcamento.

🔴 **Estes numeros foram MEDIDOS no fim do passo 2**, com os testes ja escritos: `bytes ÷ 4`, que e
a regra de bolso para codigo. A primeira versao desta tabela era estimativa, e **errou feio** na
tarefa 4 — ver o quadro abaixo. Estimar tamanho de arquivo que ainda nao existe nao funciona.

| Tarefa | Sistema do Aider | Alvo | `--read` | `--message-file` | **Total** |
| ------ | ---------------- | ---- | -------- | ---------------- | --------- |
| 1 | ~2,0k | `persistencia.py` (novo, ~0,1k) | teste **1,89k** + `banco.py` **0,76k** | ~0,1k | **~4,9k** ✅ |
| 2 | ~2,0k | `persistencia.py` (~0,8k) | teste **1,36k** | ~0,1k | **~4,3k** ✅ |
| 3 | ~2,0k | `classificador.py` (novo, ~0,1k) | teste **1,25k** | ~0,1k | **~3,5k** ✅ |
| 4 | ~2,0k | `importador.py` (novo, ~0,1k) | teste **2,69k** | **~0,5k** | **~5,3k** ✅ |
| 5 | ~2,0k | `importador.py` (~0,9k) | teste **1,73k** | ~0,2k | **~4,8k** ✅ |
| 6 | ~2,0k | `importador.py` (~1,1k) | teste **1,56k** | ~0,1k | **~4,8k** ✅ |

### 🔴 O que a medicao do passo 2 mudou no fatiamento

**A tarefa 4 original virou duas.** Escrito o modulo de teste, ele saiu com **13.533 bytes ≈ 3,4k
tokens** — contra os ~2,0k que esta tabela estimava antes. Com isso o turno 1 da tarefa 4 batia em
**~6,0k**, em cima do teto de 6k da regra 5, e a conversao `bytes ÷ 4` tem margem de erro para os
dois lados: a ~7,2k o laco estaria condenado, em silencio.

O corte foi por criterio, nao por linha: **C4 (o `.zip`) virou a tarefa 4** e **C5 (o `.xml`
avulso) virou a tarefa 5**, cada uma com seu modulo de teste — que e a propria regra de "um modulo
de teste por sub-tarefa". A divisao tambem e honesta do ponto de vista do defeito: o C5 nao e "mais
do mesmo", e um criterio de **desenho** (os dois caminhos tem de convergir numa funcao so), com o
C5.4 servindo de detector de copia.

> ⭐ **Isto e o Achado E se repetindo, e desta vez ele foi pego a tempo.** A licao operacional:
> o orcamento de contexto so vale depois que os testes existem. Orcar no passo 1, com o modulo de
> teste ainda por escrever, produz um numero que parece medido e nao e.

### ⭐ A tarefa 4 ainda precisou de uma manobra

Mesmo depois do corte, ela precisa conhecer `persistencia.py`, `classificador.py` **e** o DDL de
`importacoes` / `importacao_arquivos` em `banco.py`. Passar os tres no `--read` da **~2,2k extras**
e leva o turno 1 de volta a ~7,5k.

**A manobra:** nao mandar os modulos, mandar o **contrato** deles. O `tarefa.txt` da tarefa 4 leva,
em texto, as duas linhas de `import`, as duas assinaturas com o que cada uma devolve, e **so os
dois `CREATE TABLE` que interessam**, recortados do DDL. Custa ~0,5k no lugar de ~2,2k.

> ⚠️ **O risco desta manobra, escrito antes de correr:** o modelo passa a depender de um resumo meu
> em vez do arquivo real. Se ele errar o nome de uma coluna, a falha aparece como `OperationalError`
> no `--auto-test`, nao como truncamento silencioso — ou seja, **e um modo de falha visivel**, que e
> justamente por que ele e preferivel ao estouro de contexto, que e invisivel. Anotar no passo 4 se
> aconteceu.

---

## Checagens antes de cada invocacao

1. `ollama ps` mostra `CONTEXT` = **8192**. Se mostrar outro valor, o `.aider.model.settings.yml`
   nao casou com o nome do modelo e **todo este orcamento deixa de valer**, em silencio.
2. `/clear` desde a tarefa anterior (regra 4).
3. O `tarefa.txt` foi reescrito para **esta** tarefa — um pedido, um defeito (regra 2).
4. ⛔ `edit-format` e `diff`, nunca `udiff` — o `udiff` falha em silencio.

---

## ✅ Passo 2 — resultado: o vermelho certo, e nenhuma tarefa nasceu verde

**Medido as 10h5x do dia 2026-09-14**, com os seis modulos de teste escritos e nenhuma linha de
implementacao:

```
ERROR tests/test_classificador.py          ModuleNotFoundError: nfe_parser.classificador
ERROR tests/test_dedup.py                  ModuleNotFoundError: nfe_parser.persistencia
ERROR tests/test_importacao_contadores.py  ModuleNotFoundError: nfe_parser.importador
ERROR tests/test_importar_avulso.py        ModuleNotFoundError: nfe_parser.importador
ERROR tests/test_importar_lote.py          ModuleNotFoundError: nfe_parser.importador
ERROR tests/test_persistir_nota.py         ModuleNotFoundError: nfe_parser.persistencia
Interrupted: 6 errors during collection
```

✅ **E o vermelho certo.** A falha e `ModuleNotFoundError` dos tres modulos a criar — nao
`No module named pytest`, que significaria `.venv` desativada e faria todo diff do modelo local
parecer errado.

✅ **Os 66 testes anteriores continuam verdes.** Rodados a parte, ignorando os seis modulos novos:
`66 passed in 0.76s`. Isso importa porque a interrupcao da coleta os esconde do `verify.py` cheio.

⭐ **Nenhuma tarefa nasceu verde — ao contrario da story 003.** La, duas das tres tarefas passaram
sem uma linha nova, porque o `extrator.py` ja era generico onde ninguem exigiu. Aqui o pre-voo do
*Achado I* ja tinha medido o motivo: o `src/` inteiro tem quatro funcoes publicas, `zipfile` nao
e importado em lugar nenhum e nao existe um unico `INSERT`. **As seis tarefas vao todas ao modelo
local**, que e a condicao que faltou a medicao 4 para resolver a previsao do P3.

| | Medicao 4 (story 003) | Medicao 5 (story 004) |
| - | --------------------- | --------------------- |
| Tarefas fatiadas | 3 | **6** |
| Tarefas que foram ao modelo local | **1** | **6** (a confirmar no passo 3) |
| Modulos de teste novos | 3 | **6** |
| Funcoes de teste novas | 28 | **61** |

### Bugs e ruidos observados no passo 2 (§6 do protocolo: anotar, nao consertar)

Nenhum. O `verify.py`, a `.venv` e as fixtures se comportaram como o pre-voo previa.

## Passo 4 — revisao

*(a preencher)*

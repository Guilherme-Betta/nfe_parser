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

| # | Tarefa | Arquivo alvo | Oraculo da tarefa | Criterios | Turno 1 (est.) | Status |
| - | ------ | ------------ | ----------------- | --------- | -------------- | ------ |
| 1 | **Persistir**: `persistir_nota` insere a nota e os N itens, devolvendo `"nova"` | `src/nfe_parser/persistencia.py` (novo) | `tests/test_persistir_nota.py` | C1 | ~4,7k ✅ | ⬜ |
| 2 | **Dedup idempotente**: `chave` ja presente devolve `"duplicada"` e **nao escreve nada** | `src/nfe_parser/persistencia.py` | `tests/test_dedup.py` | C2 | ~4,1k ✅ | ⬜ |
| 3 | **Classificar**: raiz + `ide/mod` viram uma de 4 strings, sem nunca levantar | `src/nfe_parser/classificador.py` (novo) | `tests/test_classificador.py` | C3 | ~3,5k ✅ | ⬜ |
| 4 | **Importar o lote**: `.zip` e `.xml` avulso pelo mesmo caminho, uma linha de log por arquivo, nenhuma excecao escapando | `src/nfe_parser/importador.py` (novo) | `tests/test_importar_lote.py` | C4, C5 | ~4,6k ⚠️ | ⬜ |
| 5 | **Contadores**: a linha de `importacoes` fecha com os 5 contadores batendo com o log | `src/nfe_parser/importador.py` | `tests/test_importacao_contadores.py` | C6 | ~4,2k ✅ | ⬜ |

**Status:** ⬜ nao iniciada · 🔄 no modelo local · 👀 aguardando revisao · ✅ aceita

### Por que esta ordem, e nao outra

A ordem e a **das dependencias**, e ela e estrita: a 4 chama `persistir_nota` (1 e 2) e
`classificar_xml` (3); a 5 fecha a linha de `importacoes` que a 4 abriu.

⚠️ **A tarefa 1 antes da 2 nao e detalhe de gosto — e a regra 2.** Insercao e dedup sao **dois**
defeitos. Pedidos juntos, o modelo tende a resolver os dois com um `INSERT OR REPLACE`, que passa
em C2.1 e C2.2 e **reprova em C2.3**, porque reescreve o `criado_em`. Separadas, a tarefa 2 chega
com a insercao ja verde e so um problema para resolver.

---

## ⚠️ A decisao A volta a valer nesta story

A story 003 registrou uma decisao do Gui (2026-09-13, 11h48) que **nao chegou a ser aplicada**,
porque a 003 encolheu para uma tarefa so. O proprio registro dizia: *"ela volta a valer na proxima
story que fatiar em duas ou mais tarefas de verdade"*. **Esta e essa story**, com cinco.

O problema: o `scripts/verify.py` roda `pytest -q` sobre a **suite inteira**, e o passo 2 commita
**todos** os testes antes de a implementacao comecar. Quando a tarefa 1 rodar, os testes das
tarefas 2 a 5 ja estarao commitados e **vermelhos**. O `--auto-test` realimenta essas falhas no
modelo, que tenta consertar cinco coisas de uma vez — exatamente a regra 2, que ja corrompeu
arquivo neste projeto, queimando as 3 reflexoes da regra 3 em trabalho que nao e da tarefa.

**Aplicacao (decisao A):** cada invocacao das tarefas **1 a 4** passa o `--test-cmd` **estreitado**:

```powershell
--test-cmd "python -m pytest -q tests\test_<modulo_da_tarefa>.py"
```

A **tarefa 5**, por ser a ultima, roda com o `scripts/verify.py` cheio — que ali e o oraculo certo,
porque a essa altura a suite inteira **tem** de estar verde.

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

| Tarefa | Sistema do Aider | Alvo | `--read` | `--message-file` | **Total** |
| ------ | ---------------- | ---- | -------- | ---------------- | --------- |
| 1 | ~2,0k | `persistencia.py` (novo, ~0,1k) | teste ~1,6k + `banco.py` ~0,9k | ~0,1k | **~4,7k** ✅ |
| 2 | ~2,0k | `persistencia.py` (~0,8k) | teste ~1,2k | ~0,1k | **~4,1k** ✅ |
| 3 | ~2,0k | `classificador.py` (novo, ~0,1k) | teste ~1,3k | ~0,1k | **~3,5k** ✅ |
| 4 | ~2,0k | `importador.py` (novo, ~0,1k) | teste ~2,0k | **~0,5k** | **~4,6k** ⚠️ |
| 5 | ~2,0k | `importador.py` (~1,1k) | teste ~1,0k | ~0,1k | **~4,2k** ✅ |

### ⭐ A tarefa 4 e a unica que precisou de manobra

Feita a soma ingenua, ela estourava: alem do teste (~2,0k), ela precisa conhecer `persistencia.py`,
`classificador.py` **e** o DDL de `importacoes` / `importacao_arquivos` em `banco.py`. Passar os
tres no `--read` da **~2,2k extras** e leva o turno 1 a **~6,3k** — acima do teto empirico da regra
5, onde a story 001 ja viu as 3 reflexoes rodarem **truncadas em silencio**.

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

## Passo 2 — resultado

*(a preencher quando os testes estiverem commitados e o `verify.py` rodar vermelho)*

## Passo 4 — revisao

*(a preencher)*

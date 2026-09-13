# Plan — 003 · NFC-e 65 e multi-item

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

## Tarefas

Todas em `src/nfe_parser/extrator.py`. Nenhum modulo novo.

| # | Tarefa | Oraculo da tarefa | `edit-format` | Turno 1 (est.) | Status |
| - | ------ | ----------------- | ------------- | -------------- | ------ |
| 1 | **NFC-e 65**: `extrair_nota` aceita `mod=65` com os mesmos campos da 55, sem quebrar diante do bloco `<infNFeSupl>` | `tests/test_extrator_nfce65.py` | `diff` | ~4,2k | ⬜ |
| 2 | **Multi-item**: N blocos `det` viram N itens, com `gtin` resolvido **por item** | `tests/test_extrator_multi_item.py` | `diff` | ~4,3k | ⬜ |
| 3 | **Anotacao de tipo**: retorno e parametros de toda funcao publica do modulo | `tests/test_anotacoes.py` | `diff` | ~4,0k | ⬜ |

**Status:** ⬜ nao iniciada · 🔄 no modelo local · 👀 aguardando revisao · ✅ aceita

### Por que esta ordem, e nao outra

A tarefa **3 e a ultima de proposito**. O teste dela descobre as funcoes publicas por
**introspecao** (C4.1), entao ele cobre o que existir no modulo **no momento em que roda**. Se ela
rodasse primeiro e a tarefa 1 ou 2 criasse uma funcao auxiliar publica sem anotacao, a tarefa 3
apareceria "pronta" e o modulo terminaria meio anotado. Fechando por ultimo, ela varre tudo.

### Orcamento de contexto (regra 5)

Somado **antes** de invocar, nao depois:

| Item | tokens (est.) |
| ---- | ------------- |
| Prompt de sistema do Aider | ~2,0k |
| `--map-tokens 0` (mapa desligado; o alvo ja vai explicito) | 0 |
| `src/nfe_parser/extrator.py` (66 linhas hoje, ~90 ao fim) | ~0,9k |
| Modulo de teste no `--read` | ~1,2k |
| Instrucao do `--message-file` | ~0,1k |
| **Total turno 1** | **~4,2k** ✅ |

Folga confortavel ate os 6k da regra 5. ⛔ **As fixtures XML NAO entram no `--read`** — o modelo
nao precisa ver o XML para implementar contra o teste, e uma NF-e inteira sozinha comeria o
orcamento.

---

## ⚠️ Decisao pendente — o oraculo de cada tarefa vs. o `verify.py`

**Levantada no passo 1 da medicao 4. Precisa de decisao do Gui antes do passo 3.**

O `scripts/verify.py` roda `pytest -q` sobre a **suite inteira**. O passo 2 do protocolo manda
**commitar todos os testes antes** de a implementacao comecar — e essa ordem e certa, porque testes
nao commitados sao testes que o modelo local pode editar para passar.

O choque: quando a tarefa 1 rodar, os testes das tarefas 2 e 3 ja estarao commitados e
**vermelhos**. O `--auto-test` vai realimentar essas falhas no modelo, que vai tentar consertar as
tres coisas de uma vez. Isso e **exatamente a regra 2** — um pedido, tres defeitos — que ja
corrompeu arquivo neste projeto, e queima as 3 reflexoes da regra 3 em trabalho que nao e da tarefa.

Duas saidas, e a escolha e do Gui:

| | O que fazer | Custo |
| - | ----------- | ----- |
| **A** | Passar `--test-cmd "python -m pytest -q tests/test_<modulo>.py"` na linha de comando de cada tarefa, e deixar a **tarefa 3** rodar com o `verify.py` cheio | ⚠️ Contraria a letra do §5 do protocolo, que lista `test-cmd` entre os campos a **nao** repassar na linha de comando |
| **B** | Nao mexer em nada; aceitar que as tarefas 1 e 2 rodem com a suite inteira vermelha | ⚠️ Aceita a violacao da regra 2 de fatiamento, com risco documentado de corromper o arquivo |

Recomendacao: **A**. O motivo do §5 para nao repassar esses campos e nao repetir a toa o que a
config ja diz; aqui o `--test-cmd` nao esta sendo repetido, esta sendo **estreitado de proposito**,
para fazer valer a regra de fatiamento que o proprio kit escreveu. A tarefa 3, que roda por ultimo,
fecha com o oraculo completo — entao nada e aceito sem a suite inteira verde.

⛔ **O que NAO e saida:** marcar os testes das outras tarefas com `skip` ou `xfail`. Isso e mexer
no oraculo durante a implementacao, que e a coisa que o passo 2 existe para impedir.

---

## ⚠️ Risco: as tarefas 1 e 2 podem ja nascer verdes

Registrado no passo 1, **sem verificacao** — checar custaria cota do passo errado, e os criterios
sao pre-registrados e nao mudam de qualquer forma.

Lendo o `extrator.py` atual: ele ja faz `for det in inf.det` (multi-item pode ja funcionar) e ja usa
`int(inf.ide.mod.value)` (o modelo 65 pode ja sair certo). Se for o caso, as tarefas 1 e 2 viram
**testes de regressao que passam de primeira**, e o passo 3 encolhe para quase so a tarefa 3.

**Consequencia para a medicao 4, e e por isso que fica escrito aqui:** um passo 3 quase vazio faz o
Δ% da L3 ficar perto de zero **por falta de trabalho**, nao porque o offload funcionou. Os dois
desfechos se parecem no numero e sao coisas opostas. A leitura da L3 tem que vir acompanhada de
**quantas tarefas o modelo local de fato executou** e **quantas ja estavam verdes** — senao a
previsao da §1 do protocolo se confirma sozinha, de graca, e nao prova nada.

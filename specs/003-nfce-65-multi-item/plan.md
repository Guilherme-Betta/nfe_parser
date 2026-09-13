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
| 1 | **NFC-e 65**: `extrair_nota` aceita `mod=65` com os mesmos campos da 55, sem quebrar diante do bloco `<infNFeSupl>` | `tests/test_extrator_nfce65.py` (11) | `diff` | ~4,2k | 🟩 **verde de nascenca** |
| 2 | **Multi-item**: N blocos `det` viram N itens, com `gtin` resolvido **por item** | `tests/test_extrator_multi_item.py` (8) | `diff` | ~4,3k | 🟩 **verde de nascenca** |
| 3 | **Anotacao de tipo**: retorno e parametros de toda funcao publica do modulo | `tests/test_anotacoes.py` (9) | `diff` | **4,7k** ✅ | ✅ **aceita** — 1 turno, 0 reflexoes |

**Status:** ⬜ nao iniciada · 🔄 no modelo local · 👀 aguardando revisao · ✅ aceita

### Revisao do passo 4 — o que foi lido, e o que o oraculo nao vê

Commit do modelo local: **`90154bc`**, autoria `Aider (qwen2.5-coder:14b)`.

| Conferido | Resultado |
| --------- | --------- |
| Diff linha a linha | **2 linhas**, as duas `def`. Nada mais tocado |
| Arquivo inteiro relido (66 linhas) | Sem corpo duplicado, sem codigo depois do `return` — o modo de falha do Achado H, que **nenhuma** regra do `ruff` pega e nenhuma assercao alcanca |
| Comportamento | Inalterado. Anotacao de tipo nao roda em tempo de execucao no CPython |
| `scripts/verify.py` | **66 passed**, verde |
| `python -m ruff check .` | `All checks passed!` |

⚠️ **Fora de escopo, anotado e NAO consertado (regra da §6 do protocolo):**
`python -m ruff format --check .` reprova **7 arquivos**, dos quais quatro sao anteriores a esta
story: `scripts/verify.py`, `specs/002-extrair-nfe-55/spec.md`, `.../api-nfelib.md` e o
`split('.')` que a story 002 escreveu no `extrator.py`. Ou seja, **`ruff format` nunca foi padrao
deste projeto** — o oraculo roda `ruff check`, que e outra coisa. Rodar `ruff format` agora
reescreveria a entrega da story 002, que a §4 da spec poe explicitamente fora de escopo.

> Candidata a decisao futura, fora de qualquer janela medida: adotar `ruff format` no projeto
> inteiro de uma vez, ou nunca. O estado atual — nem adotado, nem recusado por escrito — e o unico
> que garante que a pergunta volte toda story.

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

## ✅ Resultado do passo 2 — duas das tres tarefas nasceram verdes

**Medido as 12h do dia 2026-09-13**, rodando `scripts/verify.py` com os testes novos commitados e
nenhuma linha de implementacao escrita:

```
8 failed, 58 passed
```

**As 8 falhas sao todas de `test_anotacoes.py`** (tarefa 3). Os 11 testes da NFC-e 65 e os 8 de
multi-item passaram **sem uma linha de codigo nova**.

Nao e sorte, e sim o `extrator.py` da story 002 ja ter sido escrito generico onde ninguem exigiu
que fosse: o laco `for det in inf.det` ja cobria N itens, e `int(inf.ide.mod.value)` ja devolvia 65
para uma NFC-e. O que a story 002 nao cobria era a **prova** disso — e agora cobre, com 19 testes.

> **Isso muda o que as tarefas 1 e 2 sao.** Elas nao sao mais implementacao: sao **testes de
> caracterizacao**, que travam por contrato um comportamento que existia por acidente. O valor
> delas e real e e de regressao — mas nenhuma delas vai ao modelo local, porque nao ha o que
> implementar.

**Consequencia para a medicao 4, e esta e a parte que dói:** o passo 3 encolheu para **uma** tarefa,
e uma tarefa pequena. O Δ% da L3 vai sair baixo — mas um Δ baixo **por falta de trabalho** e
indistinguivel, no numero, de um Δ baixo **porque o offload funcionou**. A previsao da §1 do
protocolo (`P3 ≅ 0,09 %/min`) sai desta medicao com n=1 tarefa trivial. **Registre a L3 com essa
ressalva colada nela**, senao a previsao se confirma de graca e nao prova nada.

---

## ✅ Decisao tomada: A — e ela virou inofensiva

**Decidida pelo Gui as 11h48 do dia 2026-09-13: opcao A.** Registro abaixo o problema e por que ele
deixou de existir na pratica.

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

Recomendacao aceita: **A**. O motivo do §5 para nao repassar esses campos e nao repetir a toa o que
a config ja diz; ali o `--test-cmd` nao estaria sendo repetido, estaria sendo **estreitado de
proposito**, para fazer valer a regra de fatiamento que o proprio kit escreveu.

> ✅ **Mas o passo 2 dissolveu o problema.** Como as tarefas 1 e 2 nasceram verdes, sobrou **uma**
> invocacao do Aider — a tarefa 3, que e a ultima e que ja rodaria com o `verify.py` cheio de
> qualquer forma. **Nao ha nenhum teste vermelho fora da tarefa dela**, entao nao existe o vazamento
> que a opcao A ia conter. O passo 3 roda com a config como esta, sem `--test-cmd` na linha de
> comando, e **sem desvio nenhum do §5 do protocolo**.
>
> A decisao fica registrada assim mesmo: ela volta a valer na proxima story que fatiar em duas ou
> mais tarefas de verdade.

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

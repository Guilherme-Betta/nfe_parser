# Plan — 005 · Cancelamento em duas passadas

> **Sprint backlog: a spec fatiada em tarefas que cabem no modelo local.**
> Uma linha = uma invocacao do Aider.
>
> ⭐ **Esta e a primeira story em que o passo 3 roda por script**
> (`scripts/rodar_passo3.py`), sem ninguem no teclado. O backlog abaixo existe em dois formatos: em
> prosa aqui, e em dados no `tarefas.json` ao lado. Sao o mesmo backlog — se divergirem, o
> `tarefas.json` e o que roda.

## Regras de fatiamento (nao sao sugestoes)

Herdadas da story 004, sem alteracao.

| # | Regra | Vem de |
| - | ----- | ------ |
| 1 | Cada tarefa cabe em **~300 linhas** de codigo relevante | orcamento de 8192 tokens |
| 2 | **Um pedido, um defeito** | Fase 0: dois defeitos no mesmo pedido -> blocos SEARCH/REPLACE sobrepostos -> arquivo corrompido |
| 3 | Cada tarefa cabe em **3 tentativas** do `--auto-test` | e o teto do Aider (`Only 3 reflections allowed`) |
| 4 | **`/clear` entre tarefas** | 3 turnos ja estouram os 8k, em silencio |
| 5 | **>6k tokens no turno 1 condena o laco** | story 001: o turno 1 saiu a 7,0k e as 3 reflexoes rodaram truncadas |
| 6 | **Orce tambem o despejo de falha**, que escala com o **numero de testes do modulo** | Achado N: na tarefa 4 da 004 o turno 1 coube em 5,6k e o laco chegou a **24k** |

> A regra 4 e atendida de graca pelo `rodar_passo3.py`: cada tarefa e um processo `aider` novo,
> entao nao existe historico para limpar. A regra 6 e a que ainda depende de julgamento — e por
> ela que nenhum modulo desta story passa de **8 testes**.

---

## Tarefas

| # | Tarefa | Arquivo alvo | Oraculo da tarefa | Criterios | Turno 1 (estimado) | Status |
| - | ------ | ------------ | ----------------- | --------- | ------------------ | ------ |
| 1 | **Ler o evento**: `extrair_evento` devolve os tres campos, e nunca levanta por campo ausente | `src/nfe_parser/cancelamento.py` (novo) | `tests/test_extrair_evento.py` | C1 | ~4,3k | ✅ |
| 2 | **Aplicar o evento**: `aplicar_cancelamento` cancela a nota que existe e devolve orfao para a que nao existe | `src/nfe_parser/cancelamento.py` | `tests/test_aplicar_cancelamento.py` | C2 | ~4,6k | ✅ |
| 3 | **Duas passadas**: `importar` varre o lote duas vezes; a ordem no `.zip` deixa de importar | `src/nfe_parser/importador.py` | `tests/test_duas_passadas.py` | C3 | ~5,2k | ✅ |
| 4 | **O contador**: `cancelamentos_aplicados` deixa de ser zero fixo | `src/nfe_parser/importador.py` | `tests/test_contador_cancelamentos.py` | C4 | ~4,8k | ✅ |

**Status:** ⬜ nao iniciada · 🔄 no modelo local · 👀 aguardando revisao · ✅ aceita

> ⚠️ **Os numeros do turno 1 sao ESTIMATIVA, nao medicao** — os modulos de teste ainda nao existiam
> quando esta tabela foi escrita. O Achado E diz exatamente que estimar tamanho de arquivo que ainda
> nao existe nao funciona: na story 004 a estimativa errou 1,4k na tarefa 4 e a tarefa precisou ser
> partida em duas. **Esta tabela e reconferida no fim do passo 2**, com `bytes ÷ 4` sobre os testes
> ja escritos, e a divisao muda se algum passar de 6k.

### Por que esta ordem, e nao outra

A ordem e a das **dependencias**, e ela e estrita:

- A **2** chama o dicionario que a **1** produz.
- A **3** chama as duas funcoes da **1** e da **2**.
- A **4** conta as linhas de log que a **3** escreve. Sem a 3, nao ha o que contar.

⚠️ **A 1 antes da 2 e a regra 2, nao gosto pessoal.** "Ler o XML" e "escrever no banco" sao dois
defeitos. Pedidos juntos, a tendencia conhecida do modelo local e resolver os dois num `UPDATE`
unico que le o XML inline — que passa em C2.1 e reprova em C1.4 e C2.4, porque o tratamento do enum
de `tpEvento` nunca chega a existir como decisao separada.

⚠️ **A 3 antes da 4 tambem.** "Varrer duas vezes" e "somar o contador" sao dois defeitos, e o
segundo e uma linha de SQL. Juntos, o modelo tende a mexer no `UPDATE importacoes` no meio do
refactor das passadas e produzir um diff que ninguem consegue revisar.

---

## Orcamento de contexto (regras 5 e 6)

⛔ **As fixtures XML NAO entram no `--read`.** Os stubs de evento vivem **dentro** de cada modulo de
teste, como constantes — que e como a 004 ja faz.

🔴 **Recalculado no fim do passo 2**, com os quatro modulos de teste escritos: `bytes ÷ 4` sobre
arquivos que ja existem. A coluna **REAL** foi preenchida depois, com o que o Aider de fato enviou.

| Tarefa | Sistema do Aider | Alvo | `--read` (o teste) | `--message-file` | **Previsto no P2** | Estimado no P1 | 🔴 **REAL** |
| ------ | ---------------- | ---- | ------------------ | ---------------- | ------------------ | -------------- | ----------- |
| 1 | ~2,0k | `cancelamento.py` (novo, 0,0k) | **1,17k** | **0,61k** | ~3,8k | ~4,3k | **5,2k** |
| 2 | ~2,0k | `cancelamento.py` (~0,4k) | **1,19k** | **0,61k** | ~4,2k | ~4,6k | **5,5k** |
| 3 | ~2,0k | `importador.py` (**0,92k**) | **1,85k** | **0,75k** | ~5,5k ⚠️ | ~5,2k | **6,4k** ⛔ |
| 4 | ~2,0k | `importador.py` (~1,3k) | **1,38k** | **0,32k** | ~5,0k | ~4,8k | **5,8k** |

> 🔴 **As quatro previsoes erraram para BAIXO, entre +0,8k e +1,4k.** A formula `bytes ÷ 4` se
> sustenta; o que esta errado e a constante `~2,0k` do "Sistema do Aider", que na pratica custa
> **~2,7k a ~3,4k**. Detalhamento e a proposta de correcao em
> [`passo3-registro.md`](passo3-registro.md).
>
> A consequencia pratica: a tarefa 3 foi orcada em 5,5k, **abaixo** do teto de 6k, e entrou no
> laco a **6,4k**, acima. O aviso escrito abaixo — "a tarefa 3 e a de risco" — acertou o alvo pelo
> motivo errado, e a margem que eu achava ter nao existia.

⚠️ **A tarefa 3 e a de risco: 5,5k contra o teto de 6k da regra 5.** Ela nao foi partida porque
"varrer duas vezes" e **um** defeito — parti-la seria inventar uma fronteira que a spec nao tem, e
a regra 2 corta nos dois sentidos. O que sustenta a decisao e a regra 6: o modulo tem **7 testes**,
dos quais 6 nascem vermelhos. E menos da metade dos 16 que levaram o laco da tarefa 4 da 004 a 24k.

> Se ela nao convergir, o remedio nao e repetir o pedido — e partir por criterio (C3.1–C3.4 numa
> tarefa, C3.5–C3.7 noutra) e retomar com `--a-partir-de 3`. Escrito antes de correr, para nao ser
> decidido no susto.

### Tamanho dos modulos de teste, contra a regra 6

| Modulo | Funcoes `def test_` | Vermelhos no passo 2 |
| ------ | ------------------- | -------------------- |
| `test_extrair_evento.py` | 6 | 6 (falha na coleta) |
| `test_aplicar_cancelamento.py` | 7 | 7 (falha na coleta) |
| `test_duas_passadas.py` | 7 | **6** — um ja nasce verde |
| `test_contador_cancelamentos.py` | 5 | 5 |

Nenhum passa de 8, que e o teto que a regra 6 impos a esta story.

### A manobra da story 004 continua valendo

As tarefas 3 e 4 precisam conhecer `cancelamento.py`, `classificador.py` e o DDL. Passar os tres no
`--read` custaria ~2,2k e levaria o turno 1 a ~7,4k.

**Em vez disso, o `--message-file` leva o CONTRATO**: as linhas de `import`, as assinaturas com o
que cada funcao devolve, e so as colunas do DDL que interessam. Custa ~0,5k no lugar de ~2,2k.

> ⚠️ O risco, escrito antes de correr (e o mesmo da 004): o modelo passa a depender de um resumo em
> vez do arquivo real. Se eu errar o nome de uma coluna, a falha aparece como `OperationalError` no
> `--auto-test` — **modo de falha visivel**, que e justamente por que ele e preferivel ao estouro de
> contexto, que e invisivel.

---

## O que o `rodar_passo3.py` ja garante, e o que continua sendo meu

| Garantido pelo script | Continua sendo decisao do Claude |
| --------------------- | -------------------------------- |
| `--test-cmd` estreitado ao modulo da tarefa (a decisao A da 004) | **re-especificar** uma tarefa que nao convergiu |
| `--read` no teste, entao o modelo **nao pode** edita-lo | decidir se aproveita ou reverte o commit da tentativa que falhou |
| barra invertida no `--test-cmd` (a armadilha do `cmd.exe`) | a coluna **Quem resolveu** do registro (Achado M) |
| conferir o oraculo por conta propria, nao acreditar no Aider | a leitura linha a linha do passo 4 (Achado H) |
| parar na primeira que nao converge | |

---

## Checagens antes de rodar

O `rodar_passo3.py` faz as sete do seu pre-voo sozinho e **recusa rodar** se alguma falhar. Restam
duas que sao minhas:

1. Os quatro modulos de teste estao **commitados** antes de a implementacao comecar.
2. O vermelho e o **vermelho certo** (§5 da spec), nao `No module named pytest`.

---

## ✅ Passo 2 — resultado: o vermelho certo, e um teste que ja nasceu verde

**Medido em 2026-09-14**, com os quatro modulos escritos e nenhuma linha de implementacao.

```
ERROR tests/test_extrair_evento.py        ModuleNotFoundError: No module named 'nfe_parser.cancelamento'
ERROR tests/test_aplicar_cancelamento.py  ModuleNotFoundError: No module named 'nfe_parser.cancelamento'
Interrupted: 2 errors during collection
```

✅ **E o vermelho certo.** `ModuleNotFoundError` do modulo a criar — nao `No module named pytest`,
que significaria `.venv` desativada e faria todo diff do modelo local parecer errado.

✅ **Os modulos 3 e 4 falham por ASSERCAO, nao por coleta** — rodados a parte, porque a interrupcao
da coleta acima os esconde: `6 failed, 1 passed` e `5 failed`. Isso e a diferenca desta story para
a 004: metade do alvo (`importador.py`) ja existe.

✅ **Os 133 testes anteriores continuam verdes**, rodados ignorando os quatro modulos novos.

### ⚠️ Um teste nasceu verde, e o registro precisa dizer qual

`test_duas_passadas.py::test_evento_orfao_registra_e_nao_cria_nota_fantasma` **passa sem uma linha
nova**. Nao e defeito do teste: a story 004 ja registra **todo** evento como `cancelamento_orfao` e
ja nao cria nota a partir de evento, entao o caso orfao ela satisfaz por construcao.

⭐ Anotado aqui porque a story 003 perdeu essa informacao e ela distorce o placar: sem esta linha,
a tarefa 3 pareceria ter 7 testes resolvidos pelo modelo local quando sao **6**. E o mesmo erro de
leitura que o Achado M descreve, uma casa antes.

---

## ✅ Passo 3 — resultado

**4/4 tarefas verdes, 6 invocacoes, 3/4 resolvidas pelo modelo local.** O detalhamento, os numeros
de contexto medidos e o achado principal estao em [`passo3-registro.md`](passo3-registro.md), que
foi **reconstruido a mao** porque o script apaga o registro a cada `--a-partir-de`.

Em uma linha: **o orcamento do kit subestima o turno 1 em ~1k**, as tres invocacoes da tarefa 3
comecaram acima do teto de 6k, e por isso ela nunca teve chance.

---

## ✅ Passo 4 — revisao: o que foi lido, o que mudei e o que anotei

Lidos os **dois modulos inteiros** (`cancelamento.py` e `importador.py`), nao so o diff. O motivo e
o Achado H: na story 004, 35 testes passavam, o `ruff` passava, e uma funcao estava com o corpo
inteiro duplicado **depois do `return`** — codigo morto que nenhuma assercao alcanca.

| Conferido | Resultado |
| --------- | --------- |
| Corpo duplicado depois do `return` (Achado H) | ✅ **Nenhum**, nos dois modulos |
| `print()` de debug deixado no codigo de producao | ✅ **Nenhum** (`grep` em todo o `src/`) |
| `scripts/verify.py` | ✅ **164 passed** |
| `ruff format` e `ruff check --fix` | ✅ 1 arquivo reformatado, 3 erros corrigidos, 0 restantes |
| Nenhum `.zip`, `.db`, `.env` ou `.sqlite` rastreado | ✅ `git ls-files` limpo |
| Nenhum CPF/CNPJ real | ✅ o unico CNPJ nas fixtures e o anonimizado `99999999000199` |
| `passo3-logs/` fora do repo | ✅ ja no `.gitignore` |

### Cobertura como diagnostico (sem limiar)

```
src/nfe_parser/cancelamento.py   33 stmts   0 miss   100%
src/nfe_parser/importador.py     73 stmts   3 miss    96%   faltando: 25-27
```

Duas linhas nao-cobertas apareceram na primeira medida, e elas contavam historias diferentes:

**(1) A linha do `.xml` avulso que e um evento — lacuna de teste, e foi escrita.** O ramo existia,
estava correto, e nenhum teste passava por ele. Nao e linha morta: e o **C5 da story 004**, que
exige que o `.zip` e o avulso desemboquem no mesmo caminho de codigo. Sem o teste, "os dois
caminhos convergem" valia para nota e nao valia para evento — e ninguem saberia.
✅ Acrescentado `test_evento_chega_tambem_como_xml_avulso`, e a cobertura fechou.

**(2) As linhas 25-27 — ressalva PRE-EXISTENTE, nao mexida.** E o `except ValueError` de
`extrair_nota` em `_processar_arquivo`, que a story 004 ja tinha anotado como ressalva (c): o
`except` envolve tambem a chamada a `persistir_nota`, entao um erro da persistencia seria
registrado como `invalida`, culpando o XML por um defeito que nao e dele. **Nenhum criterio da 005
cobre isso.** Continua anotada, continua candidata a story 006.

### 🔧 O que a revisao mudou no codigo

Tudo cosmetico, nenhuma mudanca de comportamento — os 164 testes ficaram verdes antes e depois:

- **`cancelamento.py` ganhou docstrings e comentarios.** O modelo local entregou o modulo sem
  nenhum, e o resto do projeto tem. Os dois comentarios que importam explicam *por que* o
  `getattr(..., "value", ...)` existe e *por que* o `AND status = 'ok'` existe — sem eles, os dois
  parecem enfeite e o proximo a mexer os remove.
- **Imports reordenados** (`datetime` da stdlib vinha depois dos de terceiros).
- **`110111` virou a constante `TP_EVENTO_CANCELAMENTO`**, com o comentario dizendo o que sao os
  outros `tpEvento`.
- **A query do `UPDATE` quebrada em duas linhas**, que passava de 100 colunas.

### ⚠️ Anotado e NAO consertado (§6: anotar, nao consertar)

**(a) `importar` decodifica e classifica cada arquivo duas vezes.** A separacao em listas faz
`decode` + `classificar_xml` na coleta, e `_processar_arquivo` refaz os dois. E desperdicio, nao
defeito, e nenhum teste o reprova. Passar o `texto` ja decodificado adiante e a correcao obvia —
mas e mudanca de assinatura de duas funcoes sem teste que a defina.

**(b) O `getattr(..., "value", ...)` esta nos tres campos, e so `tpEvento` precisa.** Em `chNFe` e
`dhEvento` ele e inofensivo e sugere, errado, que os tres podem vir como enum. Anotado porque
mexer aqui e mexer no unico ponto do modulo que tem armadilha real.

**(c) `ruff format .` reformata blocos de codigo dentro dos `.md` das tarefas.** Ele alterou
`tarefas/tarefa-02.md` durante o passo 4. Inofensivo — as tarefas ja tinham rodado —, mas se
acontecesse ANTES da invocacao mudaria a mensagem que o modelo local recebe, e o orcamento de
contexto junto. Vale saber antes de rodar `ruff` no meio de um passo 3.

### Contexto: os `ConverterWarning` na saida do pytest

Dois `ConverterWarning` aparecem na suite (`110110` e `ABC` nao sao `InfEventoTpEvento` validos).
Eles vem dos testes que exercitam o C1.4 **de proposito** — sao a prova de que o caminho da string
crua e percorrido. Nao sao ruido a silenciar.

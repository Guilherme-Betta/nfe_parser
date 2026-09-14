# Passo 3 — registro consolidado — 005-cancelamento-duas-passadas

> 🔴 **ESTE ARQUIVO FOI RECONSTRUIDO A MAO.** O `rodar_passo3.py` reescreve o registro a cada
> execucao, entao cada `--a-partir-de` APAGA o registro das tarefas anteriores. O arquivo que a
> ultima rodada gerou continha so a tarefa 4, e dizia "1 de 1". Os numeros abaixo vieram dos logs
> das quatro rodadas. **Bug do script, anotado e nao consertado** — ver a ressalva no fim.

Rodado em 2026-09-14, entre ~15:08 e 15:25, por `scripts/rodar_passo3.py`.

- **Tarefas verdes:** 4 de 4
- **Invocacoes do Aider:** **6** (4 tarefas + 2 re-especificacoes da tarefa 3)
- **Commits do modelo local:** 11
- **Tempo total no passo 3:** ~9,0 min
- **CONTEXT do Ollama:** **8192** ✅ (conferido com `ollama ps` durante a rodada, 100% GPU)

| # | Tarefa | Verde? | Invocacoes | Tempo | Commits | Quem resolveu |
| - | ------ | ------ | ---------- | ----- | ------- | ------------- |
| 1 | `extrair_evento` le os tres campos sem levantar | ✅ | 1 | 58,1s | 3 | 🤖 **modelo local** |
| 2 | `aplicar_cancelamento` cancela ou devolve orfao | ✅ | 1 | 37,7s | 1 | 🤖 **modelo local** |
| 3 | `importar` em duas passadas | ✅ | **3** | 236,0 + 126,3 + 51,6s | 5 | 👤 **Claude ditou** |
| 4 | `cancelamentos_aplicados` conta de verdade | ✅ | 1 | 62,3s | 2 | 🤖 **modelo local** |

**4/4 tarefas verdes, 3/4 resolvidas pelo modelo local.** As duas linhas nao sao a mesma coisa, e e
exatamente por isso que esta coluna existe (Achado M).

---

## 🔴 O achado principal desta medicao: o orcamento do kit subestima o turno 1

O turno 1 de **todas as seis invocacoes** saiu acima do que o passo 2 tinha orcado. Nao foi uma
tarefa que escapou — foi o metodo.

| Invocacao | Orcado no passo 2 | **Medido** | Erro |
| --------- | ----------------- | ---------- | ---- |
| tarefa 1 | 3,8k | **5,2k** | +1,4k |
| tarefa 2 | 4,2k | **5,5k** | +1,3k |
| tarefa 3a | 5,5k | **6,4k** ⚠️ | +0,9k |
| tarefa 3b | 5,5k | **7,2k** ⚠️ | +1,7k |
| tarefa 3c | 5,5k | **6,2k** ⚠️ | +0,7k |
| tarefa 4 | 5,0k | **5,8k** | +0,8k |

**A causa:** o orcamento do kit soma `~2,0k` para o "sistema do Aider". Refazendo a conta ao
contrario a partir dos numeros medidos, o custo fixo real fica entre **~2,7k e ~3,4k**. O resto da
formula (`bytes ÷ 4` para alvo, teste e mensagem) se sustenta; **a constante e que esta errada**.

> ⭐ **Proposta para o kit, com lastro nestes seis numeros: trocar `~2,0k` por `~3,0k` na linha
> "Sistema do Aider" do orcamento.** E uma mudanca no kit, entao e decisao do Gui — anotada aqui,
> nao aplicada.

### O que isso corrige na leitura da tarefa 3

**As tres invocacoes da tarefa 3 comecaram acima do teto de 6k da regra 5** — 6,4k, 7,2k e 6,2k.
Pela propria regra 5 o laco estava condenado nas tres, e o orcamento do passo 2 dizia 5,5k, abaixo
do teto. Nao havia como saber sem medir.

🔴 **Isto corrige o que ficou escrito no commit `4ac77a1`.** La eu registrei como achado que existe
"um piso abaixo do qual re-especificar nao ajuda, porque o defeito e de conformidade com o formato
de edicao". A conclusao era prematura. O sintoma da terceira invocacao — um bloco SEARCH/REPLACE
sem o separador `=======` — e **sintoma classico de truncamento**, o mesmo que a story 004 registrou
na tarefa 4 (`# Resto do codigo...` e conselhos vagos no lugar de codigo). A explicacao simples e
que o turno 1 estourou o teto nas tres vezes, nao que o modelo seja incapaz daquele formato.

**O que a tarefa 3 mede de verdade:** que re-especificar nao salva uma tarefa cujo turno 1 ja
estourou o teto — e, pior, que **re-especificar AUMENTA o turno 1**, porque a mensagem cresce. A 3b
foi a mensagem mais longa que escrevi e a que mais estourou (7,2k). A 3c, mais curta, baixou para
6,2k e ainda assim ficou acima.

> ⚠️ A consequencia pratica e contra-intuitiva e vale para o kit: quando uma tarefa falha por
> contexto, **a resposta certa e encolher o pedido, nao detalha-lo**. O instinto de explicar melhor
> empurra na direcao errada.

### O laco, de novo (Achado N)

A primeira invocacao da tarefa 3 escalou **6,4k → 8,3k → 20k → 33k** contra um `num_ctx` de 8192.
A tarefa 4, que convergiu, foi **5,8k → 18k** — ou seja, ate uma tarefa que termina verde passa
longe do teto durante a reflexao. O despejo de falha continua sendo o maior consumidor de contexto
do kit, e continua fora de qualquer orcamento feito antes de invocar.

---

## O que aconteceu na tarefa 3, invocacao a invocacao

| # | Turno 1 | Commits | O que saiu | Decisao |
| - | ------- | ------- | ---------- | ------- |
| 3a | 6,4k | 4 | Duas passadas sobre a **mesma lista**: cada arquivo virava duas linhas de log e toda nota passava pelo tratamento de evento. As reflexoes seguintes acrescentaram remendos (`else: resultado = "desconhecido"`, lista branca antes do INSERT) para calar o `CHECK` do banco | **revertido** — aproveitar levaria o passo 4 a revisar remendos |
| 3b | 7,2k | 1 | Desenho **certo**: duas listas separadas, import no topo, ramo morto removido de `_processar_arquivo`. Mas o bloco que criaria `_processar_evento` nao casou, e a funcao nunca existiu (`NameError`) | **aproveitado** — o defeito era a edicao, nao o codigo |
| 3c | 6,2k | **0** | Recebeu a funcao pronta e a ancora do SEARCH indicada. Emitiu o bloco malformado nas tres reflexoes. Nenhuma edicao aplicada | **assumido pelo Claude** |

A funcao `_processar_evento` que esta no repo (commit `4ac77a1`) e minha. Por isso a tarefa 3 e 👤
e nao 🤝: nenhuma linha do modelo local sobreviveu nela.

⭐ **O que salvou a tarefa 3 nao foi a re-especificacao, foi a 3b ter sido aproveitada.** As duas
listas separadas, o import e a limpeza do ramo morto sao do modelo local e estao no codigo final.
Se eu tivesse revertido a 3b junto com a 3a, teria jogado fora trabalho bom.

---

## ⚠️ Ressalva anotada e nao consertada: o registro do script se apaga

`escrever_registro` grava so os `registros` da execucao corrente. Com `--a-partir-de`, isso
**sobrescreve** o arquivo e apaga as tarefas ja registradas. Nesta story o efeito foi concreto: o
registro automatico final dizia "1 de 1 tarefa verde" quando eram 4 de 4, e "1 invocacao" quando
foram 6.

O numero que mais se perde e justamente o do **Achado 11** — contar invocacoes, nao tarefas. Quem
lesse so o arquivo gerado veria 4 tarefas e 4 invocacoes, e a tarefa 3 (tres invocacoes, uma
reversao, uma funcao ditada) sumiria do placar.

⛔ **Nao consertado nesta story**: o `rodar_passo3.py` nao esta no escopo da 005, e mexer nele
durante a medicao mudaria o instrumento no meio da medida. Candidato a primeira tarefa da 006 — ler
o registro existente e mesclar, em vez de sobrescrever.

# Plan — story 009: a cascata determinística

> Como os critérios congelados na [`spec.md`](spec.md) viram três invocações do modelo local, e o
> que a revisão humana tem de olhar depois — **inclusive o que nenhum teste alcança**.

---

## 1. As três tarefas

| # | Função | Alvo | Oráculo |
| - | ------ | ---- | ------- |
| 1 | `buscar_categoria_por_ncm` | `src/nfe_parser/categorizacao.py` (**novo**) | `tests/test_ncm_ancora.py` |
| 2 | `_categoria_do_bucket` + `classificar_produto` | o mesmo arquivo | `tests/test_cascata.py` |
| 3 | `definir_categoria_manual` | o mesmo arquivo | `tests/test_categoria_manual.py` |

⭐ **Por que a tarefa 2 leva duas funções e as outras uma.** `_categoria_do_bucket` é privada, tem
quatro linhas e **só existe para o passo 4 da cascata**. Separá-la numa tarefa própria custaria uma
invocação inteira — os 3,0k de contexto fixo do Aider — para escrever um `SELECT`. E um módulo de
teste só para ela precisaria testar, por fora, uma função que a spec não expõe.

⚠️ **A tarefa 2 é a maior das três, e sabe-se disso desde já.** Ela é a única que tem a ordem de
prioridade inteira. Foi por isso que a tarefa 1 ficou com uma função só: o orçamento da 2 precisa
da folga que a 1 não gasta.

### ⛔ O que deliberadamente NÃO virou tarefa

| | Por quê |
| - | ------- |
| Uma função por passo da cascata | **D2 na spec.** São três passos fixos, sem ponto de extensão externo. A indireção não paga o próprio custo, e um registro no nível do módulo é o gatilho exato do **Achado R** |
| Um `classificar_todos_os_produtos(conexao)` | varrer `produtos` é integração, e integração é a **013** |
| Ler o `ncm` a partir de `itens` | idem — a 009 **recebe** o `ncm` por parâmetro |

---

## 2. O orçamento de contexto

```
turno 1 ≈ 3,0k (Aider) + bytes(alvo)/4 + bytes(teste)/4 + bytes(mensagem)/4
```

`num_ctx` está fixado em **8192** no `.aider.model.settings.yml`; o teto de trabalho é **6k**, e a
folga entre os dois é para os turnos 2 e 3 que o Aider gasta ao ler a saída do `--test-cmd`.

### A estimativa do P1 — com o `bytes(alvo)` ainda por medir

| Tarefa | Aider | alvo | teste | mensagem | **total** |
| ------ | ----- | ---- | ----- | -------- | --------- |
| 1 | 3,00k | **0** (arquivo novo) | ~1,13k (est. 4,5 kB) | 0,87k (3.492 B ✅) | **~5,00k** |
| 2 | 3,00k | ~0,20k (est. 800 B) | ~1,25k (est. 5,0 kB) | 1,28k (5.101 B ✅) | **~5,73k** ⚠️ |
| 3 | 3,00k | ~0,58k (est. 2,3 kB) | ~1,13k (est. 4,5 kB) | 0,91k (3.629 B ✅) | **~5,62k** ⚠️ |

✅ **As três mensagens já estão escritas e medidas** — essa coluna não é estimativa.

> 🔴 **Na 008 o erro da fórmula foi meu, não dela:** estimei mensagens de ~3,0 kB e escrevi de 3,6 a
> 3,9 kB; estimei testes de ~3,0 kB e escrevi de 4,3 a 6,1 kB. Por isso, desta vez, **as mensagens
> foram escritas ANTES do plan** e entram na tabela medidas.

### ✅ O remeço do P2 — feito, e ele **reprovou** a tarefa 2 na primeira conta

📋 **O `bytes(alvo)` saiu de graça do protótipo do Achado S** *(Achado V)*, medido por corte antes
de apagá-lo: `texto.index("def _categoria_do_bucket")` = **445 B**, e
`texto.index("def definir_categoria_manual")` = **1.504 B**. Folga por cima — o protótipo é limpo e o
do modelo local pode não ser — de **+400 B** e **+800 B** (na 008 foram +800 B na última tarefa).

| Tarefa | alvo+folga | teste (1ª conta) | mensagem | **total** | |
| ------ | ---------- | ---------------- | -------- | --------- | - |
| 1 | 0,00k | 1,01k | 0,87k | **4,89k** | ✅ |
| 2 | 0,21k | **1,79k** | 1,28k | **6,18k** | 🔴 **estourou** |
| 3 | 0,58k | 1,39k | 0,91k | **5,78k** | ⚠️ |

🔴 **A tarefa 2 estourou o teto**, e foi o corolário da 008 que a salvou: cortou-se o **docstring do
teste**, ⛔ nunca a mensagem.

⭐ **Mas o corte que mais rendeu não foi de prosa — foi de dado redundante.** `test_cascata.py`
semeava cinco categorias e três âncoras NCM, reencenando a precedência de prefixo que o
`test_ncm_ancora.py` já é dono. Reduzido a **uma âncora**, que casa ou não casa.

⚠️ **E isso melhorou o oráculo, não só o orçamento.** Antes, a mutação M1 (tirar o `ORDER BY`)
deixava **6** testes vermelhos, espalhados pelos dois módulos; depois, deixa **3**, todos no módulo
que é dono daquele risco. ⭐ **Um oráculo em que cada módulo falha pela própria razão diz onde está
o defeito; um que falha em bloco só diz que há um.**

### 📋 A conta final, e a folga agora é por desenho

| Tarefa | alvo+folga | teste | mensagem | **total** | folga até 6k |
| ------ | ---------- | ----- | -------- | --------- | ------------ |
| 1 | 0,00k | 1,01k (4.051 B) | 0,87k | **4,89k** | **+1,11k** |
| 2 | 0,21k | 1,30k (5.202 B) | 1,28k | **5,79k** | **+0,21k** |
| 3 | 0,58k | 1,29k (5.173 B) | 0,91k | **5,78k** | **+0,22k** |

⚠️ Na 008 a tarefa 3 fechou em 5,92k *"passando raspando por acidente, não por desenho"*. Os 0,2k
das duas últimas aqui são pequenos, mas foram **escolhidos**: a primeira conta deu 5,97k e o corte
continuou até haver folga de verdade.

### 🔴 Se o remeço estourar o teto, corte o docstring do TESTE — ⛔ não a mensagem

| | |
| - | - |
| A mensagem | é o que faz a tarefa **convergir**. Cortá-la troca contexto por invocação, e sai caro |
| O docstring do teste | é para quem lê a falha. A explicação longa mora na **spec**, que ⛔ não é enviada ao modelo local |

⭐ Na 008 isso tirou ~2,0 kB de dois módulos e levou a tarefa 3 de **5,92k para 5,71k**, sem perder
uma linha de contrato.

---

## 3. O P2 — os oráculos, e as duas provas

⚠️ **Nenhum módulo passa de 8 testes** *(Achado N)*. Os três ficam em **7, 8 e 6**.

### As fixtures semeiam o próprio dado

`categorias` e `ncm_ancora` estão **vazias** — o seed é a story 010. Toda fixture insere as suas
linhas por SQL direto. ⛔ Nenhum teste pode depender do seed real.

📋 **A taxonomia mínima que os testes usam** (inventada para o teste, ⛔ não é o seed):

| slug | papel |
| ---- | ----- |
| `uncategorized` | o bucket, `is_bucket = 1` |
| `mercado` | pai, para o prefixo NCM de 2 |
| `laticinios` | filho, para o prefixo de 4 |
| `queijo-minas` | neto, para o prefixo de 8 |
| `bebidas` | a categoria **discordante**, usada pelo teste de C3.3 |

### 📋 Metade 1 — provar que o oráculo é **satisfazível** *(Achado S)*

1. escrever uma **implementação de referência** no diretório temporário da sessão;
2. instalá-la no clone, rodar os três módulos novos **e a suíte inteira**;
3. **apagar**, e conferir com `git status` que só os testes ficaram.

⛔ **O protótipo não entra em commit nenhum.** Se entrar, o modelo local recebe a resposta pronta e
a medição do P3 não vale nada.

### 🔴 Metade 2 — provar que o oráculo **morde** *(Achado U)*

Com o protótipo ainda instalado, quebrar de propósito os riscos mais caros e confirmar que **os
testes certos, e só eles**, ficam vermelhos.

✅ **Feito, contra os oráculos finais.** Cinco mutações, 22 testes:

| # | Mutação | Previsto | **Medido** | |
| - | ------- | -------- | ---------- | - |
| **M1** | tirar o `ORDER BY LENGTH(prefixo) DESC` | C1.2, C1.3 | **C1.2, C1.3 e C1.7** — 3 vermelhos | ⚠️ |
| **M2** | tupla protegida vira `("manual",)` | só C2.5 | **só C2.5** | ✅ |
| **M3** | passo 1 vira `if categoria_atual is not None` | só C2.6 | **só C2.6** | ✅ |
| **M4** | tirar o `if not ncm: return None` | só C1.6 | **C1.6[None] e C2.3** | ⚠️ |
| **M5** | o ramo do bucket grava `origem='ncm'` | — | **C2.2 e C2.3** | ➕ |

⭐ **M3 é a mutação que mais importa**, porque é o erro que um humano escreveria sem perceber: "já
tem categoria, então não mexe". Ele prenderia no bucket, para sempre, todo produto que caísse lá
uma vez — e a story 010, que existe para fazer o mapa NCM crescer, não recuperaria nenhum. ✅ O
oráculo o pega, e **só** ele fica vermelho.

#### 📋 Onde a previsão errou, e o que cada erro ensinou

**M1** — previ dois vermelhos e vieram três: **C1.7 também depende do `ORDER BY`**. `"0403"` casa
`0403` e `04`, e sem a ordenação o SQLite pode devolver o pai. ⭐ Errar para **mais** é o lado bom
de errar: o oráculo morde mais do que eu sabia.

**M4** — previ só C1.6 e veio também **C2.3**, porque `classificar_produto(conexao, id, None)`
atravessa a guarda e bate em `None[:8]`. ⭐ É a prova de que a cascata realmente delega a busca em
vez de reimplementá-la.

**M5 não estava no plano** e foi acrescentada ao ver o `CHECK` da coluna: gravar `'ncm'` no ramo do
bucket é o erro mais provável de quem escreve o UPDATE uma vez só. ✅ Pego por C2.2 e C2.3.

### 🔴 Um limite do oráculo, medido e declarado

⚠️ **`C1.6` com `""` NÃO discrimina.** Sob M4, `test_ncm_vazio_devolve_none[None]` fica vermelho e
**`[""]` continua verde** — `""[:8]` é `""`, nenhum prefixo vazio existe no mapa, e a função devolve
`None` com guarda ou sem ela.

⛔ **E não dá para fortalecê-lo honestamente:** só morderia se o mapa tivesse uma linha de prefixo
vazio, que é dado que não existe no mundo. 📋 **Fica registrado como documentação de contrato, não
como guarda** — quem apagar a guarda será pego pelo caso `None`, que é o que de fato quebra.

⭐ É exatamente para isto que o Achado U serve: *um teste que nunca se viu falhar não é guarda, é
decoração* — e agora se sabe **qual** dos 22 é decoração, em vez de supor que nenhum é.

⚠️ **Satisfazível não é correto.** ✅ Protótipo apagado e `git status` conferido: só os três módulos
de teste ficaram, e a suíte voltou ao `ModuleNotFoundError` esperado.

### 🔴 Achado novo do P2 — ⛔ NÃO rode `ruff check --fix` nos testes antes do P3

Formatar os oráculos **antes** de congelá-los é certo — um `ruff format` no P4 mexeria no commit que
é a evidência do que foi congelado. ⚠️ **Mas o `ruff check` reprova três `I001` que são falsos.**

📋 **A causa, medida e não suposta:** o isort do ruff classifica `nfe_parser.categorizacao` como
**terceiro** enquanto o arquivo não existe, e quer movê-lo para junto do `import pytest`. Criado um
`categorizacao.py` vazio, o mesmo comando responde **`All checks passed!`**; apagado, os três erros
voltam.

⛔ **Aplicar o `--fix` embaralharia os imports**, e o P4 — com o módulo já criado pelo modelo local —
os desfaria. Seriam duas mexidas no arquivo congelado, ambas ruído.

📋 **A regra:** `ruff format` antes de congelar, **sim**. `ruff check --fix`, **só no P4**. ⭐ Vale
para toda story que cria um módulo **novo** — ou seja, a 010 (`seed.py`) e a 012 (`eval_llm.py`)
vão bater nisto.

---

## 4. O P3 — a ordem, e onde ele pode parar

```powershell
python scripts\rodar_passo3.py specs\009-cascata-deterministica\tarefas.json --simular
python scripts\rodar_passo3.py specs\009-cascata-deterministica\tarefas.json
```

⭐ O `--simular` custa segundos e valida o manifesto antes de qualquer invocação.

📋 **Onde a convergência pode falhar, por tarefa** — escrito antes, para a triagem não ser improviso:

| Tarefa | O erro provável | Como se reconhece no log |
| ------ | --------------- | ------------------------ |
| 1 | ordenar por `prefixo` em vez de `LENGTH(prefixo)` | C1.2 e C1.3 vermelhos, o resto verde |
| 1 | tratar o comprimento do NCM com `if` em vez de deixar o `IN` absorver repetidos | C1.7 vermelho |
| 2 | 🔴 parar no passo 1 por `categoria_atual is not None` | C2.6 vermelho |
| 2 | gravar a string `"bucket"` na coluna `origem` | `IntegrityError` do `CHECK`, em C2.2 e C2.3 |
| 2 | chamar `_categoria_do_bucket` na entrada da função | C2.8 vermelho num caso que deveria passar |
| 3 | validar `categoria_id` com um `SELECT` a mais | C3.6 vermelho — troca `IntegrityError` por `LookupError` |

⚠️ **Commit do modelo ≠ invocação.** Na 008 a tarefa 1 saiu com dois commits e **uma** invocação.
⛔ Não contar commits como invocações no recibo.

⚠️ **O Achado R não deve disparar** — nenhuma tarefa acrescenta linha a registro no nível do módulo,
e as três mensagens proíbem criar um. ⭐ Se ele disparar mesmo assim, é achado novo e vale registrar.

---

## 5. 🔴 O P4 — e o que nenhum teste alcança

**Ler o código inteiro, não só o diff** *(Achado H)*.

### Os itens que NENHUM teste pega, e que por isso são revisão humana

> ⚠️ Esta lista existe porque o Achado U tem limite declarado: a mutação prova o oráculo **só nos
> riscos que um teste alcança**. Estes quatro não são alcançáveis, e ficam escritos aqui como o
> handoff manda.

| # | O quê | Por que nenhum teste pega |
| - | ----- | ------------------------- |
| 1 | `conexao.commit()` dentro do módulo | a mesma conexão enxerga o que ela mesma não commitou — o teste passa dos dois jeitos |
| 2 | lista/dicionário no nível do módulo (**D2**) | é forma, não comportamento. Os testes passam com registro ou sem |
| 3 | SQL montado por f-string em vez de `?` | com os valores dos testes, os dois funcionam |
| 4 | ⛔ ausência de docstring | **o modelo local não escreve nenhuma** — aconteceu na 005, 006, 007 e 008 |

### 📋 A varredura de NULL *(Achado W)* — rápida, e obrigatória

Para **cada** `WHERE coluna = ?` do módulo novo, perguntar: *"e se esse parâmetro chegar NULL?"*

| Consulta | Parâmetro NULL | Resposta de desenho |
| -------- | -------------- | ------------------- |
| `WHERE prefixo IN (?,?,?)` | `ncm` vazio | **D1** — guarda devolve `None` antes de consultar |
| `WHERE id = ?` (produtos) | `produto_id` vazio | **D5** — `fetchone()` devolve `None` → `LookupError` |
| `WHERE is_bucket = 1` | — | não recebe parâmetro |

⭐ As três já têm resposta **congelada em critério**, e não improvisada no P3. É a lição da 008
aplicada antes do defeito, não depois.

### O resto do P4

```powershell
.\.venv\Scripts\python.exe -m pytest -q --cov=nfe_parser.categorizacao --cov-report=term-missing
.\.venv\Scripts\ruff.exe format --no-cache src\ tests\
.\.venv\Scripts\ruff.exe check --fix --no-cache src\ tests\
```

🔴 **Note o `src\ tests\` — ⛔ NÃO `ruff format .`.** Com o ponto, ele reformata os blocos de código
dentro dos `.md` das tarefas, que são o registro do que foi **enviado** ao modelo local. Em 15/09 ele
alcançou os arquivos da story 006, já publicada.

Cobertura é **diagnóstico sem limiar**: linha nova não-coberta é **código morto** (apagar) ou
**lacuna de teste** (escrever, ou registrar a ressalva). ⭐ E ela **não prova nada** — na 008, 100%
de cobertura não viu a comparação com NULL.

📋 **Teste escrito no P4 vai em módulo NOVO**, nunca dentro dos módulos do P2 — aqueles são a
evidência do que foi congelado antes da implementação. ⭐ E valida-se por mutação, como os outros.

📋 **Contrato acrescentado no P4 entra no §7 da spec**, dizendo que entrou no P4.

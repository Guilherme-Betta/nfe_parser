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

### ⚠️ As tarefas 2 e 3 estão a menos de 0,4k do teto — e o remeço do P2 é obrigatório

📋 **O `bytes(alvo)` sai de graça do protótipo do Achado S** *(Achado V)*. Antes de apagá-lo:

```python
texto.index("def _categoria_do_bucket")     # = bytes(alvo) da tarefa 2
texto.index("def definir_categoria_manual") # = bytes(alvo) da tarefa 3
```

⚠️ **Some folga por cima**, porque o protótipo é limpo e o do modelo local pode não ser. Na 008
foram **+800 B** na última tarefa.

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

| # | Mutação | Vermelho esperado |
| - | ------- | ----------------- |
| **M1** | tirar o `ORDER BY LENGTH(prefixo) DESC` | só os testes de prefixo mais longo (C1.2, C1.3) |
| **M2** | trocar a tupla protegida por `("manual",)` | **só C2.5** |
| **M3** | trocar o passo 1 por `if categoria_atual is not None: return` | **só C2.6** — o produto ficaria preso no bucket |
| **M4** | tirar o `if not ncm: return None` | só C1.6 |

⭐ **M3 é a mutação que mais importa**, porque é o erro que um humano escreveria sem perceber: "já
tem categoria, então não mexe". Ele prenderia no bucket, para sempre, todo produto que caísse lá
uma vez — e a story 010, que existe para fazer o mapa NCM crescer, não recuperaria nenhum.

⚠️ **Satisfazível não é correto.** Um oráculo frouxo passa no Achado S sem reclamar; é a mutação
que o reprova. **Depois apagar o protótipo e conferir o `git status` de novo.**

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

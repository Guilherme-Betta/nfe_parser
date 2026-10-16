# Plan — story 011: edição de taxonomia

> A spec está em [`spec.md`](spec.md). Aqui só o **como**: o que vai para o loop, quanto cabe na
> janela, e o que fazer quando não couber.

---

## 1. O que vai para o loop, e o que ⛔ não vai

| Parte | Onde | Quem escreve |
| ----- | ---- | ------------ |
| migração v3 (`categorias_apagadas`) | `migracoes.py` | ✅ 👤 feito no P1 |
| `_categoria_do_bucket` → `categoria_do_bucket` | `categorizacao.py` | ✅ 👤 feito no P1 *(dívida `i`)* |
| `apagar_categoria` | `taxonomia.py` (novo) | 🤖 **tarefa 1** |
| `mover_categoria` | `taxonomia.py` | 🤖 **tarefa 2** |
| `renomear_categoria` | `taxonomia.py` | 🤖 **tarefa 3** |
| o seed vira *placeholder* | `seed.py` | 👤 **P4** — 🔴 não cabe na janela |

🔴 **Por que a migração e a renomeação vieram ANTES do P2.** A tarefa 1 escreve em
`categorias_apagadas` e chama `categoria_do_bucket`. ⛔ Sem as duas prontas, o oráculo dela ficaria
vermelho pelo motivo errado, e o modelo local passaria a invocação tentando consertar um defeito que
não é dele.

---

## 2. 🔴 São TRÊS tarefas, não duas — e a ordem não é a do recorte

O recorte propunha 2 tarefas: **1.** renomear e mover (o vínculo sobrevive) · **2.** apagar (o
vínculo muda). ⚠️ **As duas mudanças têm a mesma causa, e ela é o orçamento medido.**

⭐ **A regra que decide a ordem:** com `--edit-format whole` cada tarefa recebe o arquivo alvo
**inteiro**, então o alvo só **cresce**. Logo a **mensagem maior tem de vir primeiro**, quando o
alvo ainda é o menor possível.

Mensagens medidas: `apagar` **4.112 B** · `mover` **3.760 B** · `renomear` **2.562 B**.
📋 Daí a ordem: **apagar → mover → renomear**.

| Arranjo testado | Resultado |
| --------------- | --------- |
| 2 tarefas, ordem do recorte | 🔴 tarefa 2 em **103–106%** da janela |
| 2 tarefas, invertida | 🔴 tarefa 2 em **103%** |
| **3 tarefas, mensagem decrescente** | ✅ **99% · 97% · 96%** |

⛔ **Não há perda conceitual:** a divisão do recorte era sobre *o que cada tarefa entrega*, e
continua valendo — `renomear` e `mover` são os casos em que o vínculo sobrevive, `apagar` o único em
que ele muda. O que mudou foi a granularidade.

⚠️ **O custo real da inversão, e vale declarar:** a tarefa **mais difícil** passa a ser a primeira
invocação sobre um arquivo que não existe — o caso em que o modelo local tem menos contexto para se
apoiar. ⚠️ **E o custo das três:** a tarefa 3 tem de devolver **duas** funções anteriores intactas,
em vez de uma *(Achado R)*.

---

## 3. O orçamento — ⭐ agora com TODOS os insumos medidos

> ### `sent ≈ 5,99k + bytes(alvo + teste + mensagem) / 3,7`

⚠️ Tratado como **±5%**, e a constante é a da story **010** — ⛔ ela não é constante entre stories.
Teto: **8.192** (`num_ctx` do `.aider.model.settings.yml`; o `rodar_passo3.py` recusa rodar sem ele).

⚠️ **Os bytes são contados com CRLF**, que é como os arquivos estão no disco e é o que o Aider lê.

| Tarefa | alvo | mensagem | teste | soma | `sent` previsto | folga |
| ------ | ---- | -------- | ----- | ---- | --------------- | ----- |
| 1 `apagar` | 0 | 4.112 | 3.599 | 7.711 | **8.074** (99%) | 118 |
| 2 `mover` | 1.442 | 3.760 | 1.993 | 7.195 | **7.935** (97%) | 257 |
| 3 `renomear` | 2.569 | 2.562 | 1.812 | 6.943 | **7.866** (96%) | 326 |

⭐ **O `alvo` não está estimado: foi MEDIDO no protótipo** *(Achado V)*, cortando o arquivo nos
limites de cada função. O modelo local não escreve docstring (sexta story seguida), então o
protótipo sem docstring é o proxy honesto.

### ⚠️ A tarefa 1 tem 118 tokens de folga, e isso é pouco — mas não é inédito

🔴 Na **010** o Aider enviou **8,1k** numa janela de 8.192 e as duas tarefas fecharam verdes de
primeira. ⭐ É a mesma pressão. ⛔ Não é conforto: é precedente.

📋 **Depois da PRIMEIRA invocação, leia o `Tokens: sent` do log e recalibre a constante** antes de
rodar a tarefa 2 — na 010 ela ficou estável a três tokens **dentro** da story.

⛔ **Se a tarefa 1 truncar**, o remédio já está escolhido, e ⛔ não é encurtar a mensagem (é ela que
evita o modo de falha do Achado R): **tire do módulo de teste os casos C3.6, C3.7 e C3.9** — as três
recusas — para um segundo módulo, rodado no P4 fora do loop. Isso devolve ~900 B, ou ~240 tokens.

---

## 4. P1 — o que foi feito

✅ `spec.md` com D1–D12 e os aceites C1–C4 · as três mensagens · `tarefas.json` · a migração v3 · a
dívida `i` paga.

🛑 **A parada de produto do P1 já aconteceu**, e a resposta do Gui está citada na §2 da spec. ⭐ Ela
ampliou a story: o seed passa a ser *placeholder*, e isso não estava no recorte.

---

## 5. P2 — os oráculos

Um módulo por tarefa *(Achado F)*, **8 testes cada** *(Achado N)*:

| Tarefa | Módulo | Casos |
| ------ | ------ | ----- |
| 1 | `tests/test_taxonomia_apagar.py` | C3.1 – C3.9 |
| 2 | `tests/test_taxonomia_mover.py` | C2.1 – C2.7 |
| 3 | `tests/test_taxonomia_renomear.py` | C1.1 – C1.5 |

✅ **Vermelho certo confirmado:** `ModuleNotFoundError: No module named 'nfe_parser.taxonomia'` —
⛔ não `No module named pytest`.

✅ **Metade 1, satisfazível** *(Achado S)*: protótipo de referência → **20 testes novos verdes** e a
suíte inteira em **316** → medido → apagado → `git status` confirmou que só os testes ficaram.

### 🔴 Metade 2 — sete mutações, e a previsão acertou nas sete

📋 As previsões foram escritas e **commitadas antes** de rodar (commit do P1).

| # | Mutação | Previsão | O que aconteceu |
| - | ------- | -------- | --------------- |
| M1 | apagar a categoria antes de mover produtos/âncoras | `IntegrityError` em vários | ✅ 5 acenderam |
| M2 | ⭐ não zerar a `origem` no passo 4 | **só** C3.2 | ✅ exatamente C3.2 |
| M3 | ⭐ subida vira teste de **um nível só** | C2.7 sim, C2.6 não | ✅ `[meio]` e `[folha]` sim, `[raiz]` não |
| M4 | `renomear` escrever também o `slug` | "acende?" — dúvida declarada | ✅ acende (2 testes) |
| M5 | tirar a guarda do bucket | C3.7 | ✅ exatamente C3.7 |
| M6 | 🔴 lápide com `INSERT` seco | provável **buraco de cenário** | 🔴 **não acendeu nada** |
| M7 | apagar não remover as âncoras | *(acrescentada na hora)* | 5 acenderam — a FK é real |

### ⭐ A M6, e o Achado AC aplicado sem tropeço

⛔ A mutação não acendeu **nada**. 📋 **A pergunta certa, pelo Achado AC, é "falta cenário?" antes de
"o contrato é indemonstrável?"** — e aqui faltava mesmo: nenhum teste apagava o **mesmo slug duas
vezes**.

⭐ **E o cenário não é artificial: é a própria história da ressurreição** que abriu esta story — a
categoria é apagada, volta por um seed antigo, e é apagada de novo. Virou o caso **C3.9**, e com ele
a M6 passou a acender exatamente um teste.

⚠️ Para não passar de 8 testes *(Achado N)*, C3.4 e C3.5 foram fundidos num teste só — são dois
efeitos da mesma ação.

---

## 6. P3 — um comando só

```powershell
python scripts\rodar_passo3.py specs\011-edicao-taxonomia\tarefas.json --simular
python scripts\rodar_passo3.py specs\011-edicao-taxonomia\tarefas.json --edit-format whole
```

⚠️ `--simular` ⛔ **não** estima tokens — só imprime o comando. O `sent` só existe depois de invocar.

🔴 **O risco próprio das tarefas 2 e 3:** o `whole` reescreve o arquivo inteiro, então elas podem
devolver `taxonomia.py` **sem** as funções anteriores. ⭐ As duas mensagens abrem dizendo, com todas
as letras, quais funções não se alteram e que têm de voltar completas — é o Achado R, que funcionou
nas três últimas stories. ⚠️ A tarefa 3 é a mais exposta: são **duas** funções a preservar.

⚠️ **Commit do modelo ≠ invocação.** Preencha a coluna "Quem resolveu" à mão — 🤖 · 👤 · 🤝
*(Achado M)*.

---

## 7. P4 — e aqui mora a metade que não foi ao loop

⭐ **Leia o código inteiro, não só o diff** *(Achado H)* — achou defeito nas quatro últimas stories.

🔴 **E só depois disso escreva a mudança do `seed.py`**, que é o que faz a story valer:

1. `carregar_categorias`: `ON CONFLICT(slug) DO NOTHING`, e pular slug que esteja na lápide.
2. A segunda passada (`parent_id`) só liga o pai das categorias **recém-inseridas** — ⛔ hoje ela
   sobrescreve sempre, e é ela que desfaz o "mover".
3. `carregar_ncm_ancora`: pular âncora cujo slug está na lápide; ⛔ continuar levantando para slug
   simplesmente ausente *(D9)*.
4. Um módulo novo, `tests/test_seed_respeita_edicao.py`, com os casos **C4.1 – C4.7**.

```powershell
.\.venv\Scripts\python.exe -m pytest -q --cov=nfe_parser.taxonomia --cov=nfe_parser.seed --cov-report=term-missing
.\.venv\Scripts\ruff.exe format --no-cache src\ tests\
.\.venv\Scripts\ruff.exe check --fix --no-cache src\ tests\
```

🔴 **Note o `src\ tests\` — ⛔ NÃO `ruff format .`**, que reformataria os blocos de código dentro dos
`.md` das tarefas, e eles são o registro do que foi **enviado** ao modelo.

⚠️ `ruff check --fix` só no P4 *(Achado Y)*: enquanto `taxonomia.py` não existir, o isort o
classifica como terceiro e acusa `I001` falso.

⚠️ O modelo local ⛔ não escreve docstring nenhuma. Sétima story seguida — as docstrings do
`taxonomia.py` são trabalho do P4.

📋 Contrato acrescentado no P4 entra na **§7 da spec**, dizendo que entrou no P4.

---

## 8. O que pode dar errado

| Sintoma | O que é | Remédio |
| ------- | ------- | ------- |
| `Tokens: sent` acima de 8.192 na tarefa 1 | orçamento | ⭐ **tirar C3.6, C3.7 e C3.9 para um segundo módulo** — §3 |
| tarefa 2 ou 3 devolve o arquivo sem as funções anteriores | `whole` | reverter e repetir citando as funções pelo nome *(Achado R)* |
| código errado, remendos defensivos | raciocínio | **reverter** e nomear UM defeito |
| desenho certo, bloco de edição não casou | aplicação | **aproveitar** e pedir só o que falta *(Achado T)* |
| `IntegrityError` nos testes de `apagar` | ordem dos passos | é a M1; o remédio é a REGRA 1 da mensagem |

🔴 **E um risco que não é do loop:** a mudança do `seed.py` mexe em código **já publicado no
`origin`**. ⛔ O recorte previa que só a 013 faria isso. A suíte inteira tem de fechar verde antes da
transferência — `test_seed_categorias.py` e `test_seed_ncm.py` da 010 são os que mais provavelmente
vão acusar, e ⚠️ se algum acusar, a pergunta certa é *"este teste afirmava a D4 antiga?"*, ⛔ não
*"como faço ele passar?"*.

⭐ **Este risco já se materializou uma vez nesta story, no P1:** `test_migracao_itens.py` afirmava o
literal `== 2` e a migração v3 o derrubou. A docstring dele **declarava** a premissa ("última tarefa
que mexe na versão do banco"), e foi ela que tornou a decisão fácil.

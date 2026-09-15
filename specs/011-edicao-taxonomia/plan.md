# Plan — story 011: edição de taxonomia

> A spec está em [`spec.md`](spec.md). Aqui só o **como**: o que vai para o loop, quanto cabe na
> janela, e o que fazer quando não couber.

---

## 1. O que vai para o loop, e o que ⛔ não vai

| Parte | Onde | Quem escreve |
| ----- | ---- | ------------ |
| migração v3 (`categorias_apagadas`) | `migracoes.py` | 👤 **antes** do P2 |
| `_categoria_do_bucket` → `categoria_do_bucket` | `categorizacao.py` | 👤 **antes** do P2 *(dívida `i`)* |
| `apagar_categoria` | `taxonomia.py` (novo) | 🤖 **tarefa 1** |
| `renomear_categoria` + `mover_categoria` | `taxonomia.py` | 🤖 **tarefa 2** |
| o seed vira *placeholder* | `seed.py` | 👤 **P4** — 🔴 não cabe na janela |

🔴 **Por que a migração e a renomeação vêm ANTES do P2, e não no P4.** A tarefa 1 escreve na tabela
`categorias_apagadas` e chama `categoria_do_bucket`. ⛔ Se as duas não existirem, o oráculo da
tarefa 1 fica vermelho pelo motivo errado, e o modelo local passaria a invocação inteira tentando
consertar um defeito que não é dele.

---

## 2. 🔴 A ordem das duas tarefas está INVERTIDA em relação ao recorte, e a razão é o orçamento

O recorte propunha: **1.** renomear e mover (o vínculo sobrevive) · **2.** apagar (o vínculo muda).
⭐ A divisão continua exatamente essa. O que mudou foi **qual das duas vai primeiro**.

⚠️ Com `--edit-format whole`, a tarefa 2 recebe o arquivo alvo **inteiro** — ou seja, o código que a
tarefa 1 escreveu. Então a segunda tarefa é sempre a mais cara, e a mensagem **maior** tem de cair
sobre o alvo **vazio**.

| Ordem | Tarefa 1 | Tarefa 2 |
| ----- | -------- | -------- |
| a do recorte (renomear/mover → apagar) | ~95% da janela | 🔴 **~101%** — estoura |
| **invertida (apagar → renomear/mover)** | ~95% | ~98% |

⛔ **Não há perda conceitual na inversão.** A divisão do recorte é sobre *o que cada tarefa entrega*,
e isso não mudou. ⚠️ O custo real é outro, e vale declarar: a tarefa **mais difícil** passa a ser a
primeira invocação sobre um arquivo que não existe, que é o caso em que o modelo local tem menos
contexto para se apoiar.

---

## 3. O orçamento, calibrado pelo Achado AA

> ### `sent ≈ 5,99k + bytes(alvo + teste + mensagem) / 3,7`

⚠️ Tratado como **±5%**, e a constante é a da story **010** — ⛔ ela não é constante entre stories
(andou 340 tokens em um dia). Teto da janela: **8.192** (`num_ctx` fixado no
`.aider.model.settings.yml`; o `rodar_passo3.py` recusa rodar sem ele).

⭐ Isso dá **~8.147 bytes** somados de alvo + teste + mensagem.

| | Tarefa 1 (`apagar`) | Tarefa 2 (`renomear` + `mover`) |
| - | ------------------- | ------------------------------- |
| alvo | **0** — arquivo novo | ⚠️ o que a tarefa 1 escreveu (~1,5k estimado) |
| mensagem | **4.443** ✅ medido | **4.311** ✅ medido |
| ⭐ **sobra para o teste** | **~3.700 B** | 🔴 **~2.300 B** |

### 🔴 O risco desta story é o orçamento, e ele tem remédio planejado

📋 **Depois da PRIMEIRA invocação, leia o `Tokens: sent` do log do Aider e recalibre a constante**
antes de rodar a tarefa 2. ⭐ É o procedimento do Achado AA, e na 010 a constante ficou estável a
três tokens **dentro** da story.

⛔ **Se a tarefa 2 não couber**, o remédio já está escolhido, e ⛔ não é encurtar a mensagem (é ela
que evita o modo de falha do Achado R): **corte o módulo de teste em dois**. A metade que fica
prova o contrato da tarefa; a outra metade vira teste de regressão rodado no P4, fora do loop.

⚠️ **Nenhum módulo de teste passa de 8 testes** *(Achado N)*. Os dois já estão desenhados com 8.

---

## 4. P1 — o que já está feito

✅ `spec.md` com D1–D12 e os aceites C1–C4.
✅ As duas mensagens, escritas **antes** deste plan — é o que faz o orçamento entrar medido.
✅ `tarefas.json`.

🛑 **A parada de produto do P1 já aconteceu.** A pergunta da ressurreição foi ao Gui, e a resposta
dele está citada na §2 da spec. ⭐ Ela ampliou a story: o seed passa a ser *placeholder*, e isso não
estava no recorte.

---

## 5. P2 — os oráculos

Um módulo de teste por tarefa *(Achado F)*:

| Tarefa | Módulo | Casos |
| ------ | ------ | ----- |
| 1 | `tests/test_taxonomia_apagar.py` | C3.1 – C3.8 |
| 2 | `tests/test_taxonomia_editar.py` | C1.1 – C1.5 e C2.1 – C2.7, comprimidos em 8 testes |

⛔ Confirme o **vermelho certo**: `ModuleNotFoundError: nfe_parser.taxonomia` — ⛔ **não**
`No module named pytest`.

⭐ Os testes montam a própria taxonomia mínima com `INSERT` direto *(spec §5)*. ⛔ Nenhum deles chama
`carregar_seed_padrao`: amarrar o oráculo às 44 categorias reais faria o Gui quebrar a suíte ao
curar o dado.

### 📋 Metade 1 — satisfazível *(Achado S)*

Implementação de referência no diretório temporário da sessão → instalar → rodar os dois módulos
novos **e a suíte inteira** → apagar → `git status` para confirmar que só os testes ficaram.
⛔ O protótipo não entra em commit nenhum.

🔴 **Meça o `bytes(alvo)` do protótipo da tarefa 1 antes de apagá-lo** *(Achado V)*. É o número que
falta para fechar o orçamento da tarefa 2 — hoje ele está **estimado**, e é o único estimado.

### 🔴 Metade 2 — mordente *(Achado U)*

📋 **Escreva a previsão ANTES de rodar.** As mutações candidatas, e o que cada uma põe à prova:

| # | Mutação | Previsão |
| - | ------- | -------- |
| M1 | trocar a ordem dos passos 4/5 e 7 de `apagar` (apagar a categoria primeiro) | `IntegrityError` em vários testes |
| M2 | ⭐ **não zerar a `origem` no passo 4** (só trocar `categoria_id`) | só C3.2 acende — é o ponto mais fino da D7 |
| M3 | ⭐ trocar o `while` da subida por um teste de **um nível só** (`parent_id == categoria_id`) | C2.7 acende, C2.6 **não** |
| M4 | `renomear_categoria` escrever também o `slug` | ⚠️ acende? Se nenhum teste olhar o slug depois de renomear, é buraco de oráculo |
| M5 | tirar a guarda do bucket (D5) | C3.7 acende |
| M6 | trocar `ON CONFLICT DO NOTHING` da lápide por `INSERT` seco | ⚠️ só acende se algum teste apagar duas vezes o mesmo slug — provavelmente **buraco de cenário** |

⭐ **Quando uma mutação não acender nada, pergunte primeiro se falta CENÁRIO** *(Achado AC)*, antes
de concluir que o contrato é indemonstrável *(Achado Z)*. A M6 já está marcada como candidata.

---

## 6. P3 — um comando só

```powershell
python scripts\rodar_passo3.py specs\011-edicao-taxonomia\tarefas.json --simular
python scripts\rodar_passo3.py specs\011-edicao-taxonomia\tarefas.json --edit-format whole
```

⚠️ `--simular` ⛔ **não** estima tokens — só imprime o comando. O `sent` só existe depois de invocar.

🔴 **O risco próprio da tarefa 2:** o `whole` reescreve o arquivo inteiro, então ela pode devolver
`taxonomia.py` **sem** `apagar_categoria`. ⭐ A mensagem já abre dizendo, com todas as letras, que a
função existente não se altera e tem de voltar completa — é o Achado R, que funcionou nas três
últimas stories.

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
| `Tokens: sent` acima de 8.192 na tarefa 2 | orçamento | ⭐ **cortar o módulo de teste em dois** — §3 |
| tarefa 2 devolve o arquivo sem `apagar_categoria` | `whole` | reverter e repetir citando a função pelo nome *(Achado R)* |
| código errado, remendos defensivos | raciocínio | **reverter** e nomear UM defeito |
| desenho certo, bloco de edição não casou | aplicação | **aproveitar** e pedir só o que falta *(Achado T)* |
| `IntegrityError` nos testes de `apagar` | ordem dos passos | é a M1; o remédio é a REGRA 1 da mensagem |

🔴 **E um risco que não é do loop:** a mudança do `seed.py` mexe em código **já publicado no
`origin`**. ⛔ O recorte previa que só a 013 faria isso. A suíte inteira tem de fechar verde antes da
transferência — os módulos `test_seed_categorias.py` e `test_seed_ncm.py` da 010 são os que mais
provavelmente vão acusar, e ⚠️ se algum deles acusar, a pergunta certa é *"este teste afirmava a D4
antiga?"*, ⛔ não *"como faço ele passar?"*.

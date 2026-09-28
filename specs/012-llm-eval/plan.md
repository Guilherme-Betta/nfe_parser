# Plan — story 012: LLM opt-in e o harness de eval

> ⭐ A última story do recorte da spec 02, e a única cuja definição de pronto ⛔ não cabe inteira no
> kit: suíte verde **mais** a decisão do Gui sobre os números.

---

## 1. O que vai para o loop, e o que ⛔ não vai

| | |
| - | - |
| **Vai ao modelo local** | as quatro tarefas: `llm.py`, o degrau, a varredura, o harness |
| **⛔ Fica fora** | as docstrings — o modelo local não escreve nenhuma. Entram no P4 |
| **⛔ Fica fora** | a correção da docstring de `categorizacao.py` que promete "uma linha de diff" *(spec §2)* — é documentação, no P4 |
| **⛔ Fica fora** | o script que roda o eval de verdade, e o gold em CSV — ver §7 |

---

## 2. 🔴 São QUATRO tarefas, não três — e o degrau mudou de arquivo

📋 O recorte previa **3** tarefas, com alvo `eval_llm.py` + `categorizacao.py`. ⛔ O degrau não cabe
em `categorizacao.py`: com `--edit-format whole`, a "linha de diff" que a docstring da 009 prometia
custa o arquivo inteiro na ida **e** na volta, e a soma dá **~9,6k contra 8.192**. O argumento
completo está na §2 da spec.

⭐ **O degrau nasce em `classificacao_llm.py`, por composição:** chama a cascata da 009 intacta e só
pergunta ao LLM se a `origem` continuou NULL.

🔴 **E a varredura vira tarefa própria.** O handoff dizia que ela "herdaria o degrau de graça", e
herdaria — **se** o degrau morasse em `classificar_produto`. Morando ao lado, ela precisa trocar uma
chamada e ganhar um parâmetro.

| # | Alvo | O que entrega |
| - | ---- | ------------- |
| 1 | `llm.py` 🆕 | prompt, contrato da resposta, `POST` no Ollama, `llm_do_ambiente` |
| 2 | `classificacao_llm.py` 🆕 | `classificar_produto_com_llm(conexao, produto_id, ncm, llm=None)` |
| 3 | `varredura.py` | `classificar_produtos_pendentes(conexao, llm=None)` |
| 4 | `eval_llm.py` 🆕 | `carregar_gold`, `prever`, `avaliar` |

### A ordem

⭐ A 3 depende da 2 (importa `classificar_produto_com_llm`). A 1 e a 4 são independentes de tudo.
⚠️ **A 2 ⛔ não depende da 1:** o `llm` é um parâmetro, e o oráculo passa uma função Python.

---

## 3. O orçamento — MEDIDO

> `sent ≈ 0,66k + bytes(alvo + teste + mensagem) / 3,4` · janela `num_ctx: 8192`

⭐ Os testes existem (P2 fechado) e a saída é o tamanho do protótipo *(Achado V)*.

| # | alvo | mensagem | teste | soma | `sent` | saída | **total vs. 8.192** |
| - | ---- | -------- | ----- | ---- | ------ | ----- | ------------------- |
| 1 | 0 🆕 | 4.168 | 5.123 | 9.291 | ~3,39k | 2.326 B → ~0,68k | **~4,1k** ✅ |
| 2 | 0 🆕 | 3.622 | 6.213 | 9.835 | ~3,55k | 1.192 B → ~0,35k | **~3,9k** ✅ |
| 3 | 4.015 | 1.761 | 4.021 | 9.797 | ~3,54k | 3.971 B → ~1,17k | **~4,7k** ✅ |
| 4 | 0 🆕 | 3.799 | 4.545 | 8.344 | ~3,11k | 1.971 B → ~0,58k | **~3,7k** ✅ |

⭐ **A story mais folgada do recorte.** Três dos quatro alvos são arquivos novos, e o quarto tem 4 KB.
🔴 **Para comparação, o plano do recorte** (degrau dentro de `categorizacao.py`) daria ~9,6k — ⛔ a
única tarefa do recorte inteiro que não caberia.

### ⚠️ O Achado AD

As mensagens 2 e 3 mandam uma linha de `import` com caminho de **módulo** (`nfe_parser.categorizacao`,
`nfe_parser.classificacao_llm`), ⛔ nunca nome de arquivo. 📋 Conferir no log: exatamente **dois**
`Added ... to the chat`. ⚠️ A mensagem 3 cita `src/nfe_parser/varredura.py`, que **é** o alvo.

---

## 4. P1 — o que foi feito

1. 🛑 **A parada de produto, a única prevista:** o gold. O Gui não tinha, rotulou **19 produtos** na
   hora, a partir das notas dele. Salvo em `AI_Scrum_Workflow/plan/gold-012.md` — repositório
   **privado**; ⛔ não entra neste.
2. Pré-voo verde: ramo `scrum`, árvore limpa, sem remotes, **354 testes**, `qwen2.5-coder:14b`.
3. 🔴 **Achado que o degrau não cabe em `categorizacao.py`** — spec §2.
4. ⭐ As quatro mensagens escritas **antes** do plan.

---

## 5. P2 — os oráculos

Quatro módulos novos, **27 testes**, um por tarefa *(Achado F)*. Nenhum passa de 8 *(Achado N)* —
⚠️ os dois `parametrize` do rascunho viraram laço, porque cada caso contaria como teste.

🔴 **O vermelho certo:** `ModuleNotFoundError` nos três módulos de arquivo novo, e `TypeError`
(*unexpected keyword argument `llm`*) nos três testes da varredura. ⛔ Nenhum `No module named pytest`.

### 📋 Metade 1 — satisfazível *(Achado S)*

Protótipo no scratchpad → instalado por script → **27 passed** nos módulos novos e **381 passed** na
suíte inteira (354 + 27), ⛔ zero regressão → restaurado num `finally` → `git status` só com os
oráculos e a spec.

### 🔴 Metade 2 — mordente *(Achado U)*

📋 **A previsão foi escrita no próprio script, antes de rodar**, e a comparação é de **conjunto
exato**: acender a mais também reprova. **Quinze mutações, quinze bateram.**

| M | Mutação | Previsto | |
| - | ------- | -------- | - |
| M1 | tira a guarda de `bool` | C1.5 | ✅ |
| M2 | limiar com `<=` | C1.4 | ✅ |
| M3 | não confere a lista | C1.2, C1.3 | ✅ |
| M4 | limiar padrão `"0"` quando falta | C1.8 | ✅ |
| M5 | sem `"format": "json"` | C1.7 | ✅ |
| M6 | degrau chama o LLM com a `origem` resolvida | C2.2, C2.3, **C3.2** | ✅ |
| M7 | degrau aceita o slug do bucket | C2.6 | ✅ |
| M8 | degrau não grava a `confianca` | C2.4 | ✅ |
| M9 | slugs sem `ORDER BY` | C2.7 | ✅ |
| M10 | degrau commita | C2.8 | ✅ |
| M11 | varredura não passa o `llm` | **só** C3.1 — ⚠️ C3.2 e C3.3 **verdes** | ✅ |
| M12 | eval conta as linhas fora da taxonomia | C4.3, C4.5, C4.6, C4.7, C4.8 | ✅ |
| M13 | eval põe `None` na matriz | C4.5 | ✅ |
| M14 | gold lido sem tolerar BOM | C4.1 | ✅ |
| M15 | `prever` guarda a tupla | C4.2 | ✅ |

⭐ **A M11 é a M3 da 013 de novo — Achado AG, previsto e confirmado.** C3.2 e C3.3 afirmam o que
acontece **quando o LLM não muda nada** — e uma varredura que ignora o parâmetro satisfaz as duas. 🔴
**Só a C3.1 prova que o `llm` chega ao degrau**; sem ela, as outras duas seriam ocas.

## 6. P3 — um comando só

*(a preencher depois da rodada)*

## 7. O que entra FORA do loop, no P4

| | Por quê fora |
| - | ------------ |
| as docstrings | o modelo local não escreve nenhuma |
| a docstring de `classificar_produto` | promete "uma linha de diff" que a §2 da spec desmentiu |
| `scripts/rodar_eval.py` | cola entre as quatro peças e um Ollama de verdade; ⛔ não há oráculo possível sem serviço rodando |
| o gold em CSV | dado pessoal: mora no repositório privado do workflow |

## 8. O que pode dar errado

| Risco | Onde | Remédio |
| ----- | ---- | ------- |
| 🔴 **R1** — oráculo publicado fechando o conjunto de `origem` | tarefa 3 | ⭐ a 013 não fechou; o `verify.py` entre as tarefas confirma |
| **Achado AD** | tarefas 2 e 3 | caminho de módulo, ⛔ nunca nome de arquivo; conferir os `Added` |
| `whole` apagando docstring publicada | tarefa 3 | *(Achado R)* a mensagem diz que as duas docstrings voltam palavra por palavra |
| o modelo "melhorar" o código copiado | tarefas 1 e 2 | as mensagens dizem *"copie EXATAMENTE"*; a revisão do P4 lê o arquivo inteiro |

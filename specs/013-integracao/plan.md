# Plan — story 013: integração

> ⭐ O orçamento desta story é o primeiro escrito contra a **fórmula medida na 011**
> (`sent ≈ 0,66k + bytes/3,4`), e ⛔ não contra a antiga, que errava 36% para baixo.

---

## 1. O que vai para o loop, e o que ⛔ não vai

| | |
| - | - |
| **Vai ao modelo local** | as quatro tarefas: identidade no item, categoria no JSON, diagnóstico honesto na importação, varredura |
| **⛔ Fica fora** | a alteração de `test_itens_no_json.py` *(D12)* — é **oráculo publicado**, e quem o altera é o P2 desta sessão, à mão |
| **⛔ Fica fora** | as docstrings: o modelo local não escreve nenhuma, sétima story seguida. Entram no P4 |

---

## 2. 🔴 São QUATRO tarefas, não duas — e uma delas nem estava no recorte

📋 O recorte previa **2** tarefas (`persistencia.py`, `serializacao.py`), com o `importador.py` como
terceira *"se a importação precisar mudar"*. Precisou: a dívida `c` é a mais séria da lista e ⛔ não é
opcional.

🔴 **E a quarta tarefa mudou de arquivo durante o P1.** O recorte e o handoff punham
`classificar_produtos_pendentes` dentro de `categorizacao.py`. ⛔ Não cabe: a última linha do
cabeçalho daquele módulo, escrita na 009, diz *"este módulo não lê `itens`"* — e a varredura **tem**
de ler `itens`, porque é de lá que vem o NCM. A §2 da spec tem o argumento inteiro.

⭐ **A varredura nasce em `src/nfe_parser/varredura.py`**, arquivo novo.

| # | Alvo | O que entrega | Dívidas |
| - | ---- | ------------- | ------- |
| 1 | `persistencia.py` | resolve identidade, grava `itens.produto_id`, para de commitar | **a**, **g** |
| 2 | `serializacao.py` | `categoria_slug` e `categoria` no item, por `LEFT JOIN` | — |
| 3 | `importador.py` | o `try` cobre só a extração; o lote commita uma vez no fim | **c**, **d** |
| 4 | `varredura.py` 🆕 | `classificar_produtos_pendentes(conexao) -> int` | **h** |

### A ordem, e por que ela é esta

⭐ *(Achado AE)* — com `whole` o alvo só cresce, então a mensagem maior vai sobre o alvo menor.
⚠️ Aqui **cada tarefa tem alvo próprio**, então a regra quase não morde. O que decide a ordem é outra
coisa:

🔴 **A tarefa 1 vem antes da 3 por causa do oráculo.** O C3.3 afirma que `importar` commita o lote.
Enquanto `persistir_nota` ainda commitar, esse teste passa **por acidente** — e só depois da tarefa 1
ele está afirmando o que diz afirmar.

---

## 3. O orçamento — com a régua medida na 011

> `sent ≈ 0,66k + bytes(alvo + teste + mensagem) / 3,4` · janela `num_ctx: 8192`

⚠️ **O tamanho dos testes é estimativa** até o P2 fechar (5.000 B por módulo, contra 1.8k–5.6k dos
módulos já publicados). 📋 A linha fica conferida com o primeiro `Tokens: sent` real.

| # | alvo | mensagem | teste (est.) | soma | **`sent` previsto** | folga p/ saída |
| - | ---- | -------- | ------------ | ---- | ------------------- | -------------- |
| 1 | 2.475 | 4.341 | ~5.000 | 11.816 | **~4,1k** | ~4,1k |
| 2 | 5.395 | 3.970 | ~5.000 | 14.365 | **~4,9k** | ~3,3k |
| 3 | 5.975 | 5.401 | ~5.000 | 16.376 | **~5,5k** | ~2,7k |
| 4 | 0 🆕 | 4.571 | ~5.000 | 9.571 | **~3,5k** | ~4,7k |

⭐ **As quatro cabem com folga larga.** Contra a fórmula antiga (teto ~8.100 B de insumo), **três das
quatro seriam declaradas impossíveis** — e a 013 teria sido reorganizada contra uma régua errada, que
foi exatamente o erro que custou boa parte do P1 da 011.

### ⚠️ O risco que o orçamento não mostra: o Achado AD pode morder nas tarefas 1 e 4

🔴 As mensagens 1 e 4 precisam mandar uma linha de `import`, e nela aparece um **nome de módulo do
projeto**. Pelo Achado AD, o Aider pode resolver esse nome contra o repositório e **adicionar o
arquivo à conversa sozinho**, com `--yes-always`.

| # | módulo que pode ser puxado | bytes | soma com ele | `sent` |
| - | -------------------------- | ----- | ------------ | ------ |
| 1 | `produtos.py` | 8.356 | 20.172 | **~6,6k** |
| 4 | `categorizacao.py` | 9.817 | 19.388 | **~6,4k** |

⚠️ **As duas continuam cabendo** — é isso que a régua nova compra. ⛔ Mas o arquivo puxado entra
**editável**, e o modelo poderia reescrevê-lo. 📋 Remédio nas duas mensagens, com todas as letras:
*"se qualquer outro arquivo aparecer nesta conversa, DEIXE-O EXATAMENTE COMO ESTÁ"*, e `git diff`
conferido **entre as tarefas**.

### ⚠️ A tarefa 3 é a mais apertada, e tem plano B

A saída dela é o `importador.py` inteiro reescrito — ~6.200 B, ~1,8k tokens de saída sobre ~5,5k de
entrada. 📋 A mensagem já foi enxugada de 6.373 para 5.401 bytes por causa disso.

⛔ **Se ela falhar com `did not conform to the edit format` e `sent` alto**, o plano B é tirar a
dívida **d** da tarefa: ela é a única opcional das quatro *(§288 do recorte: "pague se já estiver com
o arquivo aberto")*, e sai levando as Mudanças 1, 3 e 4(a)(b) junto — a mensagem cairia para ~2.500 B
e a saída encolheria.

---

## 4. P1 — o que foi feito

1. Pré-voo verde: ramo `scrum`, árvore limpa, sem remotes, **324 testes**, `qwen2.5-coder:14b`.
2. Lidos: o §154 e o §213 do recorte, e os cinco módulos que a story toca ou chama.
3. 🔴 **Achada a incompatibilidade da varredura com `categorizacao.py`** — ver §2.
4. 🔴 **Achada a dívida `k`**: `aplicar_cancelamento` também chama `commit()`, e ⛔ não estava anotada
   em lugar nenhum. ⛔ Não vence aqui — seria um quinto alvo. Fica na §7 da spec.
5. ⭐ **As quatro mensagens escritas ANTES do plan**, que é o que faz o orçamento entrar medido.

### 🛑 Paradas de produto: **nenhuma**

⚠️ O handoff previa nenhuma, e o P1 não encontrou nenhuma. As quatro decisões que mais pesaram
(**D1**, **D2**, **D5**, **D8**) são todas de desenho, e nenhuma é do PO.

---

## 5. P2 — os oráculos

*(preenchido no P2)*

## 6. P3 — um comando só

*(preenchido no P3)*

## 7. P4 — revisão, cobertura, estilo

*(preenchido no P4)*

## 8. O que pode dar errado

| Risco | Onde | Remédio |
| ----- | ---- | ------- |
| 🔴 **R1** — oráculo que fecha o conjunto de `origem` | tarefas 1 e 4 | ⛔ nenhum teste asserta `origem in {...}`; a varredura compara só com `is not None` |
| 🔴 **R2** — `test_itens_no_json.py` afirma as chaves do item com igualdade estrita | tarefa 2 | alterado à mão no P2, declarado na **D12**, ⛔ nunca descoberto no P3 |
| **Achado AD** — nome de módulo na mensagem puxa o arquivo | tarefas 1 e 4 | cabe no orçamento; `git diff` entre as tarefas |
| **Regressão** na suíte inteira | tarefas 1, 2 e 3 | 🔴 `verify.py` à mão **entre** as tarefas — o `rodar_passo3.py` só roda o módulo da tarefa |
| `whole` apagando docstring publicada | tarefas 2 e 3 | *(Achado R)* a mensagem diz quais voltam inteiras; `git diff` confere |
| Tarefa 3 estourar a janela | tarefa 3 | plano B da §3: tirar a dívida **d** |

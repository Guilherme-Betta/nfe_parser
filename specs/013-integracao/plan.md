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

⭐ **A tabela abaixo está MEDIDA**: os testes existem (P2 fechado) e o tamanho da saída é o do
protótipo *(Achado V)*. ⛔ Nada aqui é estimativa, exceto a própria fórmula.

| # | alvo | mensagem | teste | soma | `sent` | saída | **total vs. 8.192** |
| - | ---- | -------- | ----- | ---- | ------ | ----- | ------------------- |
| 1 | 2.475 | 4.341 | 6.963 | 13.779 | ~4,71k | 2.883 B → ~0,85k | **~5,6k** ✅ |
| 2 | 5.395 | 3.970 | 6.363 | 15.728 | ~5,29k | 5.714 B → ~1,68k | **~7,0k** ✅ |
| 3 | 5.975 | 5.401 | 6.131 | 17.507 | ~5,81k | 6.088 B → ~1,79k | **~7,6k** ⚠️ |
| 4 | 0 🆕 | 4.571 | 7.361 | 11.932 | ~4,17k | 751 B → ~0,22k | **~4,4k** ✅ |

🔴 **Os oráculos saíram 27% maiores que a estimativa do P1** (6,1k–7,4k, contra 5,0k chutados). É o
insumo que mais pesa depois do alvo, e ⛔ não dá para encolhê-lo sem encolher o contrato.

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

Medida: **~7,6k de 8.192**, ~590 tokens de folga (7%). 📋 Duas coisas já foram feitas por causa dela:
a mensagem foi enxugada de 6.373 para 5.401 bytes, e o **C3.6 foi cortado do oráculo** — ele afirmava
os contadores, que `test_importacao_contadores.py` já afirma. ⭐ As duas juntas compraram ~600 tokens.

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

Quatro módulos novos, **29 testes**, um módulo por tarefa *(Achado F)*. ⚠️ Nenhum passa de 8 testes
*(Achado N)*. Mais a alteração de **duas linhas** em `test_itens_no_json.py` *(D12)*.

🔴 **O vermelho certo, conferido antes de qualquer implementação:** 16 vermelhos, 13 verdes e um
`ModuleNotFoundError` em `test_varredura_pendentes.py` — que é o vermelho esperado de módulo que ainda
não existe, ⛔ e não `No module named pytest`.

⭐ **Os 13 verdes são informação, não ruído:** são as guardas de regressão (C3.1, C3.5) e os
critérios que o código de hoje já satisfaz. ⚠️ **O C3.3 é o caso interessante: ele passa POR ACIDENTE**,
porque `persistir_nota` ainda commita. Depois da tarefa 1 ele fica vermelho, e só a tarefa 3 o acende
de novo — 📋 previsto na §2, e ⛔ não é regressão quando aparecer no `verify.py` entre as tarefas.

### 📋 Metade 1 — satisfazível *(Achado S)*

Protótipo de referência → suíte inteira → **354 passed** (324 publicados + 30 novos), ⛔ zero
regressão → apagado → `git status` com só os oráculos e a spec.

⭐ **A armadilha da 011 foi desarmada antes de morder:** a cópia do protótipo ficou **fora do repo**,
no scratchpad, e o script de mutação restaura num `finally`.

### 🔴 Metade 2 — mordente *(Achado U)*

📋 **A previsão foi escrita ANTES de rodar.** Dez mutações, e as dez bateram.

| M | Mutação | Previsto | Acendeu |
| - | ------- | -------- | ------- |
| M1 | despachante sempre por texto | C1.1, C1.3 | ✅ as duas |
| M2 | devolve o `commit()` a `persistir_nota` | C1.5 | ✅ só ele |
| M3 | não grava `produto_id` | C1.1, C1.2, C1.4, C1.7 — ⚠️ **e C1.3 NÃO** | ✅ exato, C1.3 verde |
| M4 | `LEFT JOIN` → `JOIN` | C2.2, C2.3, C2.6 | ✅ + 3 publicados |
| M5 | as duas chaves somem da saída | C2.2, C2.3 + `test_itens_no_json` | ✅ + C2.1, C2.4, C2.5 |
| M6 | `persistir_nota` volta para dentro do `try` | C3.2 | ✅ só ele |
| M7 | tira o `commit()` de `importar` | C3.3 | ✅ só ele |
| M8 | pendente vira `categoria_id IS NULL` | C4.2 | ✅ só ele |
| M9 | `ORDER BY id DESC` → `ASC` | C4.6 | ✅ só ele |
| M10 | conta os visitados, não os resgatados | C4.5, C4.7 | ✅ as duas |

⭐ **A M3 é a que ensina alguma coisa.** A previsão dizia que a **C1.3 ficaria VERDE** mesmo com o
`produto_id` nunca gravado — porque ela compara o produto dos dois itens, e `None == None` é
verdadeiro. E ficou. 🔴 **Um oráculo que compara dois resultados não prova que qualquer um dos dois
existe.** A C1.3 só vale porque a C1.1 afirma a existência ao lado dela; sozinha, ela seria oca.

⚠️ **Duas ressalvas honestas sobre a rodada:**
- A previsão de cada mutação listava só os testes **do módulo novo**. A M4 e a M5 também acenderam
  testes **publicados** — acerto por baixo, ⛔ não erro, mas a previsão era mais estreita que o efeito.
- A M5 foi escrita como *"omite a chave quando é `None`"* e implementada como *"as duas chaves somem
  sempre"*. ⚠️ O que rodou foi a segunda, e por isso acendeu mais que o previsto.

## 6. P3 — um comando só

✅ **4 de 4 verdes na PRIMEIRA rodada**, 4 invocações para 4 tarefas, **4,7 min** de máquina, e a
suíte completa verde no fim. ⛔ Nenhuma rodada descartada, ⛔ nenhuma sonda.

| # | Tempo | Invocações | Commits | Quem resolveu |
| - | ----- | ---------- | ------- | ------------- |
| 1 | 66,9s | 1 | 1 | 🤖 |
| 2 | 117,4s | 1 | 1 | 🤖 |
| 3 | 77,5s | 1 | 1 | 🤖 |
| 4 | 23,0s | 1 | 2 | 🤖 |

### ⭐ A fórmula da 011 se confirmou fora da 011

| # | previsto no P1 | **`sent` real** | erro |
| - | -------------- | --------------- | ---- |
| 1 | 4,71k | **4,6k** | −2,3% |
| 2 | 5,29k | **5,3k** | +0,2% |
| 3 | 5,81k | **5,3k** | −8,8% |
| 4 | 4,17k | **4,3k** | +3,1% |

🔴 **Quatro pontos novos, numa story diferente, e a fórmula errou no máximo 9% — sempre para
MAIS.** ⭐ Com a 011, são sete medidas. ⚠️ Continua sendo um modelo só e uma janela só.

### 🔴 O Achado AD ⛔ NÃO mordeu — e agora se sabe onde está o gatilho

O plano previa que as mensagens 1 e 4, que mandam uma linha de `import`, pudessem puxar
`produtos.py` e `categorizacao.py` para a conversa. ✅ **Não puxaram.** O log das quatro tarefas
mostra exatamente **dois** `Added ... to the chat`: o alvo e o módulo de teste.

⭐ **A diferença para a 011 é a FORMA do nome.** Lá a mensagem dizia `` `banco.py` ``, `` `seed.py` ``
— nome de **arquivo**, com extensão. Aqui ela diz `from nfe_parser.produtos import ...` — caminho
de **módulo**, pontilhado. 📋 O Aider resolve o primeiro contra o repositório e ⛔ não o segundo.

⚠️ **Um ponto, não uma lei.** Mas é uma saída barata quando um import for inevitável: escreva o
caminho do módulo, ⛔ nunca o nome do arquivo.

### ⚠️ A tarefa 2 fez uma segunda chamada, com 8,6k — ACIMA do `num_ctx`

Ela ficou **verde na primeira** (7 passed). A segunda chamada é do encerramento do Aider, e o log
termina em `Summarization failed ... cannot schedule new futures after shutdown`. ⛔ Não afetou o
resultado, e fica **registrado como fato, sem conclusão**.

## 7. P4 — revisão, cobertura, estilo

✅ **Nenhuma docstring publicada se perdeu.** O `whole` reescreveu três arquivos que já tinham
código — até 5.975 B — e a docstring de `_processar_evento`, a de `nota_para_json`, a de
`de_centavos` e o cabeçalho de `serializacao.py` voltaram palavra por palavra. ⭐ **Achado R, quinta
story seguida.**

### O que a revisão achou

| # | Defeito | De quem |
| - | ------- | ------- |
| 1 | 🔴 **O C3.1 não exercitava o ramo que a docstring dele dizia** — ver §7 da spec | 📋 meu, no P2 |
| 2 | Dois comentários sumiram de `importar` (`# 2. Abre o .zip`, `# Trata como um arquivo XML avulso`) | 📋 meu: a mensagem mandou trocar o bloco por código que não os tinha |
| 3 | O `conexao.commit()` entrou **depois** do comentário `# 4. Devolve o importacao_id`, que passou a rotular a linha errada | 🤖 do modelo |
| 4 | O import novo colou no bloco da stdlib, sem linha em branco | 🤖 do modelo — o `ruff` resolveu |

⚠️ **O modelo local não escreveu docstring nenhuma. Oitava story seguida.** As de
`resolver_produto_do_item`, `classificar_produtos_pendentes`, os dois cabeçalhos de módulo novos e a
ampliação das de `persistir_nota` e `_itens_da_nota` entraram todas aqui.

### Cobertura, depois do C3.8

| Módulo | Cobertura |
| ------ | --------- |
| `persistencia.py` | **100%** |
| `serializacao.py` | **100%** |
| `importador.py` | **100%** *(era 96% antes do C3.8)* |
| `varredura.py` | **100%** |

✅ `ruff format` e `ruff check --fix` sobre `src/ tests/` — ⛔ nunca `.`, que reformataria os blocos
de código dos `.md` das tarefas. **354 testes verdes.**

## 8. O que pode dar errado

| Risco | Onde | Remédio |
| ----- | ---- | ------- |
| 🔴 **R1** — oráculo que fecha o conjunto de `origem` | tarefas 1 e 4 | ⛔ nenhum teste asserta `origem in {...}`; a varredura compara só com `is not None` |
| 🔴 **R2** — `test_itens_no_json.py` afirma as chaves do item com igualdade estrita | tarefa 2 | alterado à mão no P2, declarado na **D12**, ⛔ nunca descoberto no P3 |
| **Achado AD** — nome de módulo na mensagem puxa o arquivo | tarefas 1 e 4 | cabe no orçamento; `git diff` entre as tarefas |
| **Regressão** na suíte inteira | tarefas 1, 2 e 3 | 🔴 `verify.py` à mão **entre** as tarefas — o `rodar_passo3.py` só roda o módulo da tarefa |
| `whole` apagando docstring publicada | tarefas 2 e 3 | *(Achado R)* a mensagem diz quais voltam inteiras; `git diff` confere |
| Tarefa 3 estourar a janela | tarefa 3 | plano B da §3: tirar a dívida **d** |

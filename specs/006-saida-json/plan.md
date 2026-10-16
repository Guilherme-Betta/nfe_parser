# Plan — 006 · A saida em JSON

Como a `spec.md` desta pasta vira tres tarefas para o modelo local, em que ordem, com que orcamento
de contexto e quais riscos.

---

## 1. As tres tarefas

| # | Entrega | Alvo | Teste | Depende de |
| - | ------- | ---- | ----- | ---------- |
| 1 | `de_centavos` — inteiro de centavos vira string `"123.45"` | `serializacao.py` (nasce aqui) | `tests/test_de_centavos.py` | — |
| 2 | `nota_para_json` — a nota, sem itens | `serializacao.py` | `tests/test_nota_para_json.py` | 1 |
| 3 | a chave `itens` entra na saida da 2 | `serializacao.py` | `tests/test_itens_no_json.py` | 2 |

### Por que esta ordem, e por que tres e nao uma

A dependencia e real: a tarefa 2 **chama** `de_centavos`, e a 3 edita o dicionario que a 2 monta.
Nao da para paralelizar.

A razao de partir em tres e orcamento, nao gosto. Uma tarefa unica somaria os tres testes num
modulo so — passaria dos **8 testes** que o handoff fixa como teto, e o despejo de falha do pytest
escala com o **numero de testes do modulo**, nao com o tamanho do codigo (*Achado N*). Foi assim que
uma tarefa da 005 foi de 5,8k a 18k dentro do laco de reflexao.

Partir tambem separa o risco: a tarefa 1 e pura (entra int, sai str, sem banco), entao se ela falhar
o defeito e aritmetica e nada mais. E o tipo de tarefa em que o modelo local tende a nascer verde.

---

## 2. Orcamento de contexto — estimativa do P1

Formula do kit, **com a constante corrigida da medicao 6** (3,0k, nao 1,5k):

    turno 1 ≈ 3,0k (Aider) + bytes(alvo)/4 + bytes(teste)/4 + bytes(mensagem)/4

### Estimativa do P1 *(provisoria — substituida pela tabela abaixo)*

| # | alvo | teste | mensagem | **turno 1 estimado** | teto 6k |
| - | ---- | ----- | -------- | -------------------- | ------- |
| 1 | 0 b (arquivo novo) | ~1,4 kB | ~1,8 kB | **~3,8k** | ✅ |
| 2 | ~0,7 kB | ~3,0 kB | ~3,2 kB | **~4,7k** | ✅ |
| 3 | ~2,4 kB | ~2,8 kB | ~2,4 kB | **~4,9k** | ✅ |

### ⭐ Remeco do fim do P2 — bytes reais, testes ja escritos

Estimar o tamanho de um arquivo que ainda nao existe nao funciona (*Achado E*), entao a tabela
acima ficou so como registro do erro de estimativa. Esta e a que vale:

| # | alvo | teste | mensagem | **turno 1 medido** | teto 6k |
| - | ---- | ----- | -------- | ------------------ | ------- |
| 1 | **0 b** (arquivo novo) | **2.450 b** | **1.690 b** | **~4,0k** | ✅ folga de 2,0k |
| 2 | ~900 b (estimado: `serializacao.py` depois da 1) | **6.230 b** | **2.532 b** | **~5,4k** | ✅ folga de 0,6k |
| 3 | ~2.800 b (estimado: depois da 2) | **5.584 b** | **1.866 b** | **~5,6k** | ⚠️ folga de 0,4k |

⚠️ **A tarefa 3 e a apertada, e o que sobrou de incerteza e o `alvo`** — quanto o modelo local vai
escrever de docstring na tarefa 2. Se ele for verboso e `serializacao.py` chegar a 4 kB, a tarefa 3
sobe para ~5,9k: ainda dentro, sem folga.

📋 **Se a tarefa 3 estourar, o remedio e encolher, nao detalhar** (a licao cara da 005). O corte
disponivel e a mensagem `tarefa-03.md`: os dois SELECTs prontos podem virar um so, e o bloco "o que
nao pode mudar" pode virar uma linha. ⛔ Nao re-especificar com MAIS texto.

⚠️ **Nenhum modulo de teste desta story passa de 8 testes.** Contagem real: **6 · 7 · 7**.

---

## 3. Os riscos, e o que cada um exige da mensagem

### R1 — o float no dinheiro 🔴 o mais provavel

`centavos / 100` e o caminho que qualquer modelo escreve por reflexo, e ele **passa** nos casos
pequenos. Se entrar, passa nos testes obvios e erra em producao.

**Mitigacao:** a mensagem da tarefa 1 proibe `/`, `float`, `round` e `Decimal` explicitamente e
mostra a forma com `//` e `%`. E o teste inclui um valor grande o bastante para o float64 perder o
centavo, entao o reflexo errado fica **vermelho**, nao so proibido no texto.

### R2 — o sinal negativo no `//`

`-5 // 100` e `-1`, e `-5 % 100` e `95` — a forma ingenua com inteiro devolveria `"-1.95"` para
cinco centavos negativos. Nao ha valor negativo no banco hoje (`vNF` nao e negativo), mas uma funcao
de formatacao que erra em silencio e divida futura.

**Mitigacao:** separar o sinal antes, operar no `abs`. Um teste cobre.

### R3 — `sqlite3` devolve tupla, nao dicionario

Sem `row_factory`, o `SELECT` volta como tupla posicional, e montar o dicionario contando posicoes
na mao e onde nasce o campo trocado.

**Mitigacao:** a mensagem manda usar `cursor.description` para tirar os nomes das colunas e fazer
`dict(zip(...))`. ⛔ E proibe mexer em `conexao.row_factory`: a conexao e do chamador, e alterar o
comportamento dela seria efeito colateral em codigo que a 006 nem deveria tocar.

### R4 — `ensure_ascii` (criterio 6)

`json.dumps` **escapa acento por padrao**. O default erra este criterio.

**Mitigacao:** a mensagem diz `ensure_ascii=False` literalmente, e o teste da tarefa 2 usa um
municipio com til e compara depois do `json.loads`.

### R5 — a tarefa 3 reescrever a tarefa 2

Ao editar `serializacao.py` para acrescentar `itens`, o modelo local pode reformular
`nota_para_json` inteira e quebrar o que ja estava verde.

**Mitigacao:** o teste da tarefa 2 continua na suite, entao a regressao aparece. E a mensagem da
tarefa 3 diz para **acrescentar uma chave**, nomeando o que nao deve mudar.

---

## 4. Ordem de execucao (o loop do kit)

1. **P1** — esta pasta: `spec.md`, `plan.md`, `tarefas.json`, `tarefas/tarefa-0N.md`.
2. **P2** — os tres modulos de teste, **commitados antes** da implementacao. Confirmar o vermelho
   certo (`ModuleNotFoundError: nfe_parser.serializacao`, **nao** `No module named pytest`).
   ⭐ Remedir o orcamento aqui.
3. **P3** — `python scripts\rodar_passo3.py specs\006-saida-json\tarefas.json`, sem ninguem no
   teclado. Preencher a coluna "Quem resolveu" (🤖 · 👤 · 🤝) no registro.
4. **P4** — ler o diff linha a linha, cobertura de `nfe_parser.serializacao` com
   `term-missing`, `ruff format` e `ruff check --fix`.

---

## 5. Divida tecnica: nenhuma a pagar aqui

As cinco dividas abertas (a–e) estao em `persistencia.py`, `classificador.py` e `importador.py`.
⛔ **A 006 nao toca em nenhum desses arquivos** (spec §5), entao nenhuma vence nesta story — a
regra do kit e pagar quando uma story **tocar** aquele codigo.

A mais seria, a **(c)** do `importador.py`, continua esperando uma story que mexa na importacao.

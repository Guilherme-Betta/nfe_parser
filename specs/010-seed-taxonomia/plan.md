# Plan — story 010: o seed da taxonomia

> A spec diz **o que** e **por quê**. Este arquivo diz **em que ordem**, **com que orçamento**, e
> **o que pode dar errado no caminho**.

---

## 1. As duas tarefas do loop, e o que fica fora dele

| # | Alvo | Função | Oráculo |
| - | ---- | ------ | ------- |
| 1 | `src/nfe_parser/seed.py` (**novo**) | `carregar_categorias` | `tests/test_seed_categorias.py` |
| 2 | `src/nfe_parser/seed.py` | `carregar_ncm_ancora` | `tests/test_seed_ncm.py` |

**Fora do loop, escrito por Claude:**

| O quê | Quando | Por quê |
| ----- | ------ | ------- |
| `src/nfe_parser/dados/taxonomia_seed.json` | depois do P3 | 🔴 é **curadoria**, e o Gui revisa |
| `carregar_seed` + `carregar_seed_padrao` | P4 (C3) | cola de 6 linhas; ver **D3** |
| `tests/test_seed_dados.py` | P4 (C4) | teste sobre o **dado**, não sobre o código |
| a linha de `package-data` no `pyproject.toml` | P4 (C5) | sem ela o JSON some na instalação |

### 🔴 A parada do Gui não é no fim — é entre o P3 e o P4

⚠️ Diferente das stories 005–009, esta tem **uma parada no meio**: o arquivo de dados precisa da
revisão dele antes de o P4 escrever o teste que o usa. ⭐ E a ordem é essa, e não o contrário, porque
o teste C4 é justamente o que prova que o dado revisado carrega e resgata produto do bucket.

📋 **A sequência:** P1 → P2 → P3 → escrever o JSON → 🛑 **Gui revisa** → P4 → ramo curado →
🛑 **Gui transfere** → handoff → 🛑 **Gui fecha o `/usage`**.

---

## 2. 🔴 O orçamento, agora CALIBRADO — e a fórmula do kit foi aposentada

A fórmula do kit (`3,0k + bytes/4`) errou por **1,6×** na 009, e o handoff mandou tratá-la como
ordem de grandeza. ⭐ Mas a 009 deixou **três medições reais de `Tokens: sent` com `--edit-format
whole`**, e três pontos bastam para ajustar a reta em vez de chutar.

| Tarefa da 009 | alvo | teste | mensagem | **soma (B)** | **sent medido** |
| ------------- | ---- | ----- | -------- | ------------ | --------------- |
| 1 | 0 | 2.976 | 2.733 | **5.709** | **7,2k** |
| 2 | 410 | 5.202 | 5.101 | **10.713** | **8,6k** |
| 3 | 1.518 | 5.173 | 3.629 | **10.320** | **8,4k** |

**Ajustando a reta pelos extremos** (T1 → T3): 4.611 bytes a mais custaram 1.200 tokens a mais —
**1 token por 3,7 bytes**, e não por 4. Com esse coeficiente, a constante sai igual nos três pontos:

| | 7.200 − 5.709/3,7 | 8.600 − 10.713/3,7 | 8.400 − 10.320/3,7 |
| - | ---- | ---- | ---- |
| **constante** | **5.657** | **5.704** | **5.611** |

> ### 🔴 `sent ≈ 5,65k + bytes(alvo + teste + mensagem) / 3,7`
>
> ⭐ **Os três pontos caem dentro de ±50 tokens.** ⚠️ Vale para `--edit-format whole`, neste repo,
> com `--map-tokens 0`.

⛔ **A constante do kit é 3,0k e a real é 5,65k** — quase o dobro. É daí que vinha o erro de 1,6×,
e ⭐ **não era o coeficiente por byte: era o piso fixo.** O `diff` tem piso ainda maior (~+1,8k),
que é o Achado X inteiro.

### O orçamento desta story

| Tarefa | alvo | mensagem | teste (**teto**) | **sent previsto** |
| ------ | ---- | -------- | ---------------- | ----------------- |
| 1 | 0 | **3.922** | ≤ 3.500 | **~7,7k** |
| 2 | ~1.400 | **3.489** | ≤ 3.500 | **~7,9k** |

🔴 **O teto de 3.500 bytes por módulo de teste é a restrição que o P2 tem de respeitar**, e agora
ela tem origem aritmética, não gosto: é o que sobra de 8.192 depois do piso de 5,65k e das
mensagens, que já estão medidas.

⚠️ **Passar de 8.192 não é morte certa** — as tarefas 2 e 3 da 009 enviaram 8,6k e 8,4k e
converteram. ⛔ Mas também não é margem para gastar de propósito.

⭐ **O teto do `whole` não aperta aqui:** `seed.py` fecha com ~55 linhas de código, contra as ~120
que o kit mede como limite de reescrita integral.

---

## 3. P1 — o que já está feito

✅ `spec.md` com **D1–D9** e os critérios **C1–C2** congelados.
✅ As duas mensagens, escritas **antes** deste plan — por isso a tabela acima traz bytes **medidos**.
✅ `tarefas.json`.

---

## 4. P2 — os oráculos, e o corte que o orçamento impõe

**Um módulo de teste por tarefa** (Achado F). **Máximo 8 testes por módulo** (Achado N) —
aqui a restrição que morde antes é a de **bytes**, não a de contagem.

### O que NÃO repetir entre os dois módulos

⭐ A lição do corte da 009: `test_cascata.py` reencenava a precedência de prefixo que
`test_ncm_ancora.py` já era dono, e uma mutação acendia 6 vermelhos em vez de 3.

📋 Aqui a fronteira é limpa e barata de manter:

| Módulo | É dono de | ⛔ NÃO toca |
| ------ | --------- | ----------- |
| `test_seed_categorias.py` | upsert por slug, duas passadas, `id` estável, invariante do bucket | `ncm_ancora` |
| `test_seed_ncm.py` | upsert por prefixo, largura 2/4/8, resolução do slug | árvore de categorias — semeia **duas** linhas e pronto |

### 🔴 A metade 2 — as mutações que valem a pena

Previsão escrita ANTES de rodar, para poder ser contrariada (foi o que pagou na 009):

| # | Mutação | Previsão |
| - | ------- | -------- |
| M1 | juntar as duas passadas num `for` só | C1.2 vermelho (filho antes do pai) |
| M2 | trocar o UPSERT por `INSERT OR IGNORE` | C1.6 vermelho; C1.3 e C1.4 **verdes** |
| M3 | trocar o UPSERT por `INSERT OR REPLACE` | C1.4 vermelho (o `id` muda) |
| M4 | contar `is_bucket` na lista em vez de no banco | C1.7 vermelho só no caso de **dois** buckets |
| M5 | tirar a guarda de largura do prefixo | C2.5 vermelho, e **só** ele |
| M6 | deixar o `SELECT` do slug devolver `None` | C2.4 vermelho, mas com `IntegrityError` no lugar de `LookupError` |

⚠️ **M2 é a mutação mais informativa da lista**, e por isso está aqui: se `INSERT OR IGNORE`
deixasse C1.3 **e** C1.6 verdes, o oráculo não saberia distinguir "idempotente" de "insere e
ignora" — que é exatamente a diferença que a **D4** diz importar.

---

## 5. P3 — um comando só

```powershell
python scripts\rodar_passo3.py specs\010-seed-taxonomia\tarefas.json --simular
python scripts\rodar_passo3.py specs\010-seed-taxonomia\tarefas.json --edit-format whole
```

⭐ **`--edit-format whole` desde a primeira invocação** (Achado X): alvo novo e pequeno, e não se
gasta invocação redescobrindo o que a 009 já mediu.

⚠️ **O `--simular` NÃO estima tokens** — só imprime o comando. ⛔ O `sent` só existe depois de
invocar; é por isso que a calibração do §2 vale a pena.

### 🔴 O risco próprio da tarefa 2: o `whole` reescreve o arquivo inteiro

A mensagem da tarefa 2 abre dizendo, com todas as letras, que `carregar_categorias` **não se altera
e tem de vir inteira na resposta**. ⚠️ É o modo de falha natural do formato `whole`, e não existia
nas stories que usaram `diff`.

📋 Se ele apagar a função 1: é falha de **aplicação**, não de raciocínio — **aproveitar** o que veio
e pedir só a função que falta (Achado T).

---

## 6. P4 — e a ordem importa por causa do `ruff`

1. Ler o **código inteiro**, não o diff (Achado H).
2. Escrever as docstrings — o modelo local não escreve nenhuma, quinta story seguida.
3. C3 (a cola) e C5 (`pyproject.toml`).
4. Escrever o JSON de dados → 🛑 **parada do Gui**.
5. C4, o teste do dado, em módulo novo, validado por mutação.
6. Cobertura, `ruff format`, e só então `ruff check --fix`.

⚠️ **Achado Y aplica em cheio aqui:** enquanto `seed.py` não existir, o isort classifica
`nfe_parser.seed` como pacote de **terceiros** e o `ruff check` acusa `I001` falso nos testes do P2.
⛔ Por isso `ruff check --fix` só no P4 — e ⛔ sempre `src\ tests\`, nunca `.`, para não reformatar
os blocos de código dentro dos `.md` das tarefas, que são o registro do que foi **enviado**.

---

## 7. O que pode dar errado, e o que fazer

| Sintoma | O que é | Remédio |
| ------- | ------- | ------- |
| Bloco malformado, 0 commits | truncamento | já estamos em `whole`; ⭐ cortar **teste**, que é o insumo com folga |
| A tarefa 2 volta sem a função 1 | aplicação | **aproveitar**, pedir só a que falta |
| `IntegrityError` em vez de `LookupError` | o modelo usou subconsulta no `INSERT` | reverter e nomear **um** defeito: "resolva o slug antes, em Python" |
| `I001` nos testes do P2 | ⚠️ falso — Achado Y | ⛔ não conserte; `ruff check` só no P4 |
| O oráculo passa mas o `id` muda | `INSERT OR REPLACE` | é a M3; se o teste não pegou, o teste é que está fraco |

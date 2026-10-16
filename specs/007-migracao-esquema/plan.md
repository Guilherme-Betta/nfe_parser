# Plan — 007 · Migracao versionada e o esquema da classificacao

Como a `spec.md` desta pasta vira tres tarefas para o modelo local, em que ordem, com que orcamento
de contexto e quais riscos.

---

## 1. As tres tarefas

| # | Entrega | Alvo | Teste | Depende de |
| - | ------- | ---- | ----- | ---------- |
| 1 | `versao_do_banco`, `aplicar_migracoes`, `MIGRACOES` vazia, e o fio em `abrir_banco` | `migracoes.py` (nasce aqui) **+ `banco.py`** | `tests/test_migracoes.py` | — |
| 2 | migracao **v1**: as 5 tabelas e os 2 indices parciais | `migracoes.py` | `tests/test_esquema_classificacao.py` | 1 |
| 3 | migracao **v2**: `ALTER TABLE` + indice, e o banco legado | `migracoes.py` | `tests/test_migracao_itens.py` | 2 |

### 🔴 Uma mudanca em relacao ao recorte, e ela e de ORCAMENTO, nao de escopo

O recorte diz "3 tarefas · alvo `migracoes.py` (novo) + toque minimo em `banco.py`", sem dizer
**em qual** das tres o toque em `banco.py` acontece. O caminho natural seria a tarefa 2 (e quando
existe migracao para aplicar). ⛔ **Nao da, e a razao e numerica.**

`banco.py` tem **3.023 bytes**. Um arquivo alvo entra inteiro no turno 1, entao ele custa ~756
tokens onde quer que esteja. Somado a tarefa 2, que ja carrega o DDL das 5 tabelas na mensagem:

| Onde o `banco.py` entra | tarefa 1 | tarefa 2 | tarefa 3 |
| ----------------------- | -------- | -------- | -------- |
| na tarefa 2 (natural) | ~4,5k | **~5,7k** ⚠️ | ~5,2k |
| **na tarefa 1** (escolhido) | **~5,3k** | **~5,0k** | **~5,2k** |

⭐ A tarefa 1 e a mais barata das tres (alvo novo = 0 bytes), entao ela e a que tem folga para
absorver o `banco.py`. Poe a tarefa mais cara em ~5,3k em vez de ~5,7k.

📋 **Isto e detalhe de execucao, nao re-decisao do recorte:** continuam 3 tarefas, os mesmos dois
alvos, o mesmo escopo e a mesma ordem. O recorte deixou os criterios e o detalhe para o P1.

### Por que tres, e por que esta ordem

A dependencia e real e nao da para paralelizar: a tarefa 2 registra uma migracao no executor que a
1 cria, e a 3 registra a seguinte.

A razao de partir em tres e orcamento e **isolamento de risco**, nao gosto:

- a tarefa 1 e **pura mecanica** — le e escreve `PRAGMA user_version`, percorre uma lista. Nao
  conhece nenhuma tabela do dominio. Se falhar, o defeito e o executor, e nada mais.
- a tarefa 3 e a unica que toca o ponto **nao-idempotente** de toda a spec 02. Isolada, ela pode
  ter um modulo de teste inteiro dedicado ao caso do banco legado.

⚠️ **Nenhum modulo de teste passa de 8 testes** (*Achado N*: o despejo de falha escala com o numero
de testes do modulo). Contagem planejada: **7 · 7 · 7**.

---

## 2. Orcamento de contexto — estimativa do P1

Formula do kit:

    turno 1 ≈ 3,0k (Aider) + bytes(alvo)/4 + bytes(teste)/4 + bytes(mensagem)/4

Mensagem = **byte real**, ja escrita. Alvo e teste ainda sao estimativa.

| # | alvo | teste | mensagem | **turno 1 estimado** | teto 6k |
| - | ---- | ----- | -------- | -------------------- | ------- |
| 1 | **3.023 b** (`banco.py`) + 0 b (`migracoes.py` novo) | ~3,6 kB | **3.551 b** | **~5,5k** | ⚠️ folga 0,5k |
| 2 | ~1,3 kB (`migracoes.py` depois da 1) | ~3,4 kB | **3.410 b** | **~5,0k** | ✅ folga 1,0k |
| 3 | ~2,9 kB (`migracoes.py` depois da 2) | ~3,6 kB | **3.282 b** | **~5,4k** | ✅ folga 0,6k |

⚠️ **A tarefa 1 ja foi encolhida uma vez, aqui no P1.** A mensagem nasceu com 4.281 b e punha o
turno em ~5,7k — folga de 0,3k, apertado demais para uma estimativa que ainda tem o modulo de teste
por medir. Cortei 730 b de prosa **sem tirar nenhuma das quatro regras**: o racional do PRAGMA
interpolado foi de quatro linhas para duas, a proibicao de `executescript` perdeu a repeticao, e as
advertencias sobre `criar_esquema` viraram uma linha so. ⭐ O corte foi de explicacao redundante,
nunca de instrucao — a licao da 005.

### ⭐ Remeco do fim do P2 — bytes reais, testes escritos

Esta e a tabela que vale. O `alvo` das tarefas 2 e 3 continua estimado, mas agora com lastro: sao
os bytes das partes correspondentes do prototipo do §6, que foi escrito **sem docstring**, como o
modelo local escreve.

| # | alvo | teste | mensagem | **turno 1 medido** | teto 6k |
| - | ---- | ----- | -------- | ------------------ | ------- |
| 1 | **3.023 b** (`banco.py`) + 0 b (`migracoes.py` novo) | **4.111 b** | **3.551 b** | **5,67k** | ⚠️ folga 0,33k |
| 2 | ~908 b (so o executor) | **3.762 b** | **3.410 b** | **5,02k** | ✅ folga 0,98k |
| 3 | ~2.539 b (executor + migracao v1) | **4.220 b** | **3.282 b** | **5,51k** | ✅ folga 0,49k |

⚠️ **A tarefa 1 e a apertada, e ja foi encolhida duas vezes** — a mensagem no P1 (−730 b) e o
modulo de teste no P2 (−690 b: a docstring meta foi para a `spec.md` e a lista de migracoes de
mentira, repetida em dois testes, virou o helper `_tres`). ⛔ Nenhuma asserção saiu nos dois cortes.

📋 **Se a tarefa 1 truncar mesmo assim**, o proximo corte e a prosa da REGRA 2 da mensagem (o
paragrafo sobre banco meio migrado): ~160 b que motivam, mas nao instruem. ⛔ O esqueleto de codigo
da REGRA 2 nao pode sair — e ele que mostra o `PRAGMA` dentro do bloco.

⛔ **Mover o `banco.py` para outra tarefa nao ajuda** — foi recalculado com os bytes reais: na
tarefa 2 ele produz 5,78k (folga 0,22k, pior que 0,33k) e na tarefa 3, 6,27k (estoura).

⚠️ **A incerteza que sobra e o `alvo` das tarefas 2 e 3** — quanto `migracoes.py` cresce em cada
passo. O modelo local nao escreve docstring (005 e 006), entao a tendencia e ficar **abaixo** do
estimado; as docstrings entram no P4, depois do loop.

📋 **Se alguma estourar 6k, o remedio e encolher, nao detalhar** (a licao cara da 005). O corte
disponivel na tarefa 2 e o bloco de DDL da mensagem: ele pode ir sem os comentarios `--` do §2 da
spec 02. ⛔ Nao re-especificar com MAIS texto.

---

## 3. Os riscos, e o que cada um exige da mensagem

### R1 — `PRAGMA user_version = ?` 🔴 o mais provavel, e verificado

O reflexo de qualquer modelo (e de qualquer humano) e parametrizar. **Medido em 15/09:**

    con.execute("PRAGMA user_version = ?", (1,))
    -> sqlite3.OperationalError: near "?": syntax error

PRAGMA nao aceita parametro ligado, ponto. A versao tem de entrar **interpolada** na string.

**Mitigacao:** a mensagem da tarefa 1 mostra o erro e a forma certa, e diz por que interpolar aqui
**nao** e buraco de SQL injection: o valor e um `int` que vem da posicao na lista `MIGRACOES`,
nunca de entrada externa. ⚠️ Sem essa frase, um modelo bem-treinado resiste a escrever f-string em
SQL — e resistir aqui produz codigo que nao roda.

### R2 — `executescript` mata a transacao 🔴 verificado, e mata o criterio C1.5

`criar_esquema` usa `executescript`, entao ele e o exemplo que o modelo tem a mao. **Medido:**

    con.execute("BEGIN"); con.execute("CREATE TABLE b ..."); con.executescript("CREATE TABLE c ...")
    con.execute("ROLLBACK")  -> OperationalError: cannot rollback - no transaction is active
    tabelas sobreviventes: ['b', 'c']

`executescript` faz **COMMIT implicito antes de rodar**. Dentro de uma migracao ele destroi a
atomicidade do C1.5 em silencio — o `ROLLBACK` explode, e o que ja rodou fica gravado.

**Mitigacao:** ⛔ a mensagem **proibe `executescript` dentro de migracao**, nomeando a consequencia,
e manda um `conexao.execute(...)` por comando.

### R3 — a migracao gravar a versao fora da transacao ⚠️

Se o `PRAGMA user_version = N` ficar fora do `BEGIN`/`COMMIT`, uma migracao que falha no meio deixa
o banco sem as tabelas mas **com a versao avancada** — e a proxima abertura pula a migracao. Banco
permanentemente quebrado, sem sintoma no codigo.

**Mitigacao:** a mensagem mostra o esqueleto com o `PRAGMA` **dentro** do bloco, e o teste C1.5
injeta uma migracao que levanta excecao no meio e confere as duas coisas: versao inalterada **e**
efeito revertido. ⭐ Medido que DDL do SQLite **faz** rollback dentro de `BEGIN` explicito, entao o
criterio e alcancavel — nao e asserção impossivel.

### R4 — a tarefa 3 reescrever a v1 em vez de acrescentar a v2 🔴 e o risco R5 do recorte

Ao receber `migracoes.py` com a v1 pronta e a tarefa "acrescente o ALTER TABLE", o caminho curto e
editar a funcao que ja esta la.

**Mitigacao:** a mensagem da tarefa 3 diz, literalmente, para **criar uma funcao nova** e
**acrescentar** ao fim de `MIGRACOES`, nomeando o que nao pode mudar. E o teste da tarefa 2
continua na suite: se a v1 for mexida, ele fica vermelho.

### R5 — a ordem das chamadas em `abrir_banco` ⚠️

`aplicar_migracoes` antes de `criar_esquema` quebra o primeiro `abrir_banco` de um banco novo (a
v2 faz `ALTER TABLE itens`, e `itens` ainda nao existiria). O sintoma so aparece na tarefa 3 —
duas tarefas depois de o erro ser escrito.

**Mitigacao:** a mensagem da tarefa 1 mostra o corpo inteiro de `abrir_banco` ja na ordem certa,
com a razao em uma linha.

### R6 — o modelo mexer em `criar_esquema` ⚠️

Recebendo `banco.py` como alvo editavel, ha a tentacao de "organizar" o DDL antigo.

**Mitigacao:** a mensagem diz que a unica mudanca permitida em `banco.py` e **uma linha nova** em
`abrir_banco`, e que `criar_esquema` e intocavel. `test_banco.py`, ja publicado, denuncia.

---

## 4. Ordem de execucao (o loop do kit)

1. **P1** — esta pasta: `spec.md`, `plan.md`, `tarefas.json`, `tarefas/tarefa-0N.md`.
2. **P2** — os tres modulos de teste, **commitados antes** da implementacao. Confirmar o vermelho
   certo (`ModuleNotFoundError: nfe_parser.migracoes`, **nao** `No module named pytest`).
   ⭐ Remedir o orcamento aqui.
3. **P3** — `python scripts\rodar_passo3.py specs\007-migracao-esquema\tarefas.json`, sem ninguem
   no teclado. Preencher a coluna "Quem resolveu" (🤖 · 👤 · 🤝) no registro.
4. **P4** — ler o codigo inteiro (nao so o diff), cobertura de `nfe_parser.migracoes` com
   `term-missing`, `ruff format` e `ruff check --fix`, e escrever as docstrings.

---

## 5. O que este plano deixa verificado antes de escrever teste

⭐ Os cinco comportamentos do SQLite em que os criterios se apoiam foram **medidos em 15/09**, nao
lembrados — a licao da 006, onde um criterio escrito de cabeca virou asserção que nenhuma
implementacao podia satisfazer:

| Comportamento | Resultado medido |
| ------------- | ---------------- |
| `PRAGMA user_version = ?` | ⛔ `OperationalError: near "?": syntax error` |
| indice unico parcial `WHERE gtin IS NOT NULL` | ✅ recusa gtin repetido, **aceita** dois NULL |
| `ALTER TABLE ADD COLUMN ... REFERENCES` com `foreign_keys = ON` | ✅ permitido; linha legada recebe NULL |
| a FK da coluna acrescentada | ✅ `IntegrityError` para id inexistente; NULL aceito |
| `ALTER TABLE` repetido | ⛔ `OperationalError: duplicate column name` |
| DDL dentro de `BEGIN` explicito | ✅ **faz rollback**, e `user_version` volta junto |
| `executescript` dentro de `BEGIN` | ⛔ commita sozinho e destroi a transacao |

Ambiente: Python 3.14.2, SQLite 3.50.4.

---

## 6. 🔴 O oraculo foi provado SATISFAZIVEL antes de ser commitado

A story 006 perdeu as tres reflexoes de uma tarefa contra um teste que **nenhuma implementacao
podia passar** (*Achado P*). Medir comportamento do SQLite (§5) reduz esse risco, mas nao o elimina:
o defeito da 006 nasceu da interacao entre duas asserções, nao de um fato errado sobre a biblioteca.

📋 **Entao, no fim do P2, os 21 testes foram rodados contra uma implementacao de referencia** —
escrita no diretorio temporario da sessao, instalada no clone por um minuto, executada, e apagada.

    21 passed                     so os tres modulos novos
    205 passed                    a suite inteira (184 anteriores + 21)

⛔ **O prototipo NAO entrou no clone e nao existe em commit nenhum.** Se entrasse, o modelo local
receberia a resposta pronta e a medicao do P3 nao valeria nada. Conferido depois de apagar:
`git status` mostrava so os tres arquivos de teste, e `git diff src/nfe_parser/banco.py` saiu vazio.

⭐ **Dois achados caíram desta rodada:**

1. ✅ **O risco R2 do recorte nao disparou.** `test_itens_no_json.py:124` afirma
   `list(item) == CHAVES_DO_ITEM` — igualdade estrita e **publicada** — e a coluna `produto_id`
   nova em `itens` **nao** apareceu na saida. `serializacao.py` lista as colunas explicitamente em
   vez de usar `SELECT *`. O R2 continua adiado para a 013, como o recorte previu.
2. ✅ **Nenhuma das 184 asserções anteriores depende do formato da tabela `itens`.** A migracao v2
   e aditiva de verdade.

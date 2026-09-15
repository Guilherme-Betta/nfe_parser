# Plan — 008 · Identidade de produto

> Como as tres tarefas da [spec](spec.md) sao executadas pelo loop do kit, quanto contexto cada uma
> custa, e o que cada mensagem precisa dizer para o risco correspondente nao disparar.

---

## 1. As tres tarefas

| # | Entrega | Alvo | Teste |
| - | ------- | ---- | ----- |
| 1 | `normalizar_descricao` | `src/nfe_parser/produtos.py` (**novo**) | `tests/test_normalizar_descricao.py` |
| 2 | `resolver_produto_por_gtin` | `src/nfe_parser/produtos.py` | `tests/test_produto_por_gtin.py` |
| 3 | `resolver_produto_por_texto` | `src/nfe_parser/produtos.py` | `tests/test_produto_por_texto.py` |

⭐ **Tres tarefas, um unico arquivo alvo, e isso e de proposito.** Cada tarefa acrescenta uma funcao
independente ao mesmo modulo. A 2 nao precisa ler a 1 para funcionar; a 3 **chama** a 1, e so.

### Por que esta ordem

A tarefa 3 e a unica que depende de outra: ela chama `normalizar_descricao` para montar a chave.
Se viesse antes da 1, o modelo local escreveria uma normalizacao propria ali dentro e teriamos
duas.

A 2 vem antes da 3 porque e a mais simples das duas resolucoes — a chave e o proprio GTIN, sem
normalizacao no meio — e porque ela estabelece o **formato** (procurar, criar se nao achou,
devolver o `id`) que a 3 repete com outra chave. ⭐ Quando a tarefa N ja deixou o padrao escrito no
arquivo, a mensagem da N+1 pode dizer *"mesma forma da funcao anterior"* e encolher.

---

## 2. Orcamento de contexto — estimativa do P1

```
turno 1 ≈ 3,0k (Aider) + bytes(alvo)/4 + bytes(teste)/4 + bytes(mensagem)/4
```

> ⭐ A coluna **mensagem** ja e byte REAL, medido com `wc -c` depois de escrever os tres arquivos —
> nao estimativa. Alvo e teste continuam estimados ate o remeco do fim do P2.

| # | alvo | teste | mensagem (real) | **estimado** | recorte dizia |
| - | ---- | ----- | --------------- | ------------ | ------------- |
| 1 | 0 B (arquivo novo) | ~2,6 kB | **3.880 B** | **≈ 4,6k** | ~4,3k |
| 2 | ~0,7 kB | ~3,0 kB | **3.587 B** | **≈ 4,8k** | ~4,8k |
| 3 | ~2,2 kB | ~3,2 kB | **3.890 B** | **≈ 5,3k** | ~5,3k |

Nenhuma passa de 6k. ⛔ Se alguma passar no remeco do fim do P2, encolhe-se a mensagem antes de
partir a tarefa — partir e o ultimo recurso.

⚠️ **As mensagens sairam ~1 kB maiores do que eu estimei** (~2,8/3,0/3,2 kB previstos contra
3,9/3,6/3,9 kB escritos), e a causa e o R1: a tabela do contraexemplo medido e a regra contra
`isalnum()` ocupam quase 900 B sozinhas na tarefa 1. ⭐ **Vale o preco** — a alternativa e o modelo
escrever `isalnum()`, a tarefa nao convergir, e gastar uma invocacao inteira para ensinar o mesmo.
Mesmo com a folga, a tarefa mais cara fica em 5,3k contra o teto de 6k.

### 🔴 O `bytes(alvo)` da tarefa 3 ja inclui a folga do Achado R

O alvo da tarefa 3 e `produtos.py` **como ele vai estar** depois das tarefas 1 e 2 — nao como eu o
desenhei. Duas coisas o engordam:

1. O modelo local **nao escreve docstring** (aconteceu na 005, 006 e 007). Isso *reduz* o tamanho
   durante o P3 — as docstrings entram so no P4.
2. 🔴 Mas o **Achado R** o aumenta: quando o modelo erra a posicao de uma definicao, ele conserta
   **colando uma segunda copia**, nao movendo. Na 007 isso deixou ~1,7 kB de codigo morto dentro
   do alvo, e o alvo entra inteiro no turno seguinte.

Somadas as duas, a estimativa de 2,2 kB para a tarefa 3 e ~1,4 kB de codigo limpo mais ~0,8 kB de
folga para duplicacao. ⭐ **Lixo deixado por uma tarefa vira teto de contexto da proxima.**

⚠️ `produtos.py` **nao tem lista de registro no nivel do modulo** — nao ha `MIGRACOES` aqui. O
gatilho exato do Achado R nao existe nesta story. A folga fica porque o padrao e do modelo, nao do
arquivo: `PERMITIDOS` (a whitelist da tarefa 1) e uma constante de modulo, e constante de modulo
tambem pode ser duplicada.

### Remeco do fim do P2

> Preenchido ao fim do passo 2, com os testes ja escritos e medidos. ⭐ *Achado E.*

| # | alvo real | teste real | mensagem real | **medido** |
| - | --------- | ---------- | ------------- | ---------- |
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |

---

## 3. Os riscos, e o que cada mensagem exige

### R1 — 🔴 `isalnum()` no lugar da whitelist · *o mais provavel de todos*

O modelo local vai escrever `c if c.isalnum() else " "`. E a forma idiomatica, aparece em todo
tutorial, e **esta errada aqui** — `isalnum()` e Unicode-aware e deixa passar `º`, `ø`, `µ`.
Medido no clone antes de escrever a spec; ver [spec §3.2](spec.md).

📋 **A mensagem da tarefa 1 tem de trazer a constante pronta e proibir `isalnum` pelo nome**, com
o contraexemplo medido junto. ⭐ Proibir sem mostrar o contraexemplo nao segura: o modelo "conserta"
para algo equivalente.

### R2 — 🔴 A ordem dos passos 2 e 3 invertida

Se o filtro ASCII rodar **antes** da decomposicao NFD, o `ç` e descartado inteiro em vez de virar
`c`: `acucar` vira `a ucar`. C1.3 pega, mas a mensagem tem de dizer a ordem **numerada**, nao
descrever as operacoes em prosa.

### R3 — ⚠️ R4 do recorte: a tarefa 3 mexer em `normalizar_descricao`

A tarefa 3 **chama** a normalizacao. O risco e o modelo ajusta-la para fazer o teste da tarefa 3
passar, quebrando o modulo da tarefa 1.

📋 **Dois remedios, os dois necessarios:**

1. A mensagem da tarefa 3 diz literal: *`normalizar_descricao` ja esta pronta e testada. NAO
   mexa nela. Chame-a.*
2. Os testes da tarefa 1 afirmam **propriedades e equivalencias**, nunca a string inteira de uma
   descricao acentuada — assim eles nao viram um campo minado que qualquer ajuste legitimo detona.

⭐ **O segundo remedio tem um limite, e ele esta declarado na [spec §5](spec.md):** propriedade
sozinha e satisfeita por uma funcao que devolve `""`. Por isso C1.3, C1.4 e C1.6 afirmam
**preservacao de conteudo** — propriedade e preservacao juntas e que prendem o comportamento.

### R4 — ⚠️ `commit()` dentro do modulo

O modelo local tende a fechar a transacao por conta propria depois de um `INSERT`. Nenhum teste
pega isso — a mesma conexao enxerga o que ela mesma nao commitou, entao tudo fica verde.

📋 A mensagem das tarefas 2 e 3 proibe `commit()` pelo nome, **e diz por que**: repetiria a divida
tecnica (a). ⚠️ E um item de **revisao do P4**, nao de teste. Ler o codigo procurando `commit`.

### R5 — ⚠️ O `SELECT` da tarefa 3 sem o `gtin IS NULL`

A busca por texto tem de enxergar **so** as linhas sem GTIN. C3.6 cobre. A mensagem traz o `SELECT`
escrito.

### R6 — ⚠️ `INSERT OR IGNORE` / `ON CONFLICT` no lugar de procurar-e-criar

Atalho tentador: inserir com `OR IGNORE` e depois selecionar. Funciona, mas `lastrowid` fica
mentiroso quando o `INSERT` foi ignorado, e a funcao devolveria o `id` errado — em silencio, e so
na segunda chamada.

📋 A mensagem manda **procurar primeiro, inserir so se nao achou**, e devolver `lastrowid` apenas
no ramo que de fato inseriu. C2.5 e C3.5 sao os testes que pegam.

### R7 — 🔴 *Achado Q* — a barra comida pelo heredoc

⛔ **Esta e a story mais exposta do recorte**, porque os testes precisam de caracteres acentuados.

📋 **O remedio escolhido elimina a classe inteira: nao existe barra invertida em lugar nenhum.**

- Na **implementacao**: sem o modulo `re`. Os quatro passos sao `lower`, `unicodedata.normalize`,
  um `for` com whitelist e `" ".join(texto.split())`. Nenhum deles usa escape.
- Nos **testes**: os acentuados entram como **o caractere literal** em arquivo UTF-8 (`açúcar`,
  `pão`), nunca como escape `u00e7`. A forma NFD sai de `unicodedata.normalize("NFD", ...)`, nao
  de escape escrito a mao.

⭐ **Um arquivo sem barra invertida nenhuma nao tem como sofrer o Achado Q.** ⚠️ Mesmo assim:
**reler o arquivo gravado antes de commitar**, que e a regra que nao depende de eu ter acertado o
raciocinio acima.

---

## 4. Ordem de execucao — o loop do kit

| Passo | O que acontece |
| ----- | -------------- |
| **P2** | os tres modulos de teste, commitados **antes** de qualquer implementacao. Vermelho certo = `ModuleNotFoundError: nfe_parser.produtos` (⛔ nao `No module named pytest`) |
| **P2+** | 🔴 o **Achado S**: implementacao de referencia no diretorio temporario, suite inteira verde, apagar, `git status` limpo |
| **P3** | `python scripts\rodar_passo3.py specs\008-identidade-produto\tarefas.json` |
| **P4** | ler o codigo **inteiro**, cobertura de `nfe_parser.produtos`, `ruff format --no-cache src\ tests\`, docstrings |

⚠️ No P2 os modulos das tarefas 2 e 3 vao dar `ImportError` (o nome nao existe no modulo) em vez de
`ModuleNotFoundError`, assim que a tarefa 1 criar o arquivo. **Os dois sao o vermelho certo**; o
vermelho errado e `pytest` nao encontrado.

---

## 5. O que este plano deixa verificado antes de escrever teste

Medido no clone, com o Python do venv, **antes** de os criterios existirem:

| Fato | Resultado |
| ---- | --------- |
| NFD + descartar `Mn` tira acento de `ç`, `ã`, `ú`, `é` | ✅ `açúcar` → `acucar` |
| `ç` decompoe mesmo? | ✅ NFD(`ç`) = `0x63` + `0x327` |
| `isalnum()` deixa passar `º`, `ø`, `µ` | 🔴 **sim** — e o R1 |
| whitelist `a-z0-9` devolve so ASCII | ✅ em todos os 11 casos medidos |
| NFC e NFD da mesma descricao convergem | ✅ as duas dao `acucar` |
| entrada vazia / so espaco / so pontuacao | ✅ devolve `""`, sem excecao |

⭐ **Isto reduz o risco de criterio impossivel; nao o elimina.** O defeito da 006 nasceu da
**interacao entre duas assercoes**, e nenhuma medicao de biblioteca teria pego. Quem pega e o
Achado S, no fim do P2.

---

## 6. O oraculo foi provado satisfazivel?

> Preenchido no fim do P2, depois do protocolo do Achado S. ⛔ Nao commite os testes antes disto.

| | |
| - | - |
| Prototipo rodou | |
| Modulos novos | |
| Suite inteira | |
| `git status` apos apagar | |

# Spec — 008 · Identidade de produto

> Escopo e nao-escopo vieram do [recorte](../02-recorte-em-stories.md) §008, produzido antes de
> qualquer implementacao. O que este documento acrescenta sao os **criterios de aceite** (§4) e as
> decisoes de desenho que eles pressupoem (§2 e §3).
>
> Fonte do requisito: [`02_spec_classificacao.md`](../02_spec_classificacao.md) **§3**.

---

## 1. O problema, em uma frase

Duas linhas de duas notas diferentes podem ser **o mesmo produto**, e hoje nada no banco diz isso.

A tabela `itens` guarda o que veio no XML: a descricao crua do `xProd`, o `gtin` quando existe, o
`ncm`. Cada linha e um evento de compra isolado. Para perguntar *"quanto eu gastei em arroz este
mes"* — que e o ponto da spec 02 inteira — alguem precisa primeiro responder *"estas 14 linhas sao
o mesmo arroz"*.

Esta story responde **so isso**. Ela nao diz o que o produto **e** (categoria); diz apenas **qual
produto** cada item e. Dizer o que ele e fica para a 009.

---

## 2. As duas identidades, e por que elas nao sao equivalentes

O §3 da spec manda resolver nesta ordem:

| | Quando | Chave | Confiavel entre lojas? |
| - | ------ | ----- | ---------------------- |
| `gtin` | o item tem codigo de barras | o proprio GTIN | ✅ **sim** — o GTIN e global |
| `texto` | o item **nao** tem GTIN | `descricao_normalizada` + `emit_cnpj` | ⛔ **nao** — *best-effort* dentro da loja |

🔴 **A assimetria e o requisito, nao um detalhe de implementacao.** A spec chama isso de
*honestidade*: cada loja escreve `xProd` do seu jeito, e "ARROZ TIO JOAO 5KG" numa e "ARROZ T JOAO
5 KG" noutra **nao vao casar**. Fingir que casam produziria um grafico de preco no tempo que mistura
produtos diferentes e ninguem teria como notar.

Por isso o par de texto **inclui o CNPJ da loja**, e por isso a coluna `identidade_origem` existe:
ela e o sinal que os componentes consumidores (preco no tempo, orcamento) leem para saber se podem
comparar entre lojas.

📋 **Consequencia direta, e e um criterio de aceite:** a mesma descricao vinda de **CNPJs
diferentes** tem de gerar **dois produtos distintos**. Ver C3.3.

### O esquema ja existe e nao se toca

A migracao v1 da story 007 ja criou `produtos` com os dois indices unicos **parciais**:

```sql
CREATE UNIQUE INDEX ux_produtos_gtin  ON produtos(gtin) WHERE gtin IS NOT NULL;
CREATE UNIQUE INDEX ux_produtos_texto ON produtos(descricao_normalizada, emit_cnpj) WHERE gtin IS NULL;
```

⛔ **A 008 nao acrescenta migracao nenhuma.** Ela escreve o codigo que *usa* esse esquema. O banco
continua terminando em `user_version = 2`.

⭐ Os dois indices sao a **rede de seguranca** desta story: se o codigo tiver uma corrida ou um
`SELECT` mal escrito e tentar criar duplicata, o SQLite recusa com `IntegrityError` em vez de deixar
passar em silencio. O codigo procura antes de inserir; o indice garante que procurar errado doi.

---

## 3. Onde o codigo mora, e a forma da normalizacao

Modulo novo: **`src/nfe_parser/produtos.py`**. O nome esta reservado no recorte (§ *Nomes de modulo
reservados*) — `classificador.py` ja existe e classifica *documento XML*, nada a ver com isto.

### 3.1 A normalizacao, passo a passo

Quatro operacoes, **nesta ordem**, e a ordem importa:

| # | Operacao | Por que aqui |
| - | -------- | ------------ |
| 1 | `.lower()` | antes de tudo, para o resto nao precisar tratar maiuscula |
| 2 | decompor em NFD e jogar fora as marcas de combinacao (`category == "Mn"`) | e isto que tira o acento: `ç` decomposto vira `c` + cedilha solta, e a cedilha e uma marca |
| 3 | todo caractere fora de `a-z0-9` vira **espaco** | tira pontuacao, simbolo e o que sobrou de nao-ASCII |
| 4 | colapsar espacos e tirar das bordas | `" ".join(texto.split())` faz os dois de uma vez |

🔴 **O passo 2 tem de vir antes do 3.** Invertidos, o `ç` seria descartado inteiro em vez de virar
`c`, e "acucar" viraria "a ucar" — dois tokens onde havia um.

### 3.2 🔴 Por que `isalnum()` esta ERRADO aqui — medido, nao suposto

A forma obvia do passo 3 e `c if c.isalnum() else " "`. **Ela nao serve**, e foi medido no clone
antes deste documento ser escrito:

| Entrada | Com `isalnum()` | Com whitelist `a-z0-9` |
| ------- | --------------- | ---------------------- |
| `1º PRECO` | `1º preco` ⛔ | `1 preco` ✅ |
| `ø10mm` | `ø10mm` ⛔ | `10mm` ✅ |
| `µg VITAMINA` | `µg vitamina` ⛔ | `g vitamina` ✅ |

`str.isalnum()` e **Unicode-aware**: `º`, `ø` e `µ` sao letras ou numeros para o Python. Eles nao
sao decompostos pelo NFD (nao tem acento a tirar — a barra do `ø` faz parte do caractere), entao
sobrevivem ao passo 2 **e** ao passo 3, e a saida deixa de ser ASCII.

⭐ **O custo de errar aqui e silencioso**, que e o pior tipo: nada quebra, e um dia dois produtos
que deviam casar nao casam porque um deles tem um `º` no meio. Por isso C1.2 afirma a propriedade
forte — *a saida so contem `a-z`, `0-9` e espaco* — em vez de so afirmar "sem acento".

### 3.3 Pontuacao vira **espaco**, nao vira nada

`COCA-COLA` pode ir para `coca cola` (pontuacao → espaco) ou `cocacola` (pontuacao → vazio).
Escolhido: **espaco**.

⭐ **Razao:** apagar junta palavras que a pontuacao separava. `PAO/QUEIJO` viraria `paoqueijo`, um
token que nao existe em lugar nenhum. Virar espaco nunca inventa token novo — no maximo parte um
que estava junto.

⚠️ **O preco dessa escolha:** `1,5L` vira `1 5l`, nao `15l`. E aceitavel porque **o MVP nao
interpreta numero nenhum** — a spec §3 diz literalmente *"nao mexe em numeros/unidades no MVP"*. A
descricao normalizada e uma **chave de igualdade**, nao um valor a ser lido. O que importa e que
`1,5L` e `1.5 L` cheguem os dois em `1 5l`, e chegam.

### 3.4 Nada de commit dentro do modulo

As funcoes de `produtos.py` **nao chamam `conexao.commit()`**. Quem abriu a transacao a fecha.

⭐ Isso e deliberado: a divida tecnica **(a)** anotada no handoff e exatamente `persistir_nota`
chamando `commit()` por conta propria, e ela vence na 013. ⛔ Nao se paga uma divida abrindo outra
igual ao lado.

---

## 4. Criterios de aceite

> Um modulo de teste por tarefa, **nenhum passando de 8 testes** (*Achado N*).
>
> 🔴 **Os testes da tarefa 1 fixam PROPRIEDADES e EQUIVALENCIAS, nunca a string inteira de uma
> descricao acentuada** — e o remedio do risco R4 do recorte. Ver §5 do [plan](plan.md).

### C1 — `normalizar_descricao` (tarefa 1)

Modulo: `tests/test_normalizar_descricao.py`

| # | Criterio |
| - | -------- |
| C1.1 | A saida nao tem maiuscula nenhuma. |
| C1.2 | 🔴 A saida so contem `a-z`, `0-9` e espaco. Nenhum acento, nenhuma pontuacao, nenhum simbolo, nenhum caractere fora de ASCII — qualquer entrada. |
| C1.3 | Acento vira a letra-base, e **nao** some: a normalizacao de `açúcar` contem `acucar`; a de `pão` contem `pao`. ⛔ Nao se afirma a string inteira. |
| C1.4 | Pontuacao vira **espaco**, nao vira vazio: `COCA-COLA 2L` produz tres tokens, e `coca` e `cola` estao entre eles como tokens separados. |
| C1.5 | Espacos internos colapsam e as bordas somem: a saida nao tem espaco duplo, nem comeca nem termina com espaco. |
| C1.6 | Numero e unidade **sobrevivem como texto**: a normalizacao de `ARROZ TIPO 1 - 5KG` tem `1` e `5kg` entre seus tokens. ⛔ Nenhuma conversao de unidade. |
| C1.7 | A forma composta (NFC) e a decomposta (NFD) da **mesma** descricao produzem a **mesma** saida. |
| C1.8 | Entrada vazia, so espacos ou so pontuacao produz string vazia — sem excecao. |

⚠️ **C1.8 e uma escolha, e ela tem um buraco conhecido:** dois produtos de descricao so-pontuacao
na mesma loja colidiriam na chave vazia. Aceito — `xProd` e `NOT NULL` no XML e na pratica nunca e
so pontuacao. Registrado em §5 como ressalva, nao como defeito.

### C2 — Resolucao por GTIN (tarefa 2)

`resolver_produto_por_gtin(conexao, gtin, descricao_exemplo) -> int`

Modulo: `tests/test_produto_por_gtin.py`

| # | Criterio |
| - | -------- |
| C2.1 | Chamada com GTIN inedito **cria** a linha em `produtos` e devolve o `id` dela (um inteiro). |
| C2.2 | A linha criada tem `identidade_origem = 'gtin'` e o `gtin` gravado. |
| C2.3 | Na linha criada por GTIN, `descricao_normalizada` e `emit_cnpj` ficam **NULL** — a identidade e o codigo de barras, e o par de texto nao vale para ela. |
| C2.4 | `descricao_exemplo` guarda a descricao recebida, **crua**, so para leitura humana. |
| C2.5 | 🔴 Chamada de novo com o **mesmo** GTIN devolve o **mesmo** `id` e `produtos` continua com **uma** linha — mesmo que a descricao de exemplo seja outra. E o casamento cross-loja do §3. |
| C2.6 | GTINs diferentes produzem `id`s diferentes. |
| C2.7 | `criado_em` e `atualizado_em` sao gravados nao-nulos; `categoria_id` fica **NULL** (categoria nao e desta story). |

### C3 — Resolucao por texto + CNPJ (tarefa 3)

`resolver_produto_por_texto(conexao, descricao, emit_cnpj) -> int`

Modulo: `tests/test_produto_por_texto.py`

| # | Criterio |
| - | -------- |
| C3.1 | Chamada inedita cria a linha e devolve o `id`, com `identidade_origem = 'texto'` e `gtin` **NULL**. |
| C3.2 | `descricao_normalizada` recebe o resultado de `normalizar_descricao(descricao)`, e `emit_cnpj` o CNPJ recebido. `descricao_exemplo` guarda a descricao **crua**. |
| C3.3 | 🔴 **A honestidade do §3.** A **mesma** descricao com **CNPJs diferentes** produz **dois** produtos distintos, com `id`s diferentes. |
| C3.4 | Variacoes de caixa, acento e pontuacao da mesma descricao, no **mesmo** CNPJ, devolvem o **mesmo** `id` e criam **uma** linha so. E para isto que a normalizacao existe. |
| C3.5 | Chamada repetida identica devolve o mesmo `id` sem criar linha nova. |
| C3.6 | Um produto ja criado **por GTIN** com descricao parecida **nao** e devolvido aqui: a busca por texto so enxerga linhas com `gtin IS NULL`. |
| C3.7 | `categoria_id` fica **NULL**, e `criado_em`/`atualizado_em` sao nao-nulos. |

⭐ **C3.6 e o criterio que protege o indice parcial.** Sem o `gtin IS NULL` no `SELECT`, um produto
de GTIN cuja `descricao_normalizada` fosse NULL nunca casaria — mas um `SELECT` frouxo poderia
devolve-lo por engano se a coluna viesse preenchida. O teste fecha essa porta.

---

## 5. O que esta FORA desta story

| ⛔ | Por que, e onde vence |
| -- | --------------------- |
| Qualquer categoria | `categoria_id` fica NULL em toda linha criada. A cascata e a **009** |
| Alterar o fluxo de importacao | `importador.py` e `persistencia.py` nao sao tocados. A integracao e a **013** |
| Preencher `itens.produto_id` | a coluna existe (migracao v2) e continua NULL. Tambem **013** |
| Uma funcao que escolhe entre GTIN e texto | as duas resolucoes sao publicas e independentes; quem decide e o chamador. ⭐ O despachante de tres linhas nasce na **013**, junto com o unico chamador real que vai existir |
| Numeros, unidades, sinonimos, plural, *stemming* | a spec §3 exclui explicitamente no MVP |
| Qualquer mudanca de esquema | o banco fica em `user_version = 2` |

### Ressalvas registradas, que a story aceita de olhos abertos

1. **Descricao so-pontuacao colapsa na chave vazia** (C1.8). Aceito; ver a nota do C1.8.
2. **`ø`, `º` e `µ` perdem o caractere** em vez de virarem letra-base. `ø` nao decompoe em `o` —
   a barra e parte do glifo. Vira espaco. Consistente para todas as ocorrencias, que e o que uma
   chave de igualdade precisa.
3. ⚠️ **O Achado S prova que o oraculo e satisfazivel, nao que ele e correto.** C1.2 sozinho
   passaria com uma funcao que devolve `""` sempre — e por isso que C1.3, C1.4 e C1.6 afirmam
   **preservacao de conteudo**. Os dois lados juntos e que prendem o comportamento.

---

## 6. Dividas tecnicas: nenhuma vence aqui

A 008 nao toca `persistencia.py` nem `importador.py`, que e onde moram as dividas **(a)**, **(c)**
e **(d)**. A divida **(f)** (`criar_esquema` nao virou migracao v0) so vence se alguma story
precisar **alterar** tabela da spec 01 — esta nao altera tabela nenhuma.

⭐ A §3.4 acima registra uma divida que esta story **escolheu nao criar**: nenhum `commit()` dentro
do modulo.

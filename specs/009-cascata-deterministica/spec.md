# Spec — story 009: a cascata determinística

> Implementa o **§4 da `specs/02_spec_classificacao.md`, passos 1, 2 e 4**. É o MVP que a própria
> spec declara: *"base (memória+NCM+bucket) é o MVP e funciona sem LLM"*.
>
> ⛔ **Fora de escopo:** LLM (story 012), eval, edição de taxonomia (011), o seed (010) e a
> integração com a importação (013).

---

## 1. O que a story entrega

Um módulo novo, `src/nfe_parser/categorizacao.py`, com **três funções públicas**:

| Função | O que responde |
| ------ | -------------- |
| `buscar_categoria_por_ncm(conexao, ncm)` | *"que categoria o mapa NCM curado dá a este código?"* — pelo **prefixo mais longo** |
| `classificar_produto(conexao, produto_id, ncm)` | *"que categoria este produto tem?"* — a **cascata inteira**, e grava o resultado |
| `definir_categoria_manual(conexao, produto_id, categoria_id)` | *"o humano decidiu"* — grava `origem='manual'`, que a cascata nunca mais sobrescreve |

⛔ **O nome do módulo é `categorizacao.py`.** Não `classificador.py` — esse já existe e classifica
*documento XML* (modelo 55 vs 65), nada a ver com categoria de produto.

⚠️ **Nenhuma função daqui chama `conexao.commit()`.** Quem abre a transação é que a fecha. É a
mesma regra da 008, e pelo mesmo motivo: a dívida `a` (`persistir_nota` commitando por conta
própria) vence na 013, e não se paga uma dívida abrindo outra igual ao lado.

⛔ **A story não acrescenta migração.** `categoria_id`, `origem` e `confianca` já existem em
`produtos` desde a migração v1, e `categorias`/`ncm_ancora` também. O banco fica em
`user_version = 2`.

---

## 2. As decisões de desenho que o recorte não tomou

O recorte deu escopo, tarefas e riscos. Estas seis decisões são do P1, e **cada critério de aceite
lá embaixo pressupõe uma delas**.

### D1 — item sem NCM devolve `None`, não levanta

🔴 **Esta é a decisão que o Achado W da 008 obrigou a tomar.** Em SQL, `WHERE prefixo = ?` com NULL
não casa com nada — nem com uma linha que tenha NULL ali. Se `ncm` chegasse vazio e a função
consultasse assim mesmo, ela devolveria "não achei" **pelo motivo errado**, e ninguém veria.

⭐ **Mas aqui o remédio é o oposto do da 008.** Lá, GTIN vazio era **erro de programação** — quem
não tem código de barras nunca deveria ter chamado aquela função — e por isso levanta `ValueError`.
Aqui, item **sem NCM é caso normal e comum** em NFC-e. Não é erro de ninguém: é um produto que o
mapa determinístico não alcança, e a cascata já tem uma resposta pronta para isso — o **bucket**,
que é o passo 4.

📋 **Então:** `buscar_categoria_por_ncm` devolve `None` quando `ncm` é vazio ou `None`, **sem
consultar o banco**, e a cascata manda o produto para o bucket.

### D2 — a cascata é `if` sequencial, ⛔ não uma lista de regras no nível do módulo

🔴 **Isto é o Achado R sendo desarmado antes de disparar.** O achado diz que, quando o alvo tem uma
lista ou dicionário no nível do módulo, o modelo local escreve a função nova **abaixo** do registro,
bate em `NameError` e "conserta" **colando uma segunda cópia acima** — não move, copia.

⚠️ Na 008 o achado não disparou porque não havia registro no alvo. Uma "cascata" pede quase sozinha
para virar `REGRAS = [regra_memoria, regra_ncm, regra_bucket]` no fim do arquivo — e seria
exatamente o gatilho.

📋 **Decisão:** três passos, escritos como `if`/`return` em sequência dentro de uma função. As
mensagens do P3 dizem isso literalmente. ⭐ Com três passos fixos e nenhum ponto de extensão
externo, a indireção não paga o próprio custo — e a 012 acrescenta um passo editando a função, que
é uma linha de diff.

### D3 — o produto no bucket é **reprocessável**; `manual` e `memoria` não

A memória do passo 1 protege `origem in ('manual','memoria')`. O bucket grava `origem = NULL`
(§4 passo 4, textual). ⭐ **A consequência é boa e é de propósito:** quando o mapa NCM crescer — e
ele vai crescer, é a story 010 —, rodar a cascata de novo **recupera** os produtos que tinham caído
no bucket, sem tocar em nenhuma decisão humana.

⛔ Um produto com `categoria_id` preenchido **e** `origem IS NULL` está no bucket, não na memória.
Ter categoria não é o que protege; **a origem é.**

### D4 — 009 **respeita** `origem='memoria'`, mas nunca o **escreve**

⚠️ Esta é uma assimetria real, e fica registrada em vez de resolvida no escuro.

O §4 manda manter `origem in (manual, memoria)`. Mas, com a identidade de produto que a 008
entregou, **a realimentação não precisa copiar nada**: todo item do mesmo produto resolve para a
**mesma linha de `produtos`**, e a categoria já está lá. Não existe um segundo lugar para onde
"lembrar" a decisão.

📋 **Então a 009 escreve `'ncm'`, `'manual'` e `NULL`, e trata `'memoria'` como valor protegido que
outra story escreverá** — se alguma precisar. ⭐ Respeitar um valor que ainda não se escreve custa
uma palavra numa tupla e evita que a 011 ou a 013 tenham de voltar aqui.

### D5 — produto inexistente levanta `LookupError`, e é uma checagem só

Tanto `classificar_produto` quanto `definir_categoria_manual` começam **lendo a linha do produto**.
`fetchone()` devolvendo `None` significa que aquele `produto_id` não existe — e `produto_id=None`
cai no mesmo lugar, porque `WHERE id = NULL` não casa com nada.

⭐ **Uma checagem cobre os dois casos**, e cobre-os *antes* de qualquer ramo. Sem ela, o
`UPDATE ... WHERE id = ?` afetaria **zero linhas em silêncio** e a função devolveria um
`categoria_id` que não foi gravado em lugar nenhum — mentira sem sintoma, que é a assinatura do
Achado W.

⛔ `LookupError`, não `ValueError`: o argumento está bem formado, o que falta é a **linha no banco**.

### D6 — banco sem bucket levanta, mas só no ramo que precisa dele

`categorias` está **vazia** até a story 010. Um banco sem linha `is_bucket = 1` não consegue
completar o passo 4.

📋 **A checagem é preguiçosa:** só o ramo do bucket a faz. Um banco cujo mapa NCM cobre o produto
classifica normalmente sem bucket nenhum. ⭐ Levantar na entrada da função proibiria um caso que
funciona.

---

## 3. 🔴 O risco R1, e como estes oráculos se protegem dele

> **R1 (do recorte):** a 009 conhece `origem` em `manual`, `memoria`, `ncm` e NULL. A **012**
> acrescenta **`llm`** e passa a gravar `confianca`.

📋 **As três regras que todo teste desta story obedece:**

1. ⛔ **Nenhum `assert origem in {conjunto fechado}`.** Asserte o valor que *aquela* tarefa decide.
2. ⛔ **Nenhum `SELECT *` comparado como tupla.** Toda leitura nomeia a coluna.
3. ⛔ **Nenhuma asserção sobre `confianca`.** Ela é da 012; aqui fica NULL e não se fala dela.

⭐ **A regra geral do recorte vale inteira:** *a igualdade estrita mora no módulo da última tarefa
que mexe naquela saída.* A 009 **é** a última que decide o `origem` do ramo NCM (`'ncm'`), do
bucket (`NULL`) e do manual (`'manual'`) — então a igualdade estrita nesses três é legítima aqui.

### ⚠️ Um contrato que a 012 vai ter de resolver, e que NÃO se resolve aqui

Declarado agora para que a 012 não o descubra no P3:

> O §4 protege `manual` e `memoria` — **`llm` não está na lista.** Então, como a 009 a deixa, rodar
> a cascata num produto já classificado pelo LLM o reprocessaria: o NCM não casaria (foi por isso
> que ele chegou ao LLM) e ele **cairia no bucket**, perdendo a classificação.

⛔ **Isto não é defeito da 009** — é o §4 lido ao pé da letra, e a 009 implementa o §4. 📋 **É
decisão de produto da 012:** ou `llm` entra no conjunto protegido, ou a cascata passa a distinguir
"nunca classificado" de "classificado e rejeitado". ⭐ A 012 só precisa editar **uma tupla**.

---

## 4. Os critérios de aceite congelados

> Estes são os critérios que o P2 transforma em teste **antes** de qualquer implementação existir.

### C1 — `buscar_categoria_por_ncm(conexao, ncm) -> int | None`

Módulo: `tests/test_ncm_ancora.py`

| # | Critério |
| - | -------- |
| C1.1 | NCM de 8 dígitos cujo prefixo de 8 está no mapa → devolve **aquela** `categoria_id` |
| C1.2 | 🔴 Com prefixos de **8, 4 e 2** casando ao mesmo tempo, vence o **de 8** |
| C1.3 | Sem o de 8, com o de 4 e o de 2 casando, vence o **de 4** |
| C1.4 | Só o de 2 casando → devolve a categoria do **de 2** |
| C1.5 | Nenhum prefixo casa → `None` |
| C1.6 | 🔴 `ncm` vazio (`""`) ou `None` → `None` **(D1)** |
| C1.7 | NCM mais curto que 8 dígitos (ex. `"0403"`) ainda casa os prefixos de 4 e de 2 |

⭐ **C1.2 é o coração da tarefa.** "Prefixo mais longo" é a única regra que faz o mapa curado
funcionar: `04` diz *Mercado*, `0403` diz *Mercado › Laticínios*, e a resposta certa é a segunda.

### C2 — `classificar_produto(conexao, produto_id, ncm) -> int`

Módulo: `tests/test_cascata.py`

| # | Critério |
| - | -------- |
| C2.1 | Produto sem categoria + NCM que casa → grava a categoria do NCM, `origem='ncm'`, bump em `atualizado_em`, e **devolve** o `categoria_id` |
| C2.2 | Produto sem categoria + NCM que não casa → **bucket**, e `origem` fica **NULL** |
| C2.3 | Produto sem categoria + **sem NCM** → bucket **(D1)** |
| C2.4 | 🔴 `origem='manual'` → **mantém**, não escreve nada (`atualizado_em` intacto), devolve a categoria que já estava lá |
| C2.5 | `origem='memoria'` → mantém, igual a C2.4 **(D4)** |
| C2.6 | 🔴 Produto **no bucket** (`origem IS NULL`) com um NCM que agora casa → **sai do bucket** para a categoria do NCM **(D3)** |
| C2.7 | `produto_id` inexistente — e `None` — → `LookupError` **(D5)** |
| C2.8 | Ramo do bucket num banco **sem** linha `is_bucket=1` → `LookupError` **(D6)** |

### C3 — `definir_categoria_manual(conexao, produto_id, categoria_id) -> None`

Módulo: `tests/test_categoria_manual.py`

| # | Critério |
| - | -------- |
| C3.1 | Grava `categoria_id`, `origem='manual'` e faz bump em `atualizado_em` |
| C3.2 | Sobrescreve uma categoria que veio do NCM — o humano tem a palavra final |
| C3.3 | 🔴 Depois dela, `classificar_produto` **mantém**, ainda que o NCM aponte para **outra** categoria |
| C3.4 | ⭐ A realimentação do §4: dois itens do mesmo GTIN resolvem para o mesmo produto, e a decisão manual vale para os dois **sem nova escrita** |
| C3.5 | `produto_id` inexistente → `LookupError` **(D5)** |
| C3.6 | `categoria_id` inexistente → `sqlite3.IntegrityError` — a FK do DDL, com `PRAGMA foreign_keys = ON` que o `abrir_banco` liga |

⭐ **C3.3 é o critério que dá nome à story.** "A cascata nunca sobrescreve decisão humana" só é
verdade se houver um teste que classifica à mão, roda a cascata por cima com um NCM **discordante**,
e prova que a mão venceu.

---

## 5. ⚠️ As tabelas estão vazias — os testes semeiam o próprio dado

`categorias` e `ncm_ancora` foram criadas pela migração v1 **sem uma linha**, e o seed é a story
**010**, que vem *depois* desta.

📋 **Consequência:** toda fixture desta story insere as suas próprias linhas por SQL direto.
⛔ Nenhum teste pode depender do seed real.

⭐ **Isso é bom, não ruim.** Um teste que traz o próprio dado não quebra quando o seed mudar — e o
seed **vai** mudar: a 010 ainda tem três armadilhas de modelagem em aberto (o slug de `Eletrônicos`,
que é pai e filho de si mesmo; `Vestuário`, que é pai sem filho; e os nomes com `(`, `)` e `/`).

---

## 6. O que esta story NÃO entrega

| ⛔ | Por quê |
| - | ------- |
| Qualquer chamada de LLM | story **012** |
| O harness de eval | story **012** |
| O seed da taxonomia e o mapa NCM curado | story **010** |
| Apagar/renomear/mover categoria | story **011** |
| Ligar a cascata ao fluxo de importação | story **013** |
| Um despachante entre `resolver_produto_por_gtin` e `_por_texto` | dívida **g**, nasce na **013** junto com o único chamador real |
| Ler `itens` para descobrir o NCM | a 009 **recebe** o `ncm` por parâmetro; quem o lê é a 013 |

---

## 7. Contratos acrescentados no P4

> 📋 Seção obrigatória do kit, e fica **vazia até o P4 acontecer**. O que entrar aqui é contrato que
> **não** estava nos critérios congelados do §4 — legítimo, e é a rastreabilidade que o torna
> legítimo (foi o caso das duas `ValueError` da 008, registradas como C4 na spec dela).

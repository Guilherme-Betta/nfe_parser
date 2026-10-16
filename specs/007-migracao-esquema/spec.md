# Spec — 007 · Migracao versionada e o esquema da classificacao

Abre a spec 02 (`02_spec_classificacao.md`). Poe o banco sob controle de versao e cria as tabelas
do §2 daquela spec, **sem carregar dado nenhum**.

Escopo, ordem e riscos vieram do recorte (`specs/02-recorte-em-stories.md`, commit `0831e52`,
ja publicado). ⛔ Esta spec **nao re-decide** nada do recorte: ela acrescenta o que o recorte
deliberadamente nao tem — os **criterios de aceite**.

---

## 1. O problema, em uma frase

`abrir_banco` chama `criar_esquema` **a cada abertura** (`banco.py:72`), e `criar_esquema` e so
`CREATE TABLE IF NOT EXISTS` via `executescript`. Isso funciona porque todo comando la e
idempotente.

⚠️ **O `ALTER TABLE itens ADD COLUMN produto_id` da spec 02 nao e.** Medido em 15/09:

    ALTER TABLE itens ADD COLUMN produto_id INTEGER
    -> sqlite3.OperationalError: duplicate column name: produto_id

Rodar duas vezes levanta excecao. Como `abrir_banco` roda o DDL toda vez, o `ALTER TABLE` posto
dentro de `criar_esquema` quebraria **a segunda abertura de todo banco existente**.

Por isso a story 007 vem antes de qualquer outra da spec 02: sem versao de schema, nao ha onde
colocar um comando que so pode rodar uma vez.

---

## 2. A decisao estrutural: quantas versoes existem

🔴 **Este e o risco R5 do recorte, e ele se resolve aqui, por escrito, antes de qualquer teste.**

**Existem DUAS migracoes. O banco termina esta story em `user_version = 2`.**

| Versao | O que faz | Tarefa que a escreve |
| ------ | --------- | -------------------- |
| **v1** | cria as 5 tabelas novas e os 2 indices unicos parciais | 2 |
| **v2** | `ALTER TABLE itens ADD COLUMN produto_id` + `idx_itens_produto` | 3 |

### Por que duas, e nao uma v1 que faz tudo

Porque uma migracao aplicada e **imutavel**, pela mesma razao que um commit publicado e.

No instante em que a tarefa 2 fica verde e e commitada, pode existir um banco no disco com
`user_version = 1`. Se a tarefa 3 acrescentasse o `ALTER TABLE` **dentro da v1**, aquele banco
nunca receberia a coluna: a versao dele ja diz "v1 aplicada", e o executor pularia. O banco ficaria
permanentemente meio migrado, e nada no codigo denunciaria isso.

📋 **A regra que sai daqui, e vale para as stories 008–013:** mudar o esquema e sempre acrescentar
uma migracao nova. ⛔ Nunca editar uma migracao que ja pode ter rodado.

### A consequencia para os testes (R5, o remedio concreto)

| Tarefa | Pode afirmar sobre a versao | ⛔ Nao pode |
| ------ | --------------------------- | ---------- |
| 1 | `user_version == len(MIGRACOES)` — compara com o **registro**, nao com um literal, entao continua verdadeiro quando o registro crescer | `== 0`, `== 1` |
| 2 | `user_version >= 1` | `== 1` — a tarefa 3 torna isso falso |
| 3 | `user_version == 2` — **igualdade estrita legitima**: e a ultima tarefa que mexe na versao | — |

⭐ E a regra geral do recorte aplicada: *a igualdade estrita mora no modulo da ultima tarefa que
mexe naquela saida.*

---

## 3. Onde o codigo mora

📁 **Modulo novo: `src/nfe_parser/migracoes.py`.** Nasce na tarefa 1 e cresce nas 2 e 3.

✏️ **Unico arquivo existente alterado: `src/nfe_parser/banco.py`**, e so em `abrir_banco`, que
ganha uma chamada. ⛔ `criar_esquema` **nao muda uma linha**.

```python
def abrir_banco(caminho):
    conexao = sqlite3.connect(caminho)
    conexao.execute("PRAGMA foreign_keys = ON")
    criar_esquema(conexao)        # o DDL da spec 01, idempotente, como sempre
    aplicar_migracoes(conexao)    # <- a unica linha nova
    return conexao
```

### 🔴 A ordem das duas chamadas nao e estilo

`criar_esquema` **antes** de `aplicar_migracoes`, sempre. A migracao v2 faz `ALTER TABLE itens`, e
num banco novo a tabela `itens` so existe depois de `criar_esquema` rodar. Invertido, o primeiro
`abrir_banco` de um banco novo quebraria.

### Por que `criar_esquema` continua existindo, em vez de virar a migracao v0

A alternativa — jogar o DDL inteiro da spec 01 para dentro do sistema de migracoes e marcar os
bancos existentes como "ja na v0" — e o desenho que uma ferramenta madura usaria (Alembic,
Flyway). ⚠️ **E mais avancado, e foi rejeitado aqui de proposito:**

1. `criar_esquema` ja e idempotente e ja esta coberto por `test_banco.py`, que esta **publicado**.
   Mexer nele poe em risco codigo verde para ganhar elegancia.
2. Todo banco existente hoje tem `user_version = 0`. Transformar o DDL da spec 01 em v0 exigiria
   distinguir "banco vazio de verdade" de "banco da spec 01 sem marca de versao" — um caso a mais
   para errar, sem nenhum ganho nesta story.

📋 Fica anotado como divida de desenho, nao como bug. Vence se alguma story precisar **alterar**
uma tabela da spec 01 (a 013 e a candidata).

---

## 4. Criterios de aceite

### C1 — O executor de migracoes (tarefa 1)

Em `migracoes.py`:

```python
MIGRACOES = []                                    # cresce nas tarefas 2 e 3

def versao_do_banco(conexao) -> int: ...
def aplicar_migracoes(conexao, migracoes=None) -> int: ...
```

- **C1.1** — `versao_do_banco` le `PRAGMA user_version`. Banco novo devolve **0**.
- **C1.2** — `MIGRACOES` e uma **lista de funcoes**, e a **posicao e a versao**: o item de indice 0
  e a migracao v1, o de indice 1 e a v2. Cada funcao recebe a conexao e nao devolve nada.
- **C1.3** — `aplicar_migracoes` roda, **em ordem crescente**, so as migracoes cuja versao e maior
  que a versao atual do banco, e devolve a versao final.
- **C1.4** — **Idempotente.** Chamar de novo num banco ja atualizado nao roda migracao nenhuma.
- **C1.5** — **Atomica por migracao.** Cada migracao roda dentro de uma transacao que inclui a
  gravacao da versao. Se a migracao levantar excecao no meio, o banco volta ao estado anterior **e
  a versao nao avanca** — a excecao sobe para quem chamou.
- **C1.6** — O parametro `migracoes` existe para o **teste** poder injetar uma lista propria.
  `None` significa usar `MIGRACOES`.
- **C1.7** — `abrir_banco` chama `aplicar_migracoes` depois de `criar_esquema`, e um banco novo
  aberto por ele termina em `versao_do_banco(con) == len(MIGRACOES)`.

⚠️ **Por que injecao e nao teste contra `MIGRACOES` real:** se o modulo de teste da tarefa 1
exercitasse o registro real, as tarefas 2 e 3 quebrariam esse teste ao acrescentar migracoes. Com
lista injetada, a tarefa 1 testa o **mecanismo**, que nao muda mais. E o remedio do R5.

### C2 — O esquema da classificacao, migracao v1 (tarefa 2)

A migracao v1 cria, exatamente como o §2 da spec 02:

| Tabela | Observacao |
| ------ | ---------- |
| `categorias` | `slug` UNIQUE; `parent_id` referencia a propria tabela; `is_bucket` default 0 |
| `ncm_ancora` | `prefixo` e a chave primaria (TEXT) |
| `produtos` | `identidade_origem` CHECK em `('gtin','texto')`; `origem` CHECK em `('manual','memoria','ncm','llm')` |
| `tags` | `nome` UNIQUE |
| `produto_tags` | chave primaria composta `(produto_id, tag_id)` |

E os dois indices **unicos parciais**:

    ux_produtos_gtin   ON produtos(gtin)                            WHERE gtin IS NOT NULL
    ux_produtos_texto  ON produtos(descricao_normalizada, emit_cnpj) WHERE gtin IS NULL

- **C2.1** — depois de `abrir_banco`, as 5 tabelas existem. Conferido por **subconjunto** (`<=`).
- **C2.2** — os 2 indices existem. Tambem por subconjunto.
- **C2.3** — as tabelas da spec 01 continuam existindo. Subconjunto.
- **C2.4** — `ux_produtos_gtin` recusa dois produtos com o **mesmo** `gtin`.
- **C2.5** — o indice e **parcial**: dois produtos com `gtin IS NULL` e textos diferentes sao
  **aceitos**. 🔴 Sem o `WHERE`, este caso quebraria — e o criterio que prova que o `WHERE` foi
  escrito.
- **C2.6** — `ux_produtos_texto` recusa dois produtos com `gtin IS NULL` e o mesmo par
  `(descricao_normalizada, emit_cnpj)`.
- **C2.7** — `user_version >= 1`. ⛔ Nunca `== 1`.

⚠️ **Nenhuma linha e inserida por esta migracao.** Sem categorias, sem bucket `uncategorized`, sem
NCM. O seed e a story 010.

### C3 — A coluna em `itens` e o banco legado, migracao v2 (tarefa 3)

- **C3.1** — depois de `abrir_banco`, `PRAGMA table_info(itens)` mostra `produto_id`.
- **C3.2** — o indice `idx_itens_produto` existe.
- **C3.3** — `user_version == 2`. **Igualdade estrita**, por ser a ultima tarefa que mexe nisso.
- **C3.4** — **Idempotencia.** Abrir o mesmo banco duas vezes nao levanta excecao e `produto_id`
  aparece **uma unica vez** em `table_info`.
- **C3.5** — **Banco legado.** Um banco criado so com `criar_esquema` (sem migracoes), com nota e
  item ja gravados, ao ser aberto por `abrir_banco`: migra para a v2, e o item antigo continua la
  **com os mesmos valores** — nao so com o mesmo `COUNT`.
- **C3.6** — o item legado fica com `produto_id IS NULL`.
- **C3.7** — a FK e real: inserir item com `produto_id` que nao existe em `produtos` levanta
  `IntegrityError`; com `NULL` e aceito.

⚠️ **C3.5 e C3.7 foram verificados empiricamente em 15/09** antes de virarem criterio. `ALTER TABLE
ADD COLUMN ... REFERENCES` com `PRAGMA foreign_keys = ON` e permitido (a coluna nasce com default
NULL), a linha legada recebe NULL, e a FK passa a valer para insercoes novas.

---

## 5. O que esta FORA desta story

- ⛔ **Qualquer dado.** Nenhum seed, nenhuma categoria, nenhum bucket, nenhum NCM. (story 010)
- ⛔ **Qualquer logica de classificacao**, identidade de produto ou normalizacao. (008 e 009)
- ⛔ **Qualquer mudanca em `notas` ou `itens`** alem da coluna `produto_id`.
- ⛔ **Qualquer mudanca em `persistencia.py`, `importador.py` ou `serializacao.py`.** Nada passa a
  gravar ou ler `produto_id` nesta story: a coluna nasce e fica vazia.
- ⛔ **`criar_esquema` nao muda.**
- ⛔ Nenhuma CLI, nenhum script de migracao avulso. A migracao roda por `abrir_banco`.

---

## 6. Dividas tecnicas: nenhuma vence aqui

As cinco dividas abertas (a–e) moram em `persistencia.py`, `classificador.py` e `importador.py`.
⛔ A 007 nao toca nenhum desses arquivos, e a regra do kit e pagar a divida quando uma story
**tocar** aquele codigo. A mais seria, a (c), vence na 013.

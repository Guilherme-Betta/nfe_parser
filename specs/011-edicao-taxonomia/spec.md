# Spec — story 011: edição de taxonomia

> Escopo: o **último bloco do §4** de [`../02_spec_classificacao.md`](../02_spec_classificacao.md):
> *"apagar categoria com histórico → produtos vão pro bucket; renomear → mantém vínculos (id
> estável); mover subcategoria → vínculos seguem (reatribui)."*

---

## 1. O que a story entrega

✅ `src/nfe_parser/taxonomia.py` (novo) — três funções: `renomear_categoria`, `mover_categoria` e
`apagar_categoria`.

✅ **E uma mudança de regra no `seed.py`**, que não estava no recorte e que a §2 explica: o seed
passa a ser *base default*, e ⛔ nunca mais sobrescreve o que o usuário editou.

✅ Migração **v3** — a tabela `categorias_apagadas`, a "lápide" que torna apagar definitivo.

### 🔴 A story tem uma metade que ⛔ NÃO cabe no loop

| Parte | Quem escreve | Por quê |
| ----- | ------------ | ------- |
| `taxonomia.py` | 🤖 modelo local, **3 tarefas** | arquivo novo; a divisão e a ordem estão na §2 do plan |
| migração v3 | 👤 fora do loop | 4 linhas de DDL; tarefa de loop não se justifica |
| mudança no `seed.py` | 👤 fora do loop | 🔴 **não cabe:** ver abaixo |

🔴 **O `seed.py` tem 8.629 bytes.** Com `--edit-format whole` o alvo inteiro vai na mensagem, e o
orçamento da janela de 8.192 tokens dá ~8.100 bytes para **alvo + teste + mensagem somados**
*(Achado AA)*. ⛔ Só o alvo já estoura. Não é escolha de desenho; é aritmética.

⭐ É o mesmo precedente do arquivo de dados da 010: parte da story é escrita fora do loop, e a spec
diz qual parte e por quê.

---

## 2. 🔴 A decisão de produto que abriu esta story

O recorte dizia que a 011 era *"apagar → bucket, renomear → id estável, mover → vínculos seguem"*.
⚠️ **Isso estava completo quando foi escrito e não estava mais quando a story abriu**, porque entre
o recorte e hoje nasceu o seed da 010 — e o seed é um **segundo autor** da tabela `categorias`.

### A prova, rodada no banco real antes de decidir qualquer coisa

```
depois do seed:                    id=4  nome='Laticínios'         parent_id=1
depois da edicao do usuario:       id=4  nome='Leite e derivados'  parent_id=24
depois de rodar o seed de novo:    id=4  nome='Laticínios'         parent_id=1
```

🔴 **O seed desfaz o renomear e o mover, não só o apagar.** O `ON CONFLICT(slug) DO UPDATE SET nome
= excluded.nome` da D4 da 010 sobrescreve, toda vez, com o que está no arquivo.

⚠️ E o seed **vai** rodar de novo: é literalmente o motivo de ele ser idempotente (D6 da 010 — é
assim que o mapa NCM cresce e resgata produto preso no bucket).

### A decisão do Gui, 2026-09-15

> *"o ideal é ter um sistema em que o seed serve só como base default, mas o usuário consegue
> remover, editar e adicionar categorias. Naturalmente, isso deveria ser definitivo, com a seed
> sendo meramente um helpful placeholder"*

📋 **Traduzida para código, a regra é uma frase:** o seed **insere o que falta** e ⛔ **nunca toca no
que já existe**.

⭐ Isso resolve `renomear` e `mover` de graça. `apagar` precisa de uma peça a mais — a lápide — pelo
motivo da D4, abaixo.

---

## 3. As decisões de desenho

### D1 — a API é por `slug`, ⛔ não por `id`

`renomear_categoria(conexao, slug, nome)`, e assim nas três.

⭐ **O `slug` é a chave natural** e já era esse o papel dele na 010 (D1 de lá: o slug é *dado*
explícito, não é calculado a partir do nome). É por slug que o seed casa, é por slug que a lápide
precisa guardar o que foi apagado, e é por slug que uma futura UI vai se referir a uma categoria
sem depender de um `id` que ela não viu nascer.

⚠️ **O `id` continua sendo o que `produtos.categoria_id` e `ncm_ancora.categoria_id` referenciam, e
continua estável.** Não há contradição: slug é a chave *de fora*, id é a chave *de dentro*.

### D2 — renomear muda o `nome`, e ⛔ NUNCA o `slug`

🔴 **Se o slug mudasse, a categoria renomeada viraria "faltando" para o seed**, que a inseriria de
novo com o slug antigo. O usuário ficaria com **duas** categorias onde editou uma, e sem erro nenhum.

⚠️ Há ainda dois motivos menores, e cada um bastaria: a lápide casa por slug, e o
`taxonomia_seed.json` casa as âncoras NCM com a categoria **pelo slug**.

⭐ É o mesmo argumento da D1 da 010, visto do outro lado: slug derivado do nome faria "corrigir um
acento" mudar a identidade da linha.

### D3 — ⛔ renomear com nome vazio LEVANTA

`nome TEXT NOT NULL` **não** pega string vazia — `""` passa pela restrição do banco.

⭐ É o mesmo modo de falha do contrato C4 da 009 (`definir_categoria_manual` com `categoria_id`
vazio): o dano é mudo, e a coluna não defende. `ValueError`, porque o argumento está malformado.

### D4 — 🔴 a lápide: `categorias_apagadas`, e é ela que torna "apagar" definitivo

```sql
CREATE TABLE categorias_apagadas (
  slug TEXT PRIMARY KEY,
  apagada_em TEXT NOT NULL
);
```

⚠️ **Por que a regra da §2 não basta sozinha.** "Insere o que falta" trata uma categoria apagada
como *faltando*, e a insere de novo — com `id` novo e sem os produtos que tinha. O seed estaria
sendo prestativo e desfazendo a decisão do usuário.

⛔ **A tabela não tem `REFERENCES categorias(id)`**, e não é esquecimento: a linha de `categorias`
não existe mais. É exatamente isso que ela registra.

⭐ **Por que tabela separada e não uma coluna `apagada_em` em `categorias`** (o *soft delete*): com a
coluna, a linha continua lá, e **toda** consulta futura sobre categorias — relatório, UI, soma por
categoria — passaria a precisar de `WHERE apagada_em IS NULL`. Esquecer o filtro em um lugar só
volta a mostrar a categoria apagada. Com a tabela separada, quem está em `categorias` **é** uma
categoria, ponto.

### D5 — ⛔ apagar o bucket é RECUSADO

`categoria_do_bucket` (D10) levanta `LookupError` quando não há linha `is_bucket = 1`, e o passo 4 da
cascata morre inteiro. 🔴 Apagar o bucket quebraria a classificação de todo produto não coberto pelo
mapa NCM — e o próprio `apagar_categoria` precisa do bucket para funcionar.

### D6 — ⛔ apagar categoria que tem FILHAS é RECUSADO

🔴 **Achado desta story, e o handoff não o previa:** `categorias.parent_id` é
`REFERENCES categorias(id)`, e o `abrir_banco` liga `PRAGMA foreign_keys = ON`. Apagar um pai com
filhas levanta `IntegrityError` vindo do banco. Medido: das 44 categorias do seed, **10 são pais** e
**28 têm âncora**.

📋 **As três saídas, e por que a recusa ganhou:**

| Saída | Consequência |
| ----- | ------------ |
| apagar as filhas em cascata | ⛔ destrói curadoria do usuário de surpresa, num comando que ele pediu para **uma** categoria |
| promover as filhas a nível 1 | ⚠️ muda a forma da árvore sem ninguém ter pedido; e "mover" já existe, para quem quiser isso |
| **recusar, dizendo o que fazer antes** | ✅ não destrói nada, e é afrouxável depois sem quebrar quem já usa |

⚠️ A mensagem tem de dizer **quantas** filhas e **o que fazer** (mover ou apagar antes). Recusa que
não ensina o caminho é só um obstáculo.

### D7 — apagar leva os produtos ao bucket com `origem = NULL`, ⚠️ inclusive os `'manual'`

🔴 **Este é o ponto mais fino da story.** O que protege um produto da cascata é a `origem`, não a
categoria (cabeçalho de `categorizacao.py`). Se os produtos da categoria apagada fossem para o
bucket **mantendo** `origem = 'manual'`, o passo 1 da cascata os protegeria — **dentro do bucket**,
para sempre. Ficariam presos exatamente onde ninguém quer que nada fique preso.

⭐ E zerar a origem é a resposta honesta: aquela decisão manual apontava para uma categoria que **não
existe mais**. Não há o que preservar.

⚠️ **É por isso que apagar não pode ser um `DELETE` seco:** os produtos têm de sair antes, ou a FK
recusa. A ordem é obrigatória — produtos, âncoras, lápide, e só então a categoria.

### D8 — apagar remove as âncoras NCM da categoria

`ncm_ancora.categoria_id` é `NOT NULL`. ⛔ Não há como "desapontar" a âncora; ou ela aponta para
outra categoria, ou sai.

📋 **As três saídas, e a única que não envenena:**

| Saída | Consequência |
| ----- | ------------ |
| reapontar para o **bucket** | ⛔ o produto daquele NCM passa a ser classificado **ativamente** como bucket, com `origem = 'ncm'` — e `origem` não-NULL o **protege**. Ele para de ser reprocessável, que é o oposto do que o bucket significa |
| reapontar para o **pai** | ⚠️ categoria de nível 1 não tem pai. Só funciona às vezes |
| **apagar a âncora junto** | ✅ o produto volta ao bucket com `origem` NULL, reprocessável — e o mapa NCM não fica apontando para o nada |

### D9 — `carregar_ncm_ancora` PULA âncora de slug sepultado, e ⛔ continua levantando para slug ausente

⚠️ **A distinção é o que salva o seed de virar uma bomba-relógio.** Hoje a função levanta
`LookupError` quando o slug da âncora não existe em `categorias`. Depois da 011, uma categoria
apagada pelo usuário deixaria o `taxonomia_seed.json` apontando para um slug inexistente — e o seed
inteiro passaria a falhar, para sempre, por causa de uma decisão legítima.

⭐ **A lápide é o que distingue os dois casos:** slug **na lápide** é remoção deliberada e registrada
→ pula em silêncio. Slug **simplesmente ausente** é erro de digitação no arquivo de dados → levanta,
como hoje.

### D10 — `_categoria_do_bucket` vira pública: `categoria_do_bucket` — ✅ **dívida `i` paga**

`apagar_categoria` precisa do `id` do bucket.

⛔ **A alternativa — `UPDATE produtos SET categoria_id = (SELECT id FROM categorias WHERE
is_bucket = 1)` — foi descartada:** num banco sem bucket a subconsulta devolve NULL e o UPDATE grava
NULL **em silêncio**. A função levanta `LookupError` com mensagem. Falhar alto é o contrato da 009.

⚠️ Nenhum teste referencia o nome privado (conferido), então a renomeação não quebra oráculo nenhum.

### D11 — ⛔ nenhuma função desta story chama `commit()`

Mesma regra de `produtos.py`, `categorizacao.py` e `seed.py`, e pelo mesmo motivo — a dívida `a`
vence na 013, e não se paga uma dívida abrindo outra igual ao lado.

⭐ Aqui ela ganha um motivo próprio: `apagar_categoria` faz **quatro** escritas em sequência
(produtos, âncoras, lápide, categoria). ⛔ Commitar no meio deixaria o banco com produtos no bucket e
a categoria ainda de pé, se a última falhasse.

### D12 — mover recusa ciclo, e `None` significa "subir para nível 1"

🔴 Mover `mercado` para dentro de `mercado-frutas` (filha dela) cria um **ciclo** na árvore. ⛔ A
chave estrangeira não pega isso — é um caminho válido linha a linha — e o estrago é mudo até alguém
percorrer a árvore e nunca chegar ao fim.

⭐ O teste é uma subida: a partir do novo pai, siga `parent_id` para cima; se passar pela categoria
que está sendo movida, é ciclo. A subida **sempre termina**, porque ou chega a `parent_id IS NULL`
ou reencontra a categoria movida.

📋 `novo_parent_slug = None` faz a categoria virar nível 1 — é como se desfaz um "mover" errado.

---

## 4. Os critérios de aceite congelados

### C1 — `renomear_categoria(conexao, slug, nome) -> None`

| # | Caso | Esperado |
| - | ---- | -------- |
| C1.1 | slug existente | `categorias.nome` passa a ser `nome` |
| C1.2 | o `id` e o `slug` | ⛔ **não mudam** *(D2)* |
| C1.3 | `produtos.categoria_id` que apontavam para ela | ⛔ **intactos** |
| C1.4 | slug inexistente | `LookupError` |
| C1.5 | `nome` vazio ou `None` | `ValueError` *(D3)* |

### C2 — `mover_categoria(conexao, slug, novo_parent_slug) -> None`

| # | Caso | Esperado |
| - | ---- | -------- |
| C2.1 | pai novo existente | `parent_id` passa a ser o `id` do novo pai |
| C2.2 | o `id` da categoria movida | ⛔ **não muda**; produtos e âncoras seguem junto de graça |
| C2.3 | `novo_parent_slug = None` | `parent_id` vira NULL — categoria de nível 1 |
| C2.4 | slug da categoria inexistente | `LookupError` |
| C2.5 | slug do novo pai inexistente | `LookupError` |
| C2.6 | mover para dentro de si mesma | `ValueError` *(D12)* |
| C2.7 | mover para dentro de uma descendente | `ValueError` *(D12)* |

### C3 — `apagar_categoria(conexao, slug) -> None`

| # | Caso | Esperado |
| - | ---- | -------- |
| C3.1 | categoria com produtos | os produtos ficam com o `categoria_id` do bucket |
| C3.2 | produto que estava com `origem = 'manual'` | `origem` vira NULL *(D7)* |
| C3.3 | categoria com âncora NCM | as âncoras dela somem de `ncm_ancora` *(D8)* |
| C3.4 | a categoria | some de `categorias` |
| C3.5 | a lápide | `categorias_apagadas` passa a ter o slug *(D4)* |
| C3.6 | categoria com filhas | `ValueError`, e a categoria **continua lá** *(D6)* |
| C3.7 | o bucket | `ValueError`, e o bucket **continua lá** *(D5)* |
| C3.8 | slug inexistente | `LookupError` |
| C3.9 | apagar o **mesmo slug duas vezes** (ela voltou por um seed antigo) | ⛔ não levanta — a lápide usa `ON CONFLICT DO NOTHING` |

### C4 — o seed depois da 011 *(escrito fora do loop)*

| # | Caso | Esperado |
| - | ---- | -------- |
| C4.1 | rodar o seed depois de renomear | ⛔ o nome editado **permanece** |
| C4.2 | rodar o seed depois de mover | ⛔ o `parent_id` editado **permanece** |
| C4.3 | rodar o seed depois de apagar | ⛔ a categoria **não volta** *(D4)* |
| C4.4 | slug novo no arquivo de dados | ✅ é inserido normalmente — o seed continua sendo base |
| C4.5 | âncora cujo slug está na lápide | ✅ pulada, sem erro *(D9)* |
| C4.6 | âncora cujo slug nunca existiu | `LookupError`, como hoje *(D9)* |
| C4.7 | o mapa NCM das categorias vivas | ✅ continua se **atualizando** — a D6 da 010 sobrevive |

---

## 5. ⚠️ O que os oráculos semeiam, e o que ⛔ não semeiam

⭐ Os testes montam a sua **própria** taxonomia mínima, com `INSERT` direto. ⛔ Não chamam
`carregar_seed_padrao`, e não dependem das 44 categorias reais — amarrar o oráculo ao arquivo de
dados faria o Gui quebrar a suíte ao curar o dado.

⚠️ Exceção deliberada: os casos **C4.x** existem justamente para exercitar o seed, e usam listas
pequenas passadas à mão a `carregar_categorias` / `carregar_ncm_ancora`, ⛔ nunca o JSON do pacote.

---

## 6. O que esta story ⛔ NÃO entrega

⛔ UI · ⛔ HTTP · ⛔ validação de quem pode editar — os três já estavam fora pelo recorte.

⛔ **`adicionar_categoria`.** O §4 da spec 02 lista três operações, e criar não é uma delas. ⚠️ O Gui
mencionou "adicionar" ao descrever o sistema ideal; ficou **anotado**, não silenciado — ver §8.

⛔ Alterar a taxonomia no `taxonomia_seed.json`. O arquivo é dado curado à mão, e continua sendo.

⛔ Qualquer lógica de classificação. `categorizacao.py` só é tocado para tornar uma função pública.

---

## 7. Contratos acrescentados FORA do loop

*(preencher no P4 — ver o precedente na §7 da spec da 010)*

---

## 8. ⚠️ O que fica ANOTADO e não vira código

- ⚠️ **`adicionar_categoria` não existe.** Depois da 011, o usuário consegue apagar as categorias
  default e editar as que ficaram, mas ⛔ não consegue criar uma nova pelo código — só editando o
  `taxonomia_seed.json`. ⭐ É a metade que falta para o "remover, editar e adicionar" que o Gui
  descreveu, e é story própria (precisa de regra de slug para categoria criada por gente).
- ⚠️ **Mover o bucket para dentro de outra categoria é permitido.** Não quebra nada —
  `categoria_do_bucket` procura por `is_bucket = 1`, não pela posição na árvore — mas um relatório
  que some por categoria de nível 1 passaria a contar o não-classificado dentro de outra coisa.
- ⚠️ **A dívida `j` (o degrau de 6 dígitos do NCM) ⛔ não vence aqui.** Continua marcada para a 012.

# Recorte da spec 02 em stories

> Produzido na sessão de planejamento de 14/09/2026, **antes** de qualquer implementação.
> Fonte: [`02_spec_classificacao.md`](02_spec_classificacao.md) lida inteira (6.612 bytes),
> mais o estado real do código no clone.
>
> ⛔ **Aqui NÃO há critérios de aceite.** Eles são escritos no P1 de cada story, com o contexto
> fresco. Este documento decide **quais fatias existem, em que ordem, e o que fica de fora**.

---

## O que o estado atual do código impõe ao recorte

Cinco fatos medidos no clone, que mudaram o desenho em relação ao palpite de "4 ou 5 stories":

| # | Fato | Consequência |
| - | ---- | ------------ |
| 1 | **Não existe versionamento de schema.** `criar_esquema` é só `CREATE TABLE IF NOT EXISTS` via `executescript`, e `abrir_banco` o chama **a cada abertura** | O `ALTER TABLE itens ADD COLUMN produto_id` da spec **quebra na segunda abertura**. Precisa de fatia própria, primeiro |
| 2 | **`classificador.py` já existe** e classifica *documento XML* (`nfe`/`evento`/`invalida`/`nao_suportado_sat`) — nada a ver com categoria de produto | ⛔ Nenhum módulo novo pode se chamar `classificador`/`classificacao`. Nomes reservados abaixo |
| 3 | `test_banco.py:66` usa `TABELAS_ESPERADAS <= _nomes(...)` — **subconjunto** | ✅ O esquema pode crescer sem quebrar o teste. É o padrão certo, e o contraexemplo do que faltou na 006 |
| 4 | `test_itens_no_json.py:124` usa `assert list(item) == CHAVES_DO_ITEM` — **igualdade estrita e ordenada** | 🔴 Qualquer story que exponha categoria no JSON quebra esse teste. Ele **já está publicado** |
| 5 | `importador.py` tem 5.975 bytes e `serializacao.py` 5.395 | Mandar um deles inteiro como alvo custa ~1,5k só de arquivo. **Uma tarefa, um arquivo alvo** |

### Nomes de módulo reservados aqui

Para não colidir com o `classificador.py` existente, e para manter cada alvo pequeno:

| Módulo novo | Papel |
| ----------- | ----- |
| `migracoes.py` | versão de schema e os passos de migração |
| `produtos.py` | identidade de produto (§3) |
| `categorizacao.py` | a cascata (§4) |
| `taxonomia.py` | edição de categorias |
| `eval_llm.py` | o harness de eval |

⭐ **Por que módulo novo em vez de engordar `banco.py`:** pela fórmula, o alvo entra no turno 1 a
cada tarefa. Se as 5 tabelas novas forem para dentro do `banco.py`, ele vai de 3.023 para ~6.000
bytes e a **terceira tarefa da story 007 chega a 5,9k**, raspando o teto de 6k. Com `migracoes.py`
começando do zero, a mesma tarefa fica em ~5,6k. É a diferença entre caber e ter de partir.

---

## As 7 fatias

### 007 — Migração versionada e o esquema da classificação

| | |
| - | - |
| **Escopo** | pôr o banco sob controle de versão e criar as tabelas do §2, sem carregar nenhum dado |
| **Entrega** | `PRAGMA user_version`; as 5 tabelas (`categorias`, `ncm_ancora`, `produtos`, `tags`, `produto_tags`); os dois índices únicos parciais; o `ALTER TABLE itens ADD COLUMN produto_id` + índice; banco novo e banco da spec 01 chegam ao mesmo estado |
| **NÃO entrega** | ⛔ nenhum seed, nenhuma categoria, nenhum NCM, nenhuma lógica de classificação, nenhuma mudança em `notas`/`itens` já existentes |
| **Tarefas** | 3 · alvo `migracoes.py` (novo) + `banco.py` (toque mínimo) |

1. `PRAGMA user_version` e o executor de migrações em ordem (v0 → v1) — ~4,4k
2. O DDL das 5 tabelas e os índices parciais — ~5,1k
3. O `ALTER TABLE` dentro da migração + o caso do **banco legado** já populado — ~5,6k

⚠️ **O `ALTER TABLE` é o único ponto não-idempotente da spec inteira.** É por isso que ele é
tarefa isolada, e a última: se a migração v1 falhar no meio, o teste tem de provar que reabrir o
banco não duplica coluna nem perde dado.

---

### 008 — Identidade de produto

| | |
| - | - |
| **Escopo** | §3 — resolver *que produto é* cada item, sem dizer nada sobre categoria |
| **Entrega** | `normalizar_descricao`; resolução por GTIN; resolução por `descricao_normalizada + emit_cnpj`; criação/casamento em `produtos` com `identidade_origem` correto |
| **NÃO entrega** | ⛔ nenhuma categoria (`categoria_id` fica NULL), ⛔ não altera o fluxo de importação ainda, ⛔ não mexe em números/unidades na normalização |
| **Tarefas** | 3 · alvo `produtos.py` (novo) |

1. `normalizar_descricao` — minúsculas, sem acento, pontuação fora, espaços colapsados — ~4,3k
2. Resolver/criar por GTIN — ~4,8k
3. Resolver/criar por texto+CNPJ, e o `identidade_origem='texto'` como sinal de *best-effort* — ~5,3k

🔴 **Esta é a story mais exposta ao *Achado Q*.** A normalização de acento mexe com `unicodedata` e
com strings de escape — e foi uma barra comida por heredoc que criou o teste impossível da 006.
📋 **Monte toda barra invertida com `chr(92)`** ao escrever estes testes, e releia o arquivo gravado
antes de commitar.

⚠️ **A honestidade do §3 é requisito, não comentário:** casar entre lojas só é confiável por GTIN.
O teste tem de provar que `norm+CNPJ` **diferente de CNPJ** gera produtos **distintos**.

---

### 009 — Cascata determinística: memória, NCM e bucket

| | |
| - | - |
| **Escopo** | §4 passos **1, 2 e 4**. É o MVP que a spec declara: *"base (memória+NCM+bucket) é o MVP e funciona sem LLM"* |
| **Entrega** | busca do **prefixo NCM mais longo**; a ordem de prioridade da cascata; `origem='manual'` nunca sobrescrito; resto vai pro bucket |
| **NÃO entrega** | ⛔ LLM (é a 012), ⛔ eval, ⛔ edição de taxonomia (é a 011), ⛔ integração com a importação (é a 013) |
| **Tarefas** | 3 · alvo `categorizacao.py` (novo) |

1. Prefixo mais longo em `ncm_ancora` (2, 4 ou 8 dígitos) — ~4,4k
2. A cascata com a ordem de prioridade e o bucket — ~5,0k
3. Memória por produto: `manual` e `memoria` nunca sobrescritos; realimentação — ~5,4k

🔴 **O maior risco de oráculo do recorte inteiro está aqui** — ver a seção própria, abaixo.

---

### 010 — Seed: taxonomia e mapa NCM âncora

| | |
| - | - |
| **Escopo** | carregar a taxonomia do report e o mapa NCM curado |
| **Entrega** | o **carregador** idempotente do seed, e os dados |
| **NÃO entrega** | ⛔ nenhuma lógica de classificação |
| **Tarefas** | 2 · alvo `seed.py` (novo) + arquivo de dados |

🔴 **Esta story é meio dado, meio código — e o loop só serve para a metade de código.**

O modelo local escreve o **carregador**. ⛔ **Os dados NÃO vão na mensagem para ele:** 43 linhas de
categoria mais um mapa NCM de dezenas ou centenas de prefixos estourariam o turno 1 sozinhos, e
curadoria não é trabalho que se delega a um modelo de 14b sem oráculo. O arquivo de dados é escrito
fora do loop e revisado por você.

⚠️ **Dois insumos travam esta story, e nenhum deles é código** — ver *Insumos pendentes*, abaixo.

---

### 011 — Edição de taxonomia

| | |
| - | - |
| **Escopo** | o último bloco do §4 |
| **Entrega** | apagar categoria com histórico → produtos vão pro bucket; renomear → vínculos intactos (id estável); mover subcategoria → vínculos seguem |
| **NÃO entrega** | ⛔ UI, ⛔ HTTP, ⛔ validação de quem pode editar |
| **Tarefas** | 2 · alvo `taxonomia.py` (novo) |

1. Renomear e mover (os dois casos em que o vínculo **sobrevive**) — ~4,5k
2. Apagar (o único caso em que o vínculo **muda**: vai pro bucket) — ~5,0k

⭐ **Candidata a fusão com a 010** (ambas só mexem em `categorias`; juntas dariam 4 tarefas).
Decisão sua — está na parada, abaixo.

---

### 012 — LLM opt-in e o harness de eval

| | |
| - | - |
| **Escopo** | §4 passo 3, e o invariante do eval no §6 |
| **Entrega** | chamada Ollama atrás de `OLLAMA_URL`/modelo/limiar por env var; saída **restrita** à lista + `nao_sei`; fora da lista, `nao_sei` ou confiança < limiar → bucket; o harness que roda sobre um gold rotulado e emite acurácia por categoria, matriz de confusão e % no bucket |
| **NÃO entrega** | ⛔ ligar o LLM por padrão, ⛔ tags automáticas, ⛔ regras por regex (§5 as veta), ⛔ a decisão de aprovar o LLM — essa é sua, depois de ver os números |
| **Tarefas** | 3 · alvo `eval_llm.py` (novo) + `categorizacao.py` (existente até lá) |

🔴 **É aqui que o kit não alcança.** Seção própria, abaixo.

---

### 013 — Integração: a classificação entra no fluxo real

| | |
| - | - |
| **Escopo** | ligar o que as 007–011 construíram ao caminho que já existe |
| **Entrega** | a importação resolve identidade e grava `itens.produto_id`; a saída JSON expõe a categoria do produto |
| **NÃO entrega** | ⛔ nenhuma lógica nova de classificação |
| **Tarefas** | 2 · **um arquivo alvo por tarefa** |

1. `persistencia.py` (2.475 B) — resolver produto ao inserir item — ~5,2k
2. `serializacao.py` (5.395 B) — categoria no JSON — ~5,9k ⚠️ raspa o teto

⛔ **Não junte `importador.py` (5.975 B) numa dessas duas tarefas.** Alvo + teste + mensagem
passaria de 6,3k. Se a importação precisar mudar, é uma **terceira** tarefa com ele sozinho.

🔴 **Esta é a única story que toca código já publicado no `origin`.** É também onde vencem três
dívidas técnicas — ver abaixo.

---

## Ordem e dependências

```
007 (migração + esquema)
 │
 ├──► 008 (identidade) ──┐
 │                       ├──► 013 (integração)   ← toca código publicado
 ├──► 009 (cascata) ─────┘
 │     │
 │     ├──► 012 (LLM + eval)    ← opt-in; pode ficar por último sem prejuízo
 │     │
 ├──► 010 (seed)    ← travada por insumo de produto, não por código
 └──► 011 (taxonomia)
```

| Dependência | Por quê |
| ----------- | ------- |
| tudo → **007** | sem as tabelas e sem versão de schema, nada mais existe |
| 013 → 008 + 009 | integrar exige ter o que integrar |
| 012 → 009 | o LLM só vê *"o que sobrou"* depois que memória e NCM rodaram |
| 011 → 007 | "apagar → bucket" precisa do bucket, que nasce no esquema |
| 010 → 007 apenas | ⭐ **o seed NÃO bloqueia a 009** |

⭐ **A decisão de ordem que mais importa: o seed (010) vem DEPOIS da cascata (009), não antes.**
Os testes da cascata criam suas próprias categorias e prefixos — não precisam do seed de produção.
Pôr o seed antes colocaria a curadoria do NCM, que depende de você, no **caminho crítico** do
código. Deixando-o depois, as 007, 008 e 009 rodam enquanto o mapa NCM é curado em paralelo.

---

## Riscos de oráculo antecipados

> O item que a 006 ensinou: **igualdade estrita que uma tarefa posterior quebra.** Aqui o risco é
> pior, porque atravessa **stories**, e um teste de story anterior já estará commitado — parte
> dele, publicado.

| # | Onde | O que vai crescer | Como escrever o teste |
| - | ---- | ----------------- | --------------------- |
| **R1** 🔴 | **009 → 012**, o campo `origem` | a 009 conhece `manual`, `memoria`, `ncm` e NULL. A 012 acrescenta **`llm`** e passa a gravar `confianca` | ⛔ nunca `assert origem in {conjunto fechado}` nem comparar a linha inteira de `produtos`. Asserte **o campo que a tarefa decide**, e nada mais |
| **R2** 🔴 | **008/009 → 013**, o JSON | `test_itens_no_json.py:124` faz `assert list(item) == CHAVES_DO_ITEM` — igualdade **estrita e ordenada**, já publicada | a 013 **vai** ter de alterar esse teste. ⚠️ Alterá-lo é legítimo (a spec 02 manda a saída crescer), mas tem de ser **na tarefa que acrescenta a chave**, e declarado no P1 — não descoberto no P3 |
| **R3** ⚠️ | **007 → 010**, o esquema | `test_banco.py` já usa subconjunto (`<=`) | ✅ risco **já neutralizado**. Mantenha o padrão nas tabelas novas: `<=`, nunca `==` |
| **R4** ⚠️ | dentro da **008**, a normalização | a tarefa 1 normaliza; a 3 casa por texto+CNPJ | se a tarefa 1 fixar a saída exata de `normalizar_descricao` para uma descrição com acento **e** a 3 mudar a normalização, a 1 quebra. Fixe **propriedades** (sem acento, sem pontuação, espaço simples), não a string inteira |
| **R5** ⚠️ | dentro da **007** | a tarefa 1 cria a versão, a 2 as tabelas, a 3 a coluna | ⛔ a tarefa 1 não pode afirmar `user_version == 1` se a 2 e a 3 fazem parte da mesma v1. Decida na tarefa 1 **quantas versões existem** e escreva isso na spec da story |

⭐ **A regra geral que sai daqui:** *a igualdade estrita mora no módulo da última tarefa que mexe
naquela saída.* Antes dela, subconjunto ou prefixo.

---

## O que a spec 02 pede e o kit NÃO verifica

🔴 **Isto é o item que precisa ser dito antes, não depois.**

O kit prova uma coisa só: `pytest` verde num processo local, sem rede. Três exigências da spec 02
ficam fora disso:

### 1. A chamada ao LLM (§4 passo 3)

O §1 diz *"sem rede além do Ollama configurável"*. Um teste que **de fato** chame o Ollama seria não
determinístico e dependeria do serviço no ar — o `rodar_passo3.py` reprovaria de forma aleatória.

✅ **O que dá para verificar:** o **contrato em volta** da chamada, com o cliente dublado — que
resposta fora da lista vira bucket, que `nao_sei` vira bucket, que confiança abaixo do limiar vira
bucket, que a env var é lida. Isso cobre o invariante *"nunca inventa categoria"*.
⛔ **O que não dá:** que o modelo **acerte**.

### 2. O harness de eval (§6)

✅ **Verificável:** a **aritmética** do harness — dado um gold rotulado e um conjunto de predições
fixas, a acurácia por categoria, a matriz de confusão e o % no bucket saem certos. É teste puro.
⛔ **Não verificável:** se os números são **bons**. A spec já diz isso — *"Bar de aprovação:
chamada do Gui após ver os números"*. O harness é um instrumento de medida; ele não tem limiar, e
⛔ **não invente um**.

### 3. O conjunto rotulado (gold humano)

⚠️ **Não existe ainda, e o kit não o produz.** É trabalho humano: alguém olha N produtos reais e
escreve a categoria certa. Sem ele o harness roda vazio e a 012 não tem como se declarar pronta.

📋 **Consequência para o recorte:** a **012 é a única story cuja definição de pronto não cabe
inteira no kit.** As 007–011 e a 013 fecham com suíte verde. A 012 fecha com suíte verde **mais**
uma decisão sua sobre números.

---

## Insumos pendentes — travam a 010, não o resto

| # | Insumo | Estado real |
| - | ------ | ----------- |
| I1 | **A taxonomia seed** | ✅ existe: **§5** do `Self_Hosting/notas_fiscais/report_nfe_central.md` — 10 categorias de nível 1 e 32 subcategorias, mais o bucket |
| I2 | **O mapa NCM→categoria curado** | ⛔ **não existe.** O §9 do mesmo report o lista como pendência: *"construir na fase de build — dados do Claude + revisão do Gui"* |

⚠️ **Duas correções de rota que o planejamento encontrou:**

1. 📌 **A spec 02 aponta para a seção errada.** Ela diz *"seed da taxonomia final (§9 do report)"*,
   mas o §9 é *"Pendências / abertos"* — a taxonomia está no **§5**.
2. 📌 **A spec diz "travada"; o report diz que não está.** A spec 02 lista o seed entre as
   *"decisões travadas"*, mas o §9 do report registra *"Seed final — o Gui pode ainda
   tirar/renomear/adicionar categorias"*. As duas frases não podem valer juntas.

⚠️ **E o report está fora dos dois repositórios** (mora em `Self_Hosting/`). O seed precisa entrar
no clone como dado versionado antes da 010 — hoje ele não é rastreável pelo `git` do projeto.

---

## Dívidas técnicas que este recorte faz vencer

O handoff mantém 5 dívidas anotadas, pagas *"quando uma story tocar aquele código"*. O recorte diz
exatamente quando:

| Dívida | Vence na | Por quê |
| ------ | -------- | ------- |
| **(a)** `persistir_nota` chama `conexao.commit()` | **013**, tarefa 1 | resolver produto e inserir item **têm de ser a mesma transação**; com o commit onde está, um item entra sem produto se a resolução falhar depois |
| **(c)** o `except ValueError` envolve `persistir_nota` | **013** | 🔴 **a mais séria.** Com a classificação dentro do fluxo, um erro de categorização passaria a ser relatado como *"XML inválido"*. Mascarar diagnóstico numa cascata de 4 níveis é caro |
| **(d)** `importar` decodifica e classifica cada arquivo duas vezes | **013**, só se a terceira tarefa existir | não corrompe nada; pague se já estiver com `importador.py` aberto |
| **(b)** `classificar_xml` pega o primeiro `mod` | — | ⛔ não vence: nenhuma story da spec 02 toca `classificador.py` |
| **(e)** `getattr(..., "value", ...)` nos três campos | — | ⛔ não vence |

⚠️ **A (a) e a (c) não são opcionais na 013.** Não são limpeza: são pré-condição para que a
integração não fique com um buraco de transação e um diagnóstico mentiroso.

---

## Resumo em uma tabela

| Story | Fatia | Tarefas | Alvo | Depende de |
| ----- | ----- | ------- | ---- | ---------- |
| 007 | migração versionada + esquema | 3 | `migracoes.py` | — |
| 008 | identidade de produto | 3 | `produtos.py` | 007 |
| 009 | cascata memória+NCM+bucket | 3 | `categorizacao.py` | 007 |
| 010 | seed taxonomia + NCM | 2 | `seed.py` + dados | 007 · **insumo I2** |
| 011 | edição de taxonomia | 2 | `taxonomia.py` | 007 |
| 012 | LLM opt-in + eval | 3 | `eval_llm.py` | 009 · **gold humano** |
| 013 | integração no fluxo real | 2–3 | módulos publicados | 008 · 009 |

**18–19 tarefas ao todo.** ⚠️ Estimativa de turno 1 entre **4,3k e 5,9k** — nenhuma tarefa acima do
teto de 6k, mas **três raspam**: a 007.3, a 013.2 e a 013.3. ⛔ O remeço real é no P2 de cada story,
com os testes escritos; se qualquer uma passar de 6k lá, parta a tarefa.

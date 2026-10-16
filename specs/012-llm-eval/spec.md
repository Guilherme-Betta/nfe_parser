# Spec — story 012: LLM opt-in e o harness de eval

> O passo 3 da cascata da spec 02 (§4) e o instrumento que decide se ele é ligado (§6).
> ⛔ **O harness não tem limiar de aprovação.** Ele mede; quem decide é o Gui, depois de ver os números.

---

## 1. O que a story entrega

| | |
| - | - |
| **Entrega** | a conversa com o Ollama e o **contrato da resposta** (`llm.py`); o **degrau do LLM** na cascata (`classificacao_llm.py`); a varredura passando o LLM adiante; o **harness** que roda sobre um gold e emite acurácia por categoria, matriz de confusão e fração no bucket (`eval_llm.py`) |
| **NÃO entrega** | ⛔ o LLM ligado por padrão, ⛔ tags (§5 da spec 02), ⛔ regras por regex, ⛔ **a decisão de aprovar o LLM**, ⛔ um limiar escolhido por nós |
| **Tarefas** | 4, um arquivo alvo por tarefa |

### O gold

⭐ **Existe, e é pequeno de propósito:** 19 produtos rotulados pelo Gui em 2026-09-28, tirados das
notas dele. ⛔ **Ele NÃO mora neste repositório** — este repositório é público, e o gold são compras
reais. Mora no repositório privado do workflow; o harness lê um **caminho**.

📋 **Nenhum teste desta story usa o gold.** Os oráculos usam gold **sintético**: o que o kit verifica
é a **aritmética** do harness, que ou sai certa ou não sai. ⛔ Se os números são *bons* o kit não
verifica — ver §6.

---

## 2. 🔴 A descoberta do P1: o degrau do LLM ⛔ NÃO entra em `categorizacao.py`

O recorte punha o degrau lá, e a docstring de `classificar_produto` promete: *"a story 012
acrescenta o degrau do LLM editando esta funcao, que e uma linha de diff"*. ⛔ **Não cabe**, e por
duas razões independentes:

### 2.1 — A "linha de diff" custa o arquivo inteiro

A promessa foi escrita na 009, quando o kit ainda rodava com `--edit-format diff`. Desde a 009 o P3
roda com **`whole`** — e com `whole` o modelo devolve o **arquivo inteiro**, qualquer que seja o
tamanho da mudança.

| | bytes | tokens |
| - | ----- | ------ |
| `categorizacao.py` hoje | 9.817 | — |
| entrada: alvo + teste (~5,5 KB) + mensagem (~4,5 KB) | ~19.800 | `sent` ≈ 0,66k + 19.800/3,4 ≈ **~6,5k** |
| saída: o arquivo reescrito, maior que o de hoje | ~10.500 | **~3,1k** |
| **total contra `num_ctx: 8192`** | | 🔴 **~9,6k — estoura** |

⛔ **Não há mensagem enxuta que resolva isso:** só o alvo, na ida e na volta, já consome ~5,8k.

### 2.2 — `categorizacao.py` não faz I/O de rede, e isso vale a pena manter

O cabeçalho do módulo declara que ele é a cascata **determinística**. Um degrau que conversa com um
serviço HTTP muda a natureza do módulo, e todo teste da cascata passaria a ter de pensar em rede.

### ⭐ O remédio: o degrau nasce num módulo próprio, por COMPOSIÇÃO

```python
def classificar_produto_com_llm(conexao, produto_id, ncm, llm=None) -> int:
```

1. chama `classificar_produto` — a cascata da 009, **intacta**;
2. se a `origem` depois dela ainda é NULL (o produto caiu no bucket) **e** há um `llm`, pergunta a ele;
3. se a resposta é válida, grava a categoria, `origem = 'llm'` e a `confianca`.

🔴 **A ordem da spec 02 sai de graça:** memória e manual o passo 1 já protege (a `origem` não é NULL,
então o LLM nem é consultado); NCM já resolveu (idem); só o que caiu no bucket chega ao LLM. ⭐ É
exatamente o *"só pro que sobrou"* do §4.

⚠️ **Custo assumido:** o produto que o LLM resgata é gravado **duas vezes** na mesma transação —
primeiro no bucket, pela cascata, depois na categoria do LLM. ⛔ Ninguém de fora vê o estado do meio.

📋 **`categorizacao.py` só muda no P4, e só na documentação:** a frase da "linha de diff" deixa de ser
verdade e passa a apontar para cá.

---

## 3. As decisões de desenho

### D1 — o LLM é um PARÂMETRO, e `None` é o padrão *(o "opt-in")*

⛔ Nenhum módulo lê variável de ambiente sozinho no meio da cascata. Quem quer o LLM **constrói** um
e o **passa**: `classificar_produtos_pendentes(conexao, llm=...)`. Sem o argumento, tudo se comporta
exatamente como na 013.

⭐ Isso é o que torna o degrau **testável sem Ollama nenhum**: nos oráculos, o `llm` é uma função
Python de três linhas que devolve o que o teste quer.

### D2 — o contrato do `llm`: `llm(descricao, slugs) -> (slug, confianca) | None`

| Recebe | Devolve |
| ------ | ------- |
| a descrição do produto e a lista de slugs permitidos | `(slug, confianca)` se a resposta passou em **todas** as regras da D3 |
| | `None` em qualquer outro caso |

⭐ `None` significa **"não sei"**, venha de onde vier: o modelo disse `nao_sei`, inventou categoria,
mandou JSON quebrado, ou teve confiança baixa. ⛔ O degrau não precisa distinguir, e não distingue.

### D3 — a resposta só vale se passar em TODAS estas, e quem confere é `interpretar_resposta`

1. é JSON, e é um objeto;
2. `categoria` está **na lista** que foi enviada — o que exclui `nao_sei` sem regra própria;
3. `confianca` é número (⛔ `bool` não conta, mesmo sendo `int` em Python), entre 0 e 1;
4. `confianca >= limiar`.

🔴 **O limiar mora aqui, e não no degrau.** O degrau é política do banco ("o que gravar"); o limiar é
política da resposta ("em que acreditar"). E é **aqui** que o eval precisa dele, porque o eval chama
o mesmo `llm` que a produção.

### D4 — ⛔ NINGUÉM escolhe o limiar por padrão

`llm_do_ambiente()` lê três variáveis:

| Variável | Sem ela |
| -------- | ------- |
| `OLLAMA_URL` | devolve `None` — o LLM está **desligado**, e isso não é erro |
| `OLLAMA_MODELO` | 🔴 `ValueError`, se `OLLAMA_URL` estiver definida |
| `LLM_LIMIAR` | 🔴 `ValueError`, se `OLLAMA_URL` estiver definida |

⛔ **Não há modelo padrão nem limiar padrão, e não é esquecimento.** Um limiar padrão seria um número
escolhido por nós — exatamente o que o §248 do recorte proíbe. Quem liga o LLM diz **com que modelo**
e **a partir de que confiança**, e o eval é o que dá base para essa escolha.

📋 O repositório documenta **os nomes** das variáveis. ⛔ Nenhum valor, nenhum `.env`.

### D5 — a conversa com o Ollama usa só a biblioteca padrão

`urllib.request`, `POST {OLLAMA_URL}/api/generate`, com `"stream": false`, `"format": "json"` e
`"temperature": 0`. ⛔ Nenhuma dependência nova no `pyproject.toml`.

⚠️ `"format": "json"` faz o Ollama restringir a saída a JSON válido — mas ⛔ **não** restringe a
categoria à lista. É por isso que a regra 2 da D3 existe mesmo com o formato forçado.

⚠️ **Erro de rede SOBE.** Quem ligou o LLM e apontou para um Ollama fora do ar precisa saber — ⛔ e
não descobrir semanas depois que tudo foi para o bucket em silêncio.

### D6 — o que o LLM vê: `descricao_exemplo`, e só ela

É o `xProd` cru, como veio da nota — o mesmo texto que o gold do Gui tem. ⛔ Nem NCM, nem emitente
no MVP. Produto **sem** `descricao_exemplo` não é enviado: fica no bucket.

⚠️ **O gold do Gui mostrou o custo disso** — ver §7.

### D7 — a lista enviada é a das categorias que EXISTEM, ⛔ sem o bucket

`SELECT slug FROM categorias WHERE is_bucket = 0 ORDER BY slug`. Categoria apagada não está lá (a
lápide da 011 guarda o slug **fora** de `categorias`), então o LLM nunca a recebe.

⭐ O `ORDER BY` não é estética: sem ele a lista muda de ordem entre execuções, e o prompt também.

### D8 — o degrau confere o slug NO BANCO antes de gravar *(nunca inventa categoria)*

Mesmo que o `llm` devolva um slug, o degrau busca `id` por `slug` com `is_bucket = 0`. ⛔ Não achou,
não grava. ⭐ É a segunda barreira do invariante *"nunca inventa categoria"* da spec 02: a primeira é
a D3, e ela mora num módulo que o degrau **não controla** — o `llm` é um parâmetro, e pode ser
qualquer função.

### D9 — a varredura passa o `llm` adiante, e ⛔ não muda mais nada

`classificar_produtos_pendentes(conexao, llm=None)` chama `classificar_produto_com_llm` no lugar de
`classificar_produto`. ⭐ A contagem de resgatados já está certa **sem mudança**: ela compara a
`origem` com `is not None`, de propósito, desde a 013 — e `'llm'` não é `None`.

🔴 **É aqui que o risco R1 morde, e ele ⛔ não morde:** nenhum teste publicado fecha o conjunto de
`origem`.

### D10 — o formato do gold: CSV com `;`, e `esperado` vazio é "não há categoria para isto"

```
descricao;esperado
MACA FUJI KG;mercado-frutas
ITEM SEM LUGAR 1UN;
```

⭐ `;` e não `,` porque é o que o Excel em português grava. `utf-8-sig` na leitura porque o Excel põe
BOM. ⛔ A segunda coluna é **slug**, e não o rótulo livre do Gui: a tradução é feita uma vez, à mão,
no P4, e o rótulo original fica guardado ao lado.

🔴 **`esperado` vazio NÃO é erro do LLM.** São os produtos para os quais a taxonomia não tem lugar
(no gold do Gui: molho, dilatador nasal, smoothie, mochila). O LLM não tem como acertar uma categoria
que não recebeu — contá-los na acurácia mediria **a taxonomia**, e não o LLM. Eles saem num número
próprio.

### D11 — o que o harness emite

| Chave | O quê |
| ----- | ----- |
| `avaliados` | linhas com `esperado` preenchido |
| `acertos` / `acuracia` | acertos sobre `avaliados`; `None` se `avaliados == 0` |
| `taxa_no_bucket` | fração dos `avaliados` que o LLM mandou para o bucket |
| `por_categoria` | `{slug_esperado: {"total", "acertos", "acuracia"}}` |
| `matriz` | `{esperado: {previsto: contagem}}`, com o bucket como `"uncategorized"` |
| `fora_da_taxonomia` | `{"total", "no_bucket"}` — as linhas de `esperado` vazio |

⭐ **Tudo serializa em JSON** (spec 02 §6). ⛔ Nenhuma chave `None` em dicionário: o bucket vira a
string `"uncategorized"`, que é o slug que a spec 02 fixou para ele.

⚠️ **O acerto é EXATO.** Esperado `mercado-laticinios` e previsto `mercado` é erro. ⛔ Não existe
"acerto no grupo" no MVP — ver §7.

---

## 4. Os critérios de aceite congelados

### C1 — a conversa com o LLM — `tests/test_llm_contrato.py`

| # | Critério |
| - | -------- |
| C1.1 | resposta válida acima do limiar → `(slug, confianca)` |
| C1.2 | `nao_sei` → `None` |
| C1.3 | categoria **fora da lista** → `None` |
| C1.4 | confiança **abaixo** do limiar → `None`; **igual** ao limiar → aceita |
| C1.5 | texto que não é JSON, JSON que não é objeto, confiança que não é número, `bool`, ou fora de 0..1 → `None` |
| C1.6 | o prompt contém a descrição, cada slug e a palavra `nao_sei` |
| C1.7 | o `llm` de `criar_llm` faz `POST` em `/api/generate` com o modelo, `stream` falso e `format` `json`, e interpreta a resposta |
| C1.8 | `llm_do_ambiente`: sem `OLLAMA_URL` → `None`; com ela e sem `LLM_LIMIAR` ou sem `OLLAMA_MODELO` → `ValueError` |

### C2 — o degrau do LLM — `tests/test_degrau_llm.py`

| # | Critério |
| - | -------- |
| C2.1 | `llm=None` → o mesmo resultado da cascata da 009: bucket e `origem` NULL |
| C2.2 | NCM que casa → o `llm` ⛔ **não é chamado**, `origem = 'ncm'` |
| C2.3 | `origem = 'manual'` → o `llm` ⛔ **não é chamado**, nada é escrito |
| C2.4 | 🔴 produto no bucket e `llm` válido → a categoria dele, `origem = 'llm'`, `confianca` gravada |
| C2.5 | `llm` devolve `None` → bucket, `origem` NULL |
| C2.6 | 🔴 `llm` devolve slug que ⛔ não existe, ou o do bucket → bucket, `origem` NULL *(D8)* |
| C2.7 | o `llm` recebe a `descricao_exemplo` e a lista de slugs **sem o bucket**, em ordem |
| C2.8 | ⛔ não commita: um `rollback()` depois dela desfaz o degrau |

### C3 — a varredura passa o LLM — `tests/test_varredura_llm.py`

| # | Critério |
| - | -------- |
| C3.1 | 🔴 pendente sem NCM e `llm` válido → `origem = 'llm'`, e **conta** como resgatado |
| C3.2 | pendente com NCM ancorado → o `llm` ⛔ **não é chamado** |
| C3.3 | `llm` devolve `None` → bucket, e ⛔ não conta |

⭐ **O oráculo publicado da 013** (`test_varredura_pendentes.py`, 8 testes) é a guarda do resto: todos
eles chamam a varredura **sem** `llm`, e têm de continuar verdes.

### C4 — o harness — `tests/test_eval_llm.py`

| # | Critério |
| - | -------- |
| C4.1 | `carregar_gold` lê `;`, tolera BOM, e `esperado` vazio vira `None` |
| C4.2 | `prever` chama o `llm` com cada descrição e os slugs; `None` vira `None`, tupla vira o slug |
| C4.3 | `acertos` e `acuracia` sobre um gold sintético de resultado conhecido |
| C4.4 | `por_categoria` conta total e acertos **pelo esperado** |
| C4.5 | `matriz` conta os pares, com o bucket como `"uncategorized"` — e o resultado passa por `json.dumps` |
| C4.6 | `taxa_no_bucket` |
| C4.7 | 🔴 linha com `esperado` `None` ⛔ não entra em `avaliados` e vai para `fora_da_taxonomia` |
| C4.8 | gold e predições de tamanhos diferentes → `ValueError`; `avaliados == 0` → `acuracia` `None` |

---

## 5. ⚠️ O que os oráculos semeiam, e o que ⛔ não semeiam

📋 Como na 013: banco montado à mão, com `INSERT` direto. ⛔ Nenhum oráculo chama
`carregar_seed_padrao`, e ⛔ nenhum usa o gold do Gui.

⛔ **Nenhum oráculo fala com o Ollama.** O C1.7 troca `urllib.request.urlopen` por uma função falsa
(`monkeypatch`), e os C2 e C3 passam um `llm` que é uma função Python.

⛔ **Nenhum teste afirma `origem in {conjunto fechado}`** *(risco R1)*.

---

## 6. 🛑 O que o kit ⛔ NÃO verifica, e de quem é

| | Quem |
| - | ---- |
| a aritmética do harness | ✅ o kit — C4 |
| que o degrau nunca inventa categoria | ✅ o kit — C1.3, C2.6 |
| **se os números do eval são bons** | 🛑 **o Gui** |
| **que modelo usar e a partir de que limiar** | 🛑 **o Gui** |
| **se o LLM é ligado** | 🛑 **o Gui** |

---

## 7. ⚠️ O que fica ANOTADO e não vira código

O gold do Gui, com 19 produtos, já mostrou quatro coisas antes de qualquer número:

- 🔴 **Terceiro nível.** 7 dos 19 rótulos descem um nível que a taxonomia não tem (Sabonete, Iogurte,
  Frango, Tomate, Feijão, Leite, Desodorante). No CSV eles viram o nível que existe; o rótulo original
  fica guardado. ⭐ É sinal de produto: o Gui quer categorias mais finas.
- 🔴 **Categorias que faltam:** molho, sono/dilatador nasal, smoothie, algo para mochila. É a
  ressalva `adicionar_categoria` de novo, agora com exemplos reais. ⚠️ No CSV, só **molho** e
  **mochila** ficaram com `esperado` vazio: para sono e smoothie o grupo existe (`saude`,
  `restaurante-e-delivery`), e a regra da conversão é "o nível mais fundo do rótulo que existe".
- ⚠️ **Tags** ("Online", "Desnatado") — fora da spec 02 (§5). E "comprado na internet" é atributo da
  **compra**, não do produto: o mesmo item pode vir da loja e do app.
- ⚠️ **Delivery × Restaurante não está no texto do item.** Um "COMBO" de restaurante não diz
  por onde foi comprado. Quem sabe é o **emitente**, que a D6 não manda ao LLM.

E do desenho:

- ⚠️ **Produto com `origem = 'llm'` não é varrido de novo.** Se uma âncora NCM chegar depois, ele
  continua com a resposta do LLM. A spec 02 põe NCM acima do LLM — o degrau respeita isso **na hora de
  classificar**, ⛔ mas não revisita decisões já gravadas.
- ⚠️ **`confianca` antiga não é limpa** quando uma cascata posterior manda o produto para NCM ou
  bucket. Só acontece se alguém chamar a cascata num produto `llm` à mão — a varredura não o faz.
- ⚠️ **O acerto do eval é exato** (D11). "Acerto no grupo" (previu `mercado`, esperado
  `mercado-laticinios`) seria outra métrica, e ⛔ não foi inventada aqui.
- ⚠️ **`LLM_LIMIAR` não é conferido contra 0..1.** Um limiar `2` recusaria toda resposta, e o LLM
  ficaria ligado sem nunca classificar nada — sem erro. Barato de acrescentar; ⛔ não pedido.

---

## 8. Contratos acrescentados FORA do loop *(no P4)*

### C3.4 — produto sem `descricao_exemplo` ⛔ não é enviado ao LLM

🔴 **Achado pela revisão, e ⛔ NÃO pela cobertura.** A guarda da D6 é o lado direito de um `or`
(`if origem is not None or not descricao`), e a cobertura de **ramos** mede a linha do `if` — não
cada lado dele. Deu **100%** em `classificacao_llm.py` com o lado direito nunca exercitado.

📋 **Provado por mutação antes de escrever o teste:** apagar `or not descricao` deixava a suíte
inteira **verde**. Com o C3.4, acende só ele. ⭐ Mora em `test_varredura_llm.py` (4 testes), e ⛔ não
no do degrau, que já tem 8 *(Achado N)*.

### C4.7 ampliado — linha fora da taxonomia **com resposta** do LLM

🔴 **Achado pela cobertura de ramos:** `eval_llm.py` em 98%, com o ramo `32->34` descoberto. O gold
sintético só tinha linha fora da taxonomia que o LLM mandou ao bucket; `no_bucket` podia contar
**todas** as linhas de fora e nada acendia.

📋 **Provado por mutação:** `if previsto is None` → `if True` ficava verde. Com a ampliação, acende o
C4.7.

### O que também entrou no P4, e ⛔ não é contrato

- `scripts/rodar_eval.py` — a cola entre as quatro peças e um Ollama de verdade. ⛔ Sem teste: sem
  Ollama não há o que testar, e com Ollama o resultado depende do modelo.
- As docstrings dos três módulos novos, e a correção de duas publicadas: a de `classificar_produto`
  (a "linha de diff" da §2) e o cabeçalho de `varredura.py`.
- ⚠️ **Os números do eval com o gold do Gui NÃO estão aqui**, porque trazem as descrições dos produtos.
  Estão no repositório privado do workflow.

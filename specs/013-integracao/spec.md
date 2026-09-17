# Spec — story 013: integração

> A story que liga o que as 007–011 construíram ao caminho que já existe.
> ⛔ **Nenhuma lógica nova de classificação** — a cascata é a da 009 e não se altera.

---

## 1. O que a story entrega

| | |
| - | - |
| **Entrega** | a importação resolve **identidade** e grava `itens.produto_id`; a saída JSON expõe a **categoria** do produto; existe a **varredura** que classifica os pendentes |
| **NÃO entrega** | ⛔ LLM (012), ⛔ eval (012), ⛔ nenhum degrau novo na cascata, ⛔ nenhuma migração |
| **Tarefas** | 4, um arquivo alvo por tarefa |

🔴 **Esta é a única story que toca código já publicado no `origin`.** As 007–011 criaram arquivos
novos quase sempre; aqui três dos quatro alvos já rodam. ⛔ O oráculo de verdade é a **suíte inteira**
(324 testes na abertura), não o módulo da tarefa.

### As cinco dívidas que vencem aqui

| # | Dívida | Onde se paga |
| - | ------ | ------------ |
| **a** | `persistir_nota` chama `conexao.commit()` | tarefa 1 — ver **D3** |
| **c** | o `except ValueError` envolve `persistir_nota` | tarefa 3 — ver **D4** |
| **d** | `importar` decodifica e classifica cada arquivo duas vezes | tarefa 3 — ver **D10** |
| **g** | não existe despachante entre as duas resoluções de `produtos.py` | tarefa 1 — ver **D2** |
| **h** | não existe `classificar_produtos_pendentes(conexao)` | tarefa 4 — ver **D5** |

⚠️ **A `a` e a `c` não são opcionais** *(§292 do recorte)*: não são limpeza, são pré-condição para a
integração não ficar com um buraco de transação e um diagnóstico mentiroso.

---

## 2. 🔴 A descoberta do P1 que mudou o recorte: a varredura ⛔ NÃO cabe em `categorizacao.py`

O recorte e o handoff previam a varredura dentro de `categorizacao.py`. ⛔ **Não cabe**, e quem diz
isso é a última linha do cabeçalho daquele módulo, escrita na story 009:

> *"⛔ Este modulo nao le `itens`: ele RECEBE o `ncm` por parametro. Quem os liga e a story 013."*

🔴 `classificar_produtos_pendentes` **tem de ler `itens`** — é de lá que vem o NCM, porque a tabela
`produtos` não tem coluna `ncm`. Pô-la em `categorizacao.py` quebraria uma invariante que o próprio
módulo declara, e que é o que mantém a cascata testável sem nota nenhuma no banco.

⭐ **Então a varredura nasce em `src/nfe_parser/varredura.py`**, módulo novo, e é ele "quem os liga"
— exatamente o papel que a 009 reservou para a 013.

⚠️ **Efeito colateral que ajuda, mas não foi a razão:** um arquivo novo é alvo vazio para o
`--edit-format whole`, e a tarefa 4 fica sem risco nenhum de regressão.

---

## 3. As decisões de desenho

### D1 — 🔴 a importação resolve IDENTIDADE; ⛔ ela NÃO classifica

`persistir_nota` grava `itens.produto_id` e para aí. O produto nasce com `categoria_id` NULL e
`origem` NULL — que é exatamente o estado "pendente" que a varredura procura.

⛔ **E `importar` NÃO chama a varredura.** A razão é dura e foi medida: `abrir_banco` **não semeia**
a taxonomia, e `categoria_do_bucket` levanta `LookupError` em banco sem `is_bucket = 1`. Um banco sem
seed é legal — os testes de importação publicados usam um — e importar nele tem de continuar
funcionando. Com a varredura dentro de `importar`, **toda** importação em banco não semeado passaria
a explodir.

⭐ A sequência de uso é de duas chamadas explícitas: `importar(...)` e depois
`classificar_produtos_pendentes(...)`. Quem decide classificar é quem tem taxonomia carregada.

### D2 — o despachante mora em `persistencia.py`, ⛔ não em `produtos.py` *(dívida g)*

```python
def resolver_produto_do_item(conexao, item, emit_cnpj):
    if item["gtin"]:
        return resolver_produto_por_gtin(conexao, item["gtin"], item["descricao"])
    return resolver_produto_por_texto(conexao, item["descricao"], emit_cnpj)
```

🔴 A regra de despacho é uma política sobre **item de nota**, e `produtos.py` declara no cabeçalho
que não sabe o que é um item: ele fala de GTIN e de texto+CNPJ, nunca de `itens`. `persistencia.py` é
o módulo que existe justamente para transformar item de nota em linha de banco. ⭐ É lá que a política
pertence.

⚠️ `gtin` vazio **e** `emit_cnpj` vazio levanta `ValueError`, vindo de `resolver_produto_por_texto`.
⛔ Não se engole: ver **D4**.

### D3 — `persistir_nota` ⛔ não commita mais; quem commita é `importar` *(dívida a)*

Resolver o produto e inserir o item **têm de ser a mesma transação**. Com o `commit()` onde estava, a
nota e os itens já estariam gravados quando a resolução de um item posterior falhasse — e o banco
ficaria com item sem produto, sem sintoma nenhum.

⭐ A regra passa a ser a mesma que `produtos.py`, `categorizacao.py`, `seed.py` e `taxonomia.py` já
anunciam: **quem abriu a transação é que a fecha**. Quem abre o lote é `importar`, e é ele que ganha
o `commit()` — ver **D11**.

### D4 — o `except ValueError` cobre SÓ `extrair_nota` *(dívida c — a mais séria)*

```python
try:
    extraido = extrair_nota(texto)
except ValueError as e:
    resultado = "invalida"
    detalhe = str(e)
else:
    resultado = persistir_nota(conexao, extraido, importacao_id)
    chave = extraido["nota"]["chave"]
```

🔴 O `else` não é estilo: é o que tira `persistir_nota` de dentro do `try` sem precisar de variável de
controle. Com a identidade dentro do fluxo, um `ValueError` da resolução passaria a ser registrado
como *"XML inválido"* — e um lote inteiro sairia marcado com um diagnóstico falso.

⭐ **E o mesmo remédio vai em `_processar_evento`**, que tem o defeito idêntico: `aplicar_cancelamento`
está dentro do `try` que rotula `'invalida'`. ⚠️ Não estava na dívida `c`, que só nomeava
`persistir_nota` — mas é o mesmo defeito, na função ao lado, e o arquivo já está aberto.

⚠️ **Consequência assumida:** um erro de persistência agora **derruba o lote**. É o que se quer. A
alternativa seria um `resultado` novo em `importacao_arquivos`, e a coluna tem
`CHECK (resultado IN (...))` fechado — mudá-la exigiria a dívida `f` (`criar_esquema` virar migração
v0), que ⛔ não vence nesta story.

### D5 — pendente é `origem IS NULL`, ⛔ e nunca `categoria_id IS NULL` *(dívida h)*

```python
def classificar_produtos_pendentes(conexao) -> int:
```

🔴 É o mesmo erro que a 009 já nomeou no cabeçalho de `categorizacao.py`: *"o que protege um produto é
a `origem`, NÃO o fato de ele já ter categoria"*. Produto no bucket **tem** `categoria_id` preenchido
e `origem` NULL — e é justamente ele que a varredura existe para resgatar quando o mapa NCM cresce.
Uma varredura que procurasse `categoria_id IS NULL` nunca mais olharia para o bucket.

⚠️ `origem IS NULL` cobre os dois casos de uma vez: produto recém-criado pela importação, e produto
que caiu no bucket. `'manual'`, `'memoria'` e `'ncm'` ficam de fora — os dois primeiros porque a
cascata os respeita, o terceiro porque já está resolvido.

### D6 — o NCM de um produto é o do item MAIS RECENTE

`produtos` não tem coluna `ncm`, e um produto pode ter vários itens com NCMs diferentes — duas lojas
descrevem a mesma caixa de arroz de jeitos diferentes, e às vezes classificam diferente também.

⭐ A varredura usa o item de maior `id`, que é o mais recentemente inserido. ⚠️ É uma escolha, não uma
verdade: a informação mais nova é a mais provável de estar certa, e `ORDER BY id DESC LIMIT 1` é
determinístico. ⛔ Sem `ORDER BY` o SQLite não garante ordem nenhuma, e o defeito passaria
despercebido em banco pequeno.

⚠️ Produto pendente **sem item nenhum** recebe `ncm = None` e vai para o bucket — a cascata já tem
resposta pronta para NCM vazio *(`buscar_categoria_por_ncm` devolve `None`)*.

### D7 — o item no JSON ganha `categoria_slug` e `categoria`; ⛔ não ganha `produto_id` nem `origem`

⭐ O par segue o idioma que o módulo já estabeleceu com dinheiro: **uma fonte de verdade e uma
apresentação**. `categoria_slug` é o identificador estável, com o qual se agrupa e se faz conta;
`categoria` é o nome, para ler.

⛔ `produto_id` fica **fora** pela regra que `_itens_da_nota` já aplica a `id` e `nota_chave`: chave
artificial do SQLite não sai no JSON.

⛔ `origem` fica **fora** por causa do risco R1: é o campo a que a 012 vai acrescentar `'llm'`, e
expô-lo agora convidaria consumidores a fechar o conjunto em cima dele.

### D8 — `LEFT JOIN`, ⛔ nunca `INNER`

```sql
FROM itens i
LEFT JOIN produtos p ON p.id = i.produto_id
LEFT JOIN categorias c ON c.id = p.categoria_id
```

🔴 Com `INNER`, todo item sem produto — e todo item de nota importada **antes** desta story —
desapareceria da saída JSON. Uma nota perderia itens em silêncio, e o total deixaria de bater com
`valor_total`. ⛔ Este é o pior defeito possível na tarefa 2, e por isso tem oráculo próprio (C2.6).

### D9 — as duas chaves aparecem SEMPRE, com `None` quando não há categoria

⛔ Não são chaves opcionais. Item sem produto, produto sem categoria e nota antiga saem todos com
`"categoria_slug": null, "categoria": null`. Chave que some conforme o dado obriga quem consome a
testar presença antes de ler — e o `None` já diz a mesma coisa, de um jeito só.

⭐ Item no bucket sai com `"categoria": "Não Classificado"`, ⛔ e não com `null`: ele **está**
classificado no bucket, e isso é diferente de não ter produto.

### D10 — `importar` decodifica e classifica cada arquivo UMA vez *(dívida d)*

O laço do `.zip` já decodifica e chama `classificar_xml` para rotear entre `notas` e `eventos`, e
`_processar_arquivo` refazia as duas coisas. ⭐ A tupla passa a carregar `texto` e `classificacao`
junto, e as duas funções recebem prontos.

⚠️ `conteudo_bytes` continua indo junto: ele é o insumo do `sha256`, e o hash é do arquivo, ⛔ não do
texto decodificado.

### D11 — ⛔ nenhuma função nova chama `commit`; a única exceção é `importar`

`resolver_produto_do_item` e `classificar_produtos_pendentes` ⛔ não commitam, ⛔ não fazem rollback,
⛔ não abrem transação. `importar` commita **uma vez, no fim**, porque é ele quem abre o lote.

⚠️ ⛔ `importar` não commita no meio do laço: um lote é tudo ou nada.

### D12 — 🔴 `test_itens_no_json.py` é ALTERADO na tarefa 2, e isso é legítimo *(risco R2)*

O §213 do recorte marcou isto antes de a story começar: `test_itens_no_json.py:124` faz
`assert list(item) == CHAVES_DO_ITEM`, igualdade **estrita e ordenada**, já publicada no `origin`.

⭐ A spec 02 manda a saída crescer, então acrescentar chave é o contrato novo — ⛔ e não uma quebra.
📋 A alteração é de **duas linhas** na lista `CHAVES_DO_ITEM`, feita na tarefa que acrescenta as
chaves, declarada aqui no P1, e ⛔ nunca descoberta no P3.

⚠️ O teste alterado é oráculo publicado: quem o altera é **o P2 desta sessão, à mão**, ⛔ nunca o
modelo local — ele recebe testes por `--read`.

---

## 4. Os critérios de aceite congelados

### C1 — `persistir_nota` resolve identidade e grava `itens.produto_id` — `tests/test_item_resolve_produto.py`

| # | Critério |
| - | -------- |
| C1.1 | item **com** `gtin` → `itens.produto_id` aponta para produto com `identidade_origem = 'gtin'` |
| C1.2 | item **sem** `gtin` → produto com `identidade_origem = 'texto'`, `emit_cnpj` o da nota |
| C1.3 | dois itens com o mesmo `gtin`, em notas de **lojas diferentes** → o **mesmo** `produto_id` |
| C1.4 | mesma descrição sem `gtin`, **CNPJs diferentes** → produtos **diferentes** |
| C1.5 | 🔴 `persistir_nota` ⛔ não commita: um `rollback()` depois dela apaga a nota, os itens e os produtos |
| C1.6 | nota **duplicada** devolve `"duplicada"` e ⛔ não cria produto nenhum |
| C1.7 | o produto criado nasce com `categoria_id` NULL e `origem` NULL — ⛔ `persistir_nota` não classifica |
| C1.8 | item sem `gtin` em nota sem `emit_cnpj` → `ValueError` **sobe** |

### C2 — a categoria sai no JSON do item — `tests/test_categoria_no_json.py`

| # | Critério |
| - | -------- |
| C2.1 | item de produto classificado → `categoria_slug` e `categoria` com o slug e o nome da categoria |
| C2.2 | item com `produto_id` NULL → as duas chaves **presentes** e `None` |
| C2.3 | produto com `categoria_id` NULL → as duas chaves `None` |
| C2.4 | as chaves do item são as dez antigas **mais** `categoria_slug` e `categoria`, nesta ordem |
| C2.5 | produto no **bucket** → `categoria == "Não Classificado"`, ⛔ não `None` |
| C2.6 | 🔴 nota com 3 itens e só 1 com produto → saem **3** itens *(o `LEFT JOIN` da D8)* |
| C2.7 | ⛔ `produto_id` e `origem` **não** aparecem no item |

### C3 — a importação não mente no diagnóstico — `tests/test_importar_diagnostico.py`

| # | Critério |
| - | -------- |
| C3.1 | XML que não abre continua virando `resultado = 'invalida'` com `detalhe` preenchido |
| C3.2 | 🔴 `ValueError` levantado por `persistir_nota` ⛔ **não** vira `'invalida'`: sobe |
| C3.3 | `importar` **commita** o lote: outra conexão ao mesmo arquivo enxerga a nota |
| C3.4 | cada arquivo é classificado **uma** vez por `classificar_xml` *(dívida d)* |
| C3.5 | as duas passadas continuam: evento que vem **antes** da nota no `.zip` ainda se aplica |
| C3.6 | os contadores de `importacoes` continuam batendo |
| C3.7 | `ValueError` levantado por `aplicar_cancelamento` ⛔ **não** vira `'invalida'`: sobe |

### C4 — a varredura resgata os pendentes — `tests/test_varredura_pendentes.py`

| # | Critério |
| - | -------- |
| C4.1 | produto `origem` NULL com item de NCM ancorado → ganha a categoria e `origem = 'ncm'` |
| C4.2 | 🔴 produto **no bucket** é varrido de novo: com a âncora nova, sai do bucket |
| C4.3 | produto `origem = 'manual'` ⛔ não é tocado |
| C4.4 | produto `origem = 'ncm'` ⛔ não é varrido |
| C4.5 | pendente sem NCM em item nenhum → vai para o bucket, `origem` continua NULL |
| C4.6 | o NCM usado é o do item de **maior `id`** *(D6)* |
| C4.7 | devolve o número de produtos que **saíram** do pendente |
| C4.8 | ⛔ não commita: um `rollback()` depois dela desfaz a varredura inteira |

---

## 5. ⚠️ O que os oráculos semeiam, e o que ⛔ não semeiam

📋 **Os quatro módulos montam o banco à mão**, com `INSERT` diretos em `categorias`, `ncm_ancora` e
`produtos`. ⛔ Nenhum deles chama `carregar_seed_padrao`: a taxonomia real muda quando alguém edita
`taxonomia_seed.json`, e um oráculo preso a ela reprovaria por motivo alheio à tarefa.

⛔ **Nenhum teste desta story afirma `origem in {conjunto fechado}`** nem compara a linha inteira de
`produtos` *(risco R1)*. Cada teste asserta **o campo que a tarefa decide**, e nada mais.

📋 **Todo teste que afirma um literal declara a premissa na docstring** — foi o que, na 011,
transformou *"como faço passar?"* em *"este teste afirmava a regra antiga?"*.

---

## 6. O que esta story ⛔ NÃO entrega

- ⛔ **Nenhum degrau novo na cascata.** O LLM é a 012.
- ⛔ **Nenhuma migração.** O esquema da 007 já tem `itens.produto_id`.
- ⛔ **Nenhuma CLI.** Quem chama `importar` e a varredura é quem consome a biblioteca.
- ⛔ **`importar` não classifica** — ver **D1**.
- ⛔ **A dívida `f`** (`criar_esquema` virar migração v0) não vence: nada aqui altera tabela da spec 01.

---

## 7. ⚠️ O que fica ANOTADO e não vira código

- 🔴 **`aplicar_cancelamento` também chama `commit()`** *(`cancelamento.py:77`)* — é a mesma dívida
  `a`, na outra ponta do fluxo, e ⛔ não estava anotada em lugar nenhum. Achada no P1 da 013. Não
  vence aqui porque `cancelamento.py` não é alvo de tarefa nenhuma: seria um quinto arquivo. ⭐ Fica
  como dívida **k**.
- ⚠️ **Itens de notas importadas ANTES da 013 ficam com `produto_id` NULL para sempre.** ⛔ Não existe
  backfill, e a varredura não o faz: ela varre `produtos`, e esses itens não têm produto nenhum.
  ⭐ É story própria.
- ⚠️ **A varredura é O(produtos pendentes) consultas ao banco**, uma por produto para achar o NCM.
  Em banco de nota fiscal pessoal isso é irrelevante; ⛔ não se otimize sem medir.
- ⚠️ **`resolver_produto_do_item` não sabe desempatar** GTIN que muda de dono: se um item traz GTIN
  hoje e não traz amanhã, saem dois produtos. É a assimetria que a 008 declarou como requisito.

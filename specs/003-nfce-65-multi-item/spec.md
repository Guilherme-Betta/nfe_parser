# Spec — 003 · NFC-e 65 e multi-item

> **Passo 1 do loop. Escrito pelo Claude, dentro da janela da medicao 4.**
>
> ⚠️ **A invariante que governa este arquivo:** *criterio que nao vira assercao nao terminou
> de ser especificado.* Se voce nao consegue imaginar o teste que prova um criterio, o criterio
> ainda e prosa — reescreva ate conseguir.
>
> 🔒 **Os 4 criterios abaixo foram pre-registrados** em `plan/protocolo-medicao-4.md` §2 do
> `AI_Scrum_Workflow`, **fora** da janela medida. Esta spec pode **detalhar** cada um ate virar
> assercao. Nao pode **trocar** nenhum, nao pode **somar um quinto**, nao pode **soltar** nenhum.
> Escopo que se move durante a medicao contamina a medicao.

**Deriva de** [`specs/01_spec_parser_modelo.md`](../01_spec_parser_modelo.md) §2 (o DDL) e §3
(comportamento). Terceira das 6 stories do nucleo `parser`.

**Continua a story 002**, que entregou `src/nfe_parser/extrator.py` com `para_centavos` e
`extrair_nota` fechados sobre **uma** NF-e modelo **55** de **um** item. Esta story abre exatamente
os dois eixos que ficaram travados la — o **modelo** e a **contagem de itens** — e mais nada.

⛔ **Nenhum modulo novo.** Todo o codigo desta story e em `src/nfe_parser/extrator.py`.
Esta story **nao escreve no banco**.

---

## 1. User story

Como dono do app, quero **ler tambem a NFC-e (modelo 65) do supermercado, com todos os seus
itens**, para que uma compra de 30 produtos vire **30 linhas de gasto** e nao uma linha so.

---

## 2. Escopo — o que muda no contrato

As duas funcoes publicas continuam sendo as mesmas, com a mesma assinatura de entrada. O que muda:

| Funcao | Antes (story 002) | Depois (story 003) |
| ------ | ----------------- | ------------------ |
| `para_centavos(texto: str) -> int` | sem anotacao de tipo | **anotada** |
| `extrair_nota(xml_texto: str) -> dict` | so modelo 55, 1 item, sem anotacao | **modelo 55 e 65**, **N itens**, **anotada** |

O **formato de saida nao muda**. Continua `{"nota": {...}, "itens": [...]}`, com as chaves ja
fixadas pela story 002 e batendo com as colunas do DDL:

```
nota  = chave, modelo, serie, numero, dh_emi, emit_nome, emit_cnpj,
        emit_municipio, emit_uf, valor_total, forma_pagamento, xml_raw
item  = n_item, descricao, cprod, ncm, gtin, quantidade, valor_unitario,
        valor_linha, unidade
```

> ⚠️ **"Mesmos campos" e uma assercao de conjunto, nao de vibe.** O criterio 1 se prova comparando
> `set(...keys())` com esses dois conjuntos literais: **nenhuma chave a mais, nenhuma a menos**.
> Um dicionario que ganha uma chave so na 65 quebra o `INSERT` do banco la na frente.

As regras de conversao herdadas da story 002 **continuam valendo e nao se renegociam aqui**:
dinheiro (`vNF`, `vProd`) passa por `para_centavos` e vira `int`; `qCom`, `vUnCom` e `dhEmi`
saem como a **string exata do XML**, sem passar por `float` nem `Decimal`; `mod` e `UF` sao
**enums** e usam `.value`; a chave sao os 44 digitos **depois** do prefixo `NFe`.

---

## 3. Criterios de aceitacao — os 4, virados em assercao

### C1 · NFC-e 65 e extraida com os mesmos campos da 55

Com a fixture nova `tests/fixtures/nfe_65_1item.xml`:

| # | Assercao |
| - | -------- |
| 1.1 | `extrair_nota(xml_65)` devolve um dicionario com exatamente as chaves `{"nota", "itens"}` |
| 1.2 | `set(r["nota"].keys())` e **igual** ao conjunto `nota` da §2 — nem a mais, nem a menos |
| 1.3 | `set(r["itens"][0].keys())` e **igual** ao conjunto `item` da §2 |
| 1.4 | `r["nota"]["modelo"] == 65` — `int`, nao `"65"`, nao `Tmod.VALUE_65` |
| 1.5 | `r["nota"]["chave"]` tem **44 caracteres**, todos digitos, e **nao** comeca com `NFe` |
| 1.6 | `r["nota"]["chave"][20:22] == "65"` — a chave carrega o modelo; se ela disser 55 e o campo disser 65, a fixture esta incoerente e o teste tem que reprovar |
| 1.7 | `r["nota"]["valor_total"]` e `int` (centavos) e `r["nota"]["dh_emi"]` e a **string exata** do XML |
| 1.8 | `r["nota"]["emit_uf"] == "SP"` — `str`, nao enum |
| 1.9 | A 55 **continua passando**: o oraculo da story 002 sobre `nfe_55_1item.xml` roda sem nenhuma alteracao. Suportar a 65 **nao pode** custar a 55 |

> **O que a 65 tem de diferente e que pode quebrar:** ela carrega um bloco `<infNFeSupl>`
> (QR code e `urlChave`) que a 55 nao tem, e e **obrigatorio** no modelo 65. A fixture **tem
> que incluir** esse bloco. Se a extracao quebrar diante de um elemento que ela nem le, o codigo
> esta acoplado ao formato exato da 55 — e esse e justamente o defeito que a C1 caca.

### C2 · Uma nota com N itens `det` produz N linhas — nao 1, nao N+1

Com a fixture nova `tests/fixtures/nfe_55_3itens.xml`:

| # | Assercao |
| - | -------- |
| 2.1 | `len(r["itens"]) == 3` |
| 2.2 | `[i["n_item"] for i in r["itens"]] == [1, 2, 3]` — nessa ordem, e `int` |
| 2.3 | As 3 `descricao` sao **distintas entre si** e batem uma a uma com o XML. E isto que pega o modo de falha "extraiu o item 1 tres vezes", que passaria em 2.1 e em 2.2 |
| 2.4 | `sum(i["valor_linha"] for i in r["itens"]) == r["nota"]["valor_total"]` — ver a ressalva abaixo |
| 2.5 | **Regressao de 1 item:** `nfe_55_1item.xml` continua devolvendo `len(r["itens"]) == 1`. Multi-item nao pode virar "sempre >= 2" |

> ⚠️ **A 2.4 so vale porque a fixture foi construida para ela valer.** Numa NF-e real o `vNF`
> inclui frete, seguro e desconto, e a soma dos `vProd` **nao** fecha com ele. Na fixture
> `nfe_55_3itens` esses campos sao zero **de proposito**, o que torna a igualdade uma invariante
> legitima ali. **Isto e propriedade da fixture, nao regra do dominio** — nao propague para o
> codigo, e nao escreva validacao de soma no `extrator.py`.

### C3 · A fixture de GTIN ausente ja existe — reusar, nao reescrever

| # | Assercao |
| - | -------- |
| 3.1 | ⛔ `tests/fixtures/nfe_55_1item.xml` **nao e tocada**. Ela ja traz `cEAN = "SEM GTIN"`; e ela a fixture de GTIN ausente que a story 002 fechou. Criar uma segunda fixture so de GTIN e violacao direta deste criterio |
| 3.2 | Sobre ela, `r["itens"][0]["gtin"] is None` — a invariante da 002 segue verde |
| 3.3 | Na `nfe_55_3itens.xml`, o item **2** tem `cEAN = "SEM GTIN"` e os itens **1** e **3** tem GTIN de verdade. Assercao: `[i["gtin"] for i in r["itens"]] == ["7891000100103", None, "7891910000197"]` |

> **Por que a 3.3 nao e escopo novo:** ela e o criterio 3 aplicado ao eixo que esta story abre.
> A story 002 provou `"SEM GTIN" -> None` com **um** item, caso em que "por item" e "global" sao
> indistinguiveis. Com 3 itens eles se separam, e isso custa **zero**: e a mesma fixture que a C2
> ja exige. Nenhum arquivo novo, nenhuma funcao nova, nenhuma linha de codigo a mais.

### C4 · Anotacao de tipo no retorno de toda funcao publica

Criterio novo, derivado do item 5 da rubrica. A hipotese que ele testa: *o tipo de retorno de
`para_centavos` foi errado duas vezes seguidas porque o codigo nao declara o que devolve.*

"Funcao publica" = funcao **definida em** `src/nfe_parser/extrator.py` cujo nome **nao** comeca
com `_`. Hoje sao duas: `para_centavos` e `extrair_nota`.

| # | Assercao |
| - | -------- |
| 4.1 | Para **toda** funcao publica do modulo, `inspect.signature(f).return_annotation` **nao** e `inspect.Signature.empty`. O teste **descobre** as funcoes por introspecao — assim funcao publica nova ja nasce coberta, sem ninguem precisar editar o teste |
| 4.2 | `para_centavos` declara `-> int` e `extrair_nota` declara `-> dict` |
| 4.3 | **A anotacao bate com a realidade:** chamando cada funcao publica com a entrada valida da fixture, `isinstance(retorno, tipo_anotado)` e verdadeiro. Sozinha, a 4.1 passaria com uma anotacao **errada** — que e pior que anotacao nenhuma, porque mente com autoridade |
| 4.4 | Os **parametros** tambem sao anotados (`texto: str`, `xml_texto: str`). Nao e o criterio pre-registrado, que fala do **retorno** — entra porque assinatura meio anotada confunde mais que assinatura crua, e custa os mesmos caracteres |

> **Como este criterio se falsifica:** se a rubrica da story 003 mostrar que o Gui **nao** errou
> mais o tipo de retorno, a hipotese ganha um ponto. Se ele errar de novo mesmo com a anotacao
> no codigo, a culpa **nao** era do codigo. Os dois desfechos sao resultado; nenhum e fracasso.

---

## 4. Fora de escopo — e nao se negocia durante a medicao

⛔ Banco de dados · web/UI · performance · **qualquer refactor do que a story 002 entregou**.

E mais, derivado dos criterios acima:

- ⛔ **Validar o digito verificador** da chave. Nada no codigo valida DV hoje; introduzir isso e
  story nova.
- ⛔ **Rejeitar modelos diferentes de 55 e 65.** Nenhum dos 4 criterios pede. Se a vontade
  aparecer, anote — nao implemente.
- ⛔ **Trocar o dicionario por `dataclass` ou `TypedDict`.** Provavelmente e melhor, e e refactor
  da entrega da 002. Candidata a story futura.
- ⛔ **Anotar o `banco.py`.** O C4 fala das funcoes publicas **deste** modulo. O `banco.py` e
  entrega da story 001 e esta fora.

---

## 5. Fixtures

| Arquivo | Estado | Serve a | Propriedades exigidas |
| ------- | ------ | ------- | --------------------- |
| `nfe_55_1item.xml` | **existe — nao tocar** | C1.9, C2.5, C3.1, C3.2 | como esta |
| `nfe_65_1item.xml` | **criar** | C1 | `mod=65`; chave de 44 digitos com `65` nas posicoes 21-22; bloco `<infNFeSupl>` com `qrCode` e `urlChave`; `UF=SP`; 1 item |
| `nfe_55_3itens.xml` | **criar** | C2, C3.3 | `mod=55`; **tres** blocos `<det>` com `nItem` 1, 2 e 3 e descricoes distintas; `cEAN` do item 2 = `SEM GTIN`; frete, seguro e desconto **zero**; `vNF` = soma exata dos tres `vProd` |

🔴 **O `nfe_parser` e repositorio publico.** CNPJ, CPF, razao social e endereco das fixturas novas
sao **ficticios**, no mesmo padrao da fixture que ja existe (`99999999000199`). Nenhum XML de nota
real entra no repo.

---

## 6. Mapa criterio → oraculo

Um modulo de teste por sub-tarefa — e essa fatia que o modelo local recebe no passo 3.

| Criterio | Modulo de teste | Sub-tarefa |
| -------- | --------------- | ---------- |
| C1 | `tests/test_extrator_nfce65.py` | 1 |
| C2 + C3.3 | `tests/test_extrator_multi_item.py` | 2 |
| C4 | `tests/test_anotacoes.py` | 3 |
| C3.1, C3.2, C1.9, C2.5 | os modulos da story 002, **sem alteracao** | regressao |

---

## 7. Definicao de pronto

1. `python scripts/verify.py` verde — os testes das stories 001 e 002 **junto** com os novos.
2. Cada assercao das tabelas da §3 existe como assercao de verdade, nao como comentario.
3. O diff lido **linha a linha** por um humano. O Achado H mostrou por que: `ruff` verde nao
   detecta corpo de funcao duplicado depois do `return`, nenhuma regra dele pega isso, e nenhuma
   assercao alcanca codigo morto.
4. Nenhuma fixture com dado real.

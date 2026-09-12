# Spec — 002 · Extrair uma NF-e 55 de 1 item

> **Passo 1 do loop. Escrito pelo Claude.**
>
> ⚠️ **A invariante que governa este arquivo:** *criterio que nao vira assercao
> nao terminou de ser especificado.* Se voce nao consegue imaginar o teste que
> prova um criterio, o criterio ainda e prosa — reescreva ate conseguir.
>
> Isso foi medido, nao inventado: na Fase 0 a spec dizia "nao use float; 1.005
> teria que virar 101". Nenhum teste cobriu. O modelo usou `int(Decimal(x)*100)`,
> que TRUNCA (1.005 -> 100), e passou. A spec estava certa e inutil.
>
> **Esta story leva essa licao a serio**: o criterio 12 abaixo existe para que
> aquele mesmo bug nao passe de novo.

**Deriva de** [`specs/01_spec_parser_modelo.md`](../01_spec_parser_modelo.md) §2 (o DDL) e §3
(comportamento). Segunda das 6 stories do nucleo `parser`. Backlog no `offload-log.md` do
`AI_Scrum_Workflow`.

**Depende da story 001** (`banco.py`) so no sentido de que as chaves do dicionario de saida batem
com as colunas do DDL. Esta story **nao escreve no banco**.

## 1. User story

Como dono do app, quero **ler uma NF-e modelo 55 de um item e obter os campos ja no formato do
banco**, para que o gasto apareca exato ao centavo e a quantidade em quilos nao perca casa decimal
no caminho.

## 2. Escopo — o que esta feature faz

Modulo novo `src/nfe_parser/extrator.py`, com **duas funcoes publicas**:

### `para_centavos(texto) -> int`

Converte um valor monetario do XML (`"8.04"`) no inteiro de centavos (`804`).

### `extrair_nota(xml_texto) -> dict`

Recebe o **texto** de um XML `nfeProc` e devolve um dicionario com duas chaves,
`"nota"` e `"itens"`, cujos nomes de campo sao **exatamente as colunas do DDL**:

```python
{
  "nota": {
    "chave": "35260499999999000199550010000000011000000017",  # 44 digitos, sem o prefixo "NFe"
    "modelo": 55,                    # int
    "serie": 1,                      # int
    "numero": 1,                     # int  (nNF)
    "dh_emi": "2026-04-15T10:30:00-03:00",
    "emit_nome": "MERCEARIA EXEMPLO LTDA",
    "emit_cnpj": "99999999000199",   # TEXT: pode ter zero a esquerda
    "emit_municipio": "SAO PAULO",
    "emit_uf": "SP",
    "valor_total": 804,              # centavos, de vNF
    "forma_pagamento": "01",         # tPag do primeiro detPag
    "xml_raw": "<?xml ...",          # o texto recebido, sem alteracao
  },
  "itens": [
    {
      "n_item": 1,                   # int
      "descricao": "TOMATE ITALIANO KG",   # xProd cru
      "cprod": "SKU-0001",
      "ncm": "07020000",             # TEXT
      "gtin": None,                  # "SEM GTIN" vira None
      "quantidade": "1.5000",        # STRING, exata como no XML
      "unidade": "KG",
      "valor_unitario": "5.3600000000",    # STRING, exata como no XML
      "valor_linha": 804,            # centavos, de vProd
    }
  ],
}
```

## 3. Fronteiras — o que ela NAO faz

- **Nao escreve no banco.** Nada de `sqlite3`, nada de import de `banco.py`. Persistir e da
  story 004.
- **Nao roteia por raiz.** Esta story so trata `nfeProc`. Decidir entre NF-e / evento de
  cancelamento / CF-e e da story 004.
- **Nao trata modelo 65 nem multi-item.** E a story 003. O codigo **nao precisa** proibir 65 —
  so nao precisa ter teste para ele aqui.
- **Nao le arquivo do disco.** A funcao recebe **texto**; quem abre arquivo e a borda.
- **Nao normaliza `xProd`.** Guardar cru; normalizar e da classificacao (spec 01 §4).
- **Nao valida o digito verificador da chave** nem faz qualquer conferencia fiscal.
- **Nao cria classe nem dataclass.** Dicionarios, pelas razoes do §6.

## 4. O que o `nfelib` realmente devolve — medido, nao suposto

⚠️ **Leia esta secao antes de implementar.** Ela existe porque a API nao e adivinhavel, e o
orcamento de contexto nao permite explorar a lib durante a tarefa. Tudo abaixo foi medido em
2026-09-12 contra `nfelib 2.5.2` e a fixture desta story.

```python
from nfelib.nfe.bindings.v4_0.proc_nfe_v4_00 import NfeProc
proc = NfeProc.from_xml(xml_texto)      # texto -> objeto
inf = proc.NFe.infNFe                   # os nomes preservam a caixa do XML
```

| Caminho | Devolve | Tipo | ⚠️ Atencao |
| ------- | ------- | ---- | --------- |
| `inf.Id` | `"NFe3526...0017"` | `str` | **tem o prefixo `NFe`** — a chave sao os 44 digitos depois dele |
| `inf.ide.mod` | `Tmod.VALUE_55` | **enum** | precisa de `.value` -> `"55"`, e a coluna e INTEGER |
| `inf.ide.serie` | `"1"` | `str` | coluna INTEGER |
| `inf.ide.nNF` | `"1"` | `str` | coluna INTEGER |
| `inf.ide.dhEmi` | `"2026-04-15T10:30:00-03:00"` | `str` | ja e ISO-8601 com offset; **nao converter** |
| `inf.emit.CNPJ` | `"99999999000199"` | `str` | manter string |
| `inf.emit.enderEmit.xMun` | `"SAO PAULO"` | `str` | |
| `inf.emit.enderEmit.UF` | `TufEmi.SP` | **enum** | precisa de `.value` |
| `inf.det` | lista de `Det` | `list` | 1 elemento nesta story |
| `det.nItem` | `"1"` | `str` | coluna INTEGER |
| `det.prod.qCom` | `"1.5000"` | `str` | **guardar a string como veio** |
| `det.prod.vUnCom` | `"5.3600000000"` | `str` | **guardar a string como veio** |
| `det.prod.vProd` | `"8.04"` | `str` | passa por `para_centavos` |
| `det.prod.cEAN` | `"SEM GTIN"` | `str` | vira `None` |
| `inf.total.ICMSTot.vNF` | `"8.04"` | `str` | passa por `para_centavos` |
| `inf.pag.detPag[0].tPag` | `"01"` | `str` | `inf.pag` e **objeto**, nao lista |

> ⭐ **A boa noticia: os numeros ja chegam como `str`, com o texto exato do XML.** Entao
> "quantidade como string decimal exata" se cumpre **nao convertendo**. Qualquer passagem por
> `float` ou `Decimal` e volta para string quebra: `"1.5000"` vira `"1.5"`.

> ⛔ **Os dois enums sao a pegadinha.** `inf.ide.mod` e `UF` **nao** sao strings. `str(inf.ide.mod)`
> devolve `"Tmod.VALUE_55"`, nao `"55"`. Use `.value`.

**Erro:** qualquer XML que o `nfelib` nao consiga ler levanta `xsdata.exceptions.ParserError` —
tanto XML corrompido quanto XML valido que nao e NF-e quanto string vazia.

## 5. Criterios de aceitacao (TESTAVEIS)

Cada linha vira pelo menos uma assercao no passo 2. A fixture e
[`tests/fixtures/nfe_55_1item.xml`](../../tests/fixtures/nfe_55_1item.xml).

### `extrair_nota`

| # | Criterio | Vira que assercao |
| - | -------- | ----------------- |
| 1 | A chave sai **sem o prefixo `NFe`** e com 44 digitos | `nota["chave"] == "3526...0017"` e `len(...) == 44` |
| 2 | `modelo` e o **inteiro** 55 | `nota["modelo"] == 55` (e `is` int, nao enum nem str) |
| 3 | `serie` e `numero` sao inteiros | `nota["serie"] == 1`, `nota["numero"] == 1` |
| 4 | `dh_emi` sai **igual ao XML**, com offset | `nota["dh_emi"] == "2026-04-15T10:30:00-03:00"` |
| 5 | Emitente completo | `emit_nome`, `emit_cnpj`, `emit_municipio`, `emit_uf` == valores da fixture |
| 6 | `emit_uf` e **string**, nao enum | `nota["emit_uf"] == "SP"` |
| 7 | ⭐ `valor_total` e **804**, nao 803 | `nota["valor_total"] == 804` |
| 8 | `forma_pagamento` vem do `tPag` | `nota["forma_pagamento"] == "01"` |
| 9 | `xml_raw` e o texto **recebido, intacto** | `nota["xml_raw"] == xml_texto` |
| 10 | **Um** item | `len(resultado["itens"]) == 1` |
| 11 | ⭐ `quantidade` e `valor_unitario` sao as **strings exatas** | `== "1.5000"` e `== "5.3600000000"` |
| 12 | ⭐ `valor_linha` e **804**, nao 803 | `itens[0]["valor_linha"] == 804` |
| 13 | `descricao` e o `xProd` **cru** | `== "TOMATE ITALIANO KG"` |
| 14 | `ncm` e `cprod` como strings | `== "07020000"`, `== "SKU-0001"` |
| 15 | `gtin` de `"SEM GTIN"` vira **`None`** | `itens[0]["gtin"] is None` |
| 16 | `n_item` e inteiro | `itens[0]["n_item"] == 1` |

### `para_centavos`

| # | Criterio | Vira que assercao |
| - | -------- | ----------------- |
| 17 | Converte exato | `para_centavos("8.04") == 804` |
| 18 | ⭐ **Nao usa float** | `para_centavos("0.29") == 29` (o float daria 28) |
| 19 | Inteiro sem casas decimais | `para_centavos("10") == 1000` |
| 20 | Zero | `para_centavos("0.00") == 0` |
| 21 | ⭐ **Mais de 2 casas REJEITA, nao trunca** | `para_centavos("1.005")` levanta `ValueError` |
| 22 | Texto nao numerico rejeita | `para_centavos("abc")` levanta `ValueError` |
| 23 | String vazia rejeita | `para_centavos("")` levanta `ValueError` |

> ⭐ **Os criterios 7, 12, 18 e 21 sao o coracao desta story.** Os tres primeiros matam o
> `float`; o 21 mata o `Decimal` truncado — que foi **exatamente** o bug que passou na Fase 0.
> `int(Decimal("1.005") * 100)` devolve `100` sem reclamar. Aqui tem que estourar.

## 6. Casos de borda e caminho de erro

⚠️ **Item 1 da rubrica de qualidade:** o `verify` precisa cobrir o caminho de erro, nao so o feliz.

| # | Entrada | Comportamento esperado |
| - | ------- | ---------------------- |
| 24 | XML corrompido (`"<nfeProc><naofecha>"`) | `ValueError` |
| 25 | XML valido que nao e NF-e (`"<pedido/>"`) | `ValueError` |
| 26 | String vazia | `ValueError` |

> ⛔ **`ValueError`, nao `ParserError`.** O `nfelib` levanta `xsdata.exceptions.ParserError`. O
> nucleo **traduz** para `ValueError` para que o `xsdata` nao vaze para quem chama — a borda e a
> story 004 nao deveriam ter que importar `xsdata` para tratar erro. Capture e re-levante.

## 7. Por que dicionario, e nao dataclass

As chaves foram escolhidas para bater **nome por nome** com as colunas do DDL. Isso faz o INSERT
da story 004 ser direto (`INSERT INTO notas (...) VALUES (:chave, :modelo, ...)`) sem camada de
traducao no meio. Uma dataclass aqui sao ~40 linhas a mais para o mesmo efeito, e a rubrica do kit
penaliza abstracao que nao paga.

## 8. Tamanho — cabe no orcamento?

- [x] O codigo relevante para esta feature cabe em **~300 linhas**?

Estimativa: `para_centavos` ~15 linhas, `extrair_nota` ~45 linhas, imports e docstrings ~20.
**~80 linhas**, em um arquivo novo. Folgado dentro dos 300.

⚠️ **Mas o orcamento apertado nao e o do arquivo, e o dos 8k de contexto.** A story 001 mandou
7,0k no turno 1 — e ">6k no turno 1 condena o laco de reflexao". Por isso o `plan.md` fatia esta
story em **duas invocacoes**, e por isso o §4 acima existe: ele substitui a exploracao da `nfelib`,
que o modelo nao teria orcamento para fazer.

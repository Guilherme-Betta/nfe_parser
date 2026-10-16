# O que o `nfelib` devolve — medido

> Referencia curta, de proposito. Ela existe para caber no `--read` de uma tarefa do modelo
> local sem estourar os 8192 tokens. Medido em 2026-09-12 contra **`nfelib 2.5.2`** e a fixture
> `tests/fixtures/nfe_55_1item.xml`. Nao e suposicao: cada linha foi impressa.

```python
from nfelib.nfe.bindings.v4_0.proc_nfe_v4_00 import NfeProc

proc = NfeProc.from_xml(xml_texto)  # texto -> objeto
inf = proc.NFe.infNFe  # os nomes preservam a caixa do XML
```

| Caminho | Valor na fixture | Tipo |
| ------- | ---------------- | ---- |
| `inf.Id` | `"NFe35260499999999000199550010000000011000000017"` | `str` |
| `inf.ide.mod` | `Tmod.VALUE_55` | **enum** |
| `inf.ide.serie` | `"1"` | `str` |
| `inf.ide.nNF` | `"1"` | `str` |
| `inf.ide.dhEmi` | `"2026-04-15T10:30:00-03:00"` | `str` |
| `inf.emit.CNPJ` | `"99999999000199"` | `str` |
| `inf.emit.xNome` | `"MERCEARIA EXEMPLO LTDA"` | `str` |
| `inf.emit.enderEmit.xMun` | `"SAO PAULO"` | `str` |
| `inf.emit.enderEmit.UF` | `TufEmi.SP` | **enum** |
| `inf.pag.detPag[0].tPag` | `"01"` | `str` |
| `inf.total.ICMSTot.vNF` | `"8.04"` | `str` |
| `inf.det` | lista de `Det` | `list` |
| `det.nItem` | `"1"` | `str` |
| `det.prod.cProd` | `"SKU-0001"` | `str` |
| `det.prod.xProd` | `"TOMATE ITALIANO KG"` | `str` |
| `det.prod.NCM` | `"07020000"` | `str` |
| `det.prod.cEAN` | `"SEM GTIN"` | `str` |
| `det.prod.uCom` | `"KG"` | `str` |
| `det.prod.qCom` | `"1.5000"` | `str` |
| `det.prod.vUnCom` | `"5.3600000000"` | `str` |
| `det.prod.vProd` | `"8.04"` | `str` |

## As tres coisas que enganam

**1. `inf.Id` tem o prefixo `NFe`.** A chave sao os 44 digitos DEPOIS dele.

**2. `inf.ide.mod` e `enderEmit.UF` sao ENUMS, nao strings.** `str(inf.ide.mod)` devolve
`"Tmod.VALUE_55"`, nao `"55"`. Use `.value`.

**3. Os numeros ja chegam como `str`, com o texto exato do XML.** Entao "quantidade como string
decimal exata" se cumpre **nao convertendo**. Passar por `float` ou `Decimal` e voltar para string
transforma `"1.5000"` em `"1.5"` e quebra o teste. Vale para `qCom`, `vUnCom` e `dhEmi`.

Dinheiro (`vNF`, `vProd`) e a excecao: esses passam por `para_centavos`, que ja esta no arquivo.

## Erro

Qualquer XML que o `nfelib` nao consiga ler levanta **`xsdata.exceptions.ParserError`** — XML
corrompido, XML valido que nao e NF-e, e string vazia, os tres. Capture e levante `ValueError`
no lugar, para o `xsdata` nao vazar para quem chama.

```python
from xsdata.exceptions import ParserError
```

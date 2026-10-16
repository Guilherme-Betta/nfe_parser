# Spec — 005 · Cancelamento em duas passadas

Fecha a invariante do §5 da `specs/01_spec_parser_modelo.md`:
*"cancelamento aplicado inclusive com evento antes da nota; orfao e invalido nao quebram o lote"*.

E a ultima invariante do §5 que nenhuma story anterior fechou.

---

## 1. O que existe hoje, e por que nao basta

A story 004 registra **todo** evento como `cancelamento_orfao` e grava
`cancelamentos_aplicados = 0` fixo (`importador.py`, linhas 29-30 e 88).

**Era o certo la, e nao e bug da 004.** O `importar` faz **uma** varredura do `.zip`. Numa varredura
so, um evento que aparece antes da sua nota nao tem como ser aplicado — a nota ainda nao esta no
banco. Sem segunda passada, nenhum evento **podia** ser aplicado, e `cancelamento_orfao` e o unico
dos seis valores do `CHECK` que descreve honestamente "um evento que nao alterou nota nenhuma".

A 005 e quem torna aquela escolha correta.

---

## 2. DDL: nada muda

✅ **Verificado em 14/09 contra `src/nfe_parser/banco.py`.** O esquema da story 001 ja tem tudo:

| Ja existe | Onde |
| --------- | ---- |
| `notas.status TEXT NOT NULL DEFAULT 'ok' CHECK (status IN ('ok','cancelada'))` | `banco.py:27` |
| `notas.cancelado_em TEXT` | `banco.py:28` |
| `importacoes.cancelamentos_aplicados INTEGER DEFAULT 0` | `banco.py:17` |
| `CHECK` de `importacao_arquivos.resultado` aceitando `'cancelamento_aplicado'` e `'cancelamento_orfao'` | `banco.py:52-54` |

⛔ **Nenhuma tarefa desta story pode tocar em `banco.py`.** Se alguma precisar, a spec esta errada.

---

## 3. Criterios de aceite

Os seis criterios abaixo sao os que o Gui aprovou na abertura da sessao, refinados em blocos
testaveis. Os titulos C1–C4 sao a numeracao dos blocos; os numeros 1–6 entre parenteses apontam
para o criterio aprovado que cada bloco serve.

### C1 — Ler o evento (criterios 1, 6)

O modulo novo `src/nfe_parser/cancelamento.py` expoe:

```python
def extrair_evento(xml_texto: str) -> dict:
    """{'ch_nfe': str|None, 'tp_evento': str|None, 'dh_evento': str|None}"""
```

| # | Criterio |
| - | -------- |
| C1.1 | Evento completo devolve `ch_nfe` com os 44 digitos, `tp_evento='110111'` e o `dh_evento` do XML |
| C1.2 | Evento **sem `chNFe`** devolve `ch_nfe=None` — **nao levanta** |
| C1.3 | Evento **sem `tpEvento`** devolve `tp_evento=None` — **nao levanta** |
| C1.4 | `tp_evento` sai sempre **`str` ou `None`**, nunca um objeto de enum |
| C1.5 | `<procEventoNFe>` vazio ou sem `<infEvento>` devolve os tres campos `None` — **nao levanta** |
| C1.6 | XML que o parser nao consegue abrir levanta **`ValueError`** |

> 🔴 **C1.4 nao e preciosismo — e um `AttributeError` esperando acontecer.** Medido em 14/09:
> o `xsdata` devolve `tpEvento` como **enum** quando o valor e `'110111'` (`.value == '110111'`),
> mas como **`str` crua** para qualquer outro valor (`'110110'` da carta de correcao, `'ABC'`),
> emitindo apenas um `ConverterWarning`. Um `inf.tpEvento.value` ingenuo funciona no caminho feliz
> e estoura no primeiro evento que nao seja cancelamento.

### C2 — Aplicar o evento (criterios 3, 4, 5, 6)

```python
def aplicar_cancelamento(conexao, evento: dict) -> str:
    """'cancelamento_aplicado' | 'cancelamento_orfao'"""
```

| # | Criterio |
| - | -------- |
| C2.1 | `ch_nfe` bate com nota do banco e `tp_evento == '110111'` → a nota vira `status='cancelada'` com `cancelado_em` preenchido, e devolve `'cancelamento_aplicado'` |
| C2.2 | `ch_nfe` nao bate com nota nenhuma → devolve `'cancelamento_orfao'` e ⛔ **nao cria linha em `notas`** |
| C2.3 | `ch_nfe=None` → `'cancelamento_orfao'`, sem tocar em nota nenhuma |
| C2.4 | `tp_evento` diferente de `'110111'` (carta de correcao, `None`, lixo) → `'cancelamento_orfao'`, e **nenhuma nota muda de status** |
| C2.5 | Aplicar duas vezes o mesmo evento deixa `cancelado_em` **inalterado** (o primeiro carimbo vence) e devolve `'cancelamento_aplicado'` nas duas |
| C2.6 | Uma nota cancelada nao afeta as outras: so a linha da `ch_nfe` muda |

> **C2.5 e o que "nao re-cancela" significa.** O estado final depois de duas aplicacoes e
> identico ao de uma — que e a definicao de idempotencia. O valor devolvido continua sendo
> `'cancelamento_aplicado'` porque a pergunta que ele responde e *"este evento corresponde a uma
> nota que esta cancelada?"*, e a resposta e sim nas duas vezes. A regra e uma so: **existe nota
> para a chave? entao aplicado; nao existe? entao orfao.** Implementa-se com
> `UPDATE ... WHERE chave = ? AND status = 'ok'`, que protege o carimbo sem precisar de um segundo
> ramo de decisao.

### C3 — As duas passadas (criterios 1, 2, 6)

`importar` passa a processar o lote em **duas varreduras**: a primeira persiste as notas, a segunda
aplica os eventos.

| # | Criterio |
| - | -------- |
| C3.1 | Um `.zip` com o **evento antes** da nota produz o mesmo estado final que o `.zip` com a ordem inversa — ⭐ **a invariante-titulo** |
| C3.2 | Evento cujo `chNFe` bate com nota do **mesmo lote** registra `resultado='cancelamento_aplicado'` na linha do log |
| C3.3 | Evento cujo `chNFe` bate com nota de uma importacao **anterior** tambem aplica |
| C3.4 | Evento orfao registra `resultado='cancelamento_orfao'` e ⛔ **nao cria linha em `notas`** |
| C3.5 | Evento cujo XML nao abre registra `resultado='invalida'` com `detalhe` nao vazio, e **o lote segue** |
| C3.6 | A coluna `chave` da linha do log recebe o `chNFe` do evento quando ele existe |
| C3.7 | Reimportar o mesmo `.zip` nao duplica notas nem move `cancelado_em` |

> **C3.5 e a fronteira entre "invalida" e "orfao", e ela tem lastro.** Um evento que **parseia** mas
> nao casa com nota nenhuma e `cancelamento_orfao`. Um evento que **nao abre** e `invalida` — o
> mesmo tratamento que o `importador` ja da a uma nota que nao abre. Medido em 14/09: um
> `<procEventoNFe>` **sem namespace** e classificado como `"evento"` por `classificar_xml`
> (`classificador.py:20` aceita a tag sem namespace) mas faz o parser levantar `ParserError`. Sem o
> C3.5, esse arquivo derruba o lote inteiro.

> 🔴 **Compatibilidade com a 004, e ela restringe o desenho.** Os testes
> `test_o_mapa_de_classificacao_para_resultado` e `test_cada_desfecho_cai_no_seu_contador` da story
> 004 usam um evento **sem `chNFe`** e exigem `resultado='cancelamento_orfao'` e
> `invalidas == 1`. Portanto **evento sem chave continua orfao, nunca invalida** — classificar o
> evento malformado como `invalida` quebraria dois testes verdes. O criterio 6 diz "registrado",
> nao diz "como invalida".

### C4 — O contador (criterio 5)

| # | Criterio |
| - | -------- |
| C4.1 | `importacoes.cancelamentos_aplicados` conta as linhas do log com `resultado='cancelamento_aplicado'` |
| C4.2 | Orfaos **nao** entram nesse contador |
| C4.3 | `total_arquivos` continua contando todos os arquivos, evento incluso |
| C4.4 | Os contadores sao por importacao e nao acumulam entre lotes |

---

## 4. Fora de escopo

- ⛔ Qualquer alteracao de DDL (§2).
- ⛔ Eventos que nao sejam cancelamento (carta de correcao, manifestacao). Eles sao **reconhecidos**
  e descartados como orfaos (C2.4), nao implementados.
- ⛔ Descancelamento. Nao existe no §5 e nao ha valor no `CHECK` para ele.
- ⛔ As tres ressalvas abertas no passo 4 da story 004 (o `commit()` dentro de `persistir_nota`, o
  `mod` em pre-ordem, o `except ValueError` largo). Continuam anotadas, continuam sem teste que as
  defina. Candidatas a story 006.

---

## 5. O vermelho certo esperado no passo 2

```
ERROR tests/test_extrair_evento.py        ModuleNotFoundError: nfe_parser.cancelamento
ERROR tests/test_aplicar_cancelamento.py  ModuleNotFoundError: nfe_parser.cancelamento
```

Os modulos C3 e C4 testam `importador.py`, que **ja existe** — entao eles falham por **assercao**,
nao por coleta. Isso e esperado e e a diferenca desta story para a 004: metade do alvo ja esta
escrito.

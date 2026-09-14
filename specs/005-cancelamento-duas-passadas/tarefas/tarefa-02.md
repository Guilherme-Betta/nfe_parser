Acrescente a funcao `aplicar_cancelamento` ao arquivo `src/nfe_parser/cancelamento.py`.

NAO altere a funcao `extrair_evento` que ja esta nesse arquivo. Ela esta pronta e testada.

```python
def aplicar_cancelamento(conexao, evento: dict) -> str: ...
```

`evento` e exatamente o dicionario que `extrair_evento` devolve: `{"ch_nfe": ..., "tp_evento": ...,
"dh_evento": ...}`.

A funcao devolve uma de duas strings: `"cancelamento_aplicado"` ou `"cancelamento_orfao"`.

A REGRA, EM UMA FRASE: existe nota no banco para esta chave, e este evento e de cancelamento?
Entao cancela a nota e devolve `"cancelamento_aplicado"`. Caso contrario devolve
`"cancelamento_orfao"` e nao escreve nada.

OS CASOS:

1. `tp_evento` diferente de `"110111"` (inclusive `None`) -> devolve `"cancelamento_orfao"` e NAO
   toca no banco. So o tipo `110111` e cancelamento; `110110` e carta de correcao, por exemplo.

2. `ch_nfe` e `None` -> devolve `"cancelamento_orfao"` e NAO toca no banco.

3. `ch_nfe` nao corresponde a nenhuma linha da tabela `notas` -> devolve `"cancelamento_orfao"`.

   PROIBIDO criar linha em `notas` neste caso. Um evento orfao nunca inventa a nota que falta.
   Nada de `INSERT`, nada de `INSERT OR IGNORE`.

4. `ch_nfe` corresponde a uma nota -> marca a nota como cancelada e devolve
   `"cancelamento_aplicado"`.

COMO MARCAR A NOTA — use exatamente este UPDATE:

```sql
UPDATE notas SET status = 'cancelada', cancelado_em = ? WHERE chave = ? AND status = 'ok'
```

O `AND status = 'ok'` no fim nao e enfeite: ele e o que faz a funcao ser idempotente. Aplicar o
mesmo evento duas vezes tem de deixar `cancelado_em` com o carimbo da PRIMEIRA vez, e o filtro por
`status = 'ok'` garante isso sem precisar de um segundo `if`.

ATENCAO: mesmo quando o UPDATE nao muda nenhuma linha porque a nota JA estava cancelada, a funcao
ainda devolve `"cancelamento_aplicado"`. A decisao entre aplicado e orfao depende de a NOTA EXISTIR,
nao de o UPDATE ter mudado alguma linha. Portanto confira a existencia com um SELECT antes:

```sql
SELECT 1 FROM notas WHERE chave = ?
```

O valor de `cancelado_em` e o instante atual em UTC no formato ISO, igual ao que `persistencia.py`
ja usa:

```python
from datetime import UTC, datetime

datetime.now(UTC).isoformat()
```

Use `conexao.execute(...)` com parametros `?`, nunca montando a SQL com f-string.
Chame `conexao.commit()` no fim, quando a funcao tiver escrito algo.

NAO altere nenhum outro arquivo.

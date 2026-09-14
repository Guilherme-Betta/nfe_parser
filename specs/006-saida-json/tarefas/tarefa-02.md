Acrescente a funcao `nota_para_json` ao arquivo `src/nfe_parser/serializacao.py`.

```python
def nota_para_json(conexao, chave: str) -> str | None:
    ...
```

Ela recebe uma conexao sqlite3 JA ABERTA e a chave de uma nota, e devolve uma **string** em JSON
com os dados daquela nota. Se a chave nao existir no banco, devolve `None`.

ATENCAO: devolve uma STRING, nao um `dict`. Quem chama faz `json.loads` no que voce devolveu.

COMO LER DO BANCO — use exatamente este SELECT, com estas colunas e nesta ordem:

```python
cursor = conexao.execute(
    "SELECT chave, modelo, serie, numero, dh_emi, emit_nome, emit_cnpj,"
    " emit_municipio, emit_uf, valor_total, forma_pagamento, status, cancelado_em"
    " FROM notas WHERE chave = ?",
    (chave,),
)
linha = cursor.fetchone()
if linha is None:
    return None
colunas = [d[0] for d in cursor.description]
dados = dict(zip(colunas, linha))
```

O `cursor.description` da os nomes das colunas na ordem em que vieram. E isso que evita montar o
dicionario contando posicoes na mao, que e onde nasce campo trocado.

E PROIBIDO mexer em `conexao.row_factory`. A conexao e de quem chamou; altera-la seria efeito
colateral em codigo que nao e desta tarefa.

AS CHAVES DA SAIDA — nesta ordem, e SO estas 14:

    chave, modelo, serie, numero, dh_emi, emit_nome, emit_cnpj, emit_municipio,
    emit_uf, valor_total_centavos, valor_total, forma_pagamento, status, cancelado_em

O DINHEIRO SAI DUAS VEZES, e as duas vezes vem do MESMO inteiro:

    valor_total_centavos  =  o inteiro cru da coluna `notas.valor_total`
    valor_total           =  de_centavos(aquele mesmo inteiro)

A funcao `de_centavos` ja esta neste arquivo, da tarefa anterior. Chame-a. NAO a reescreva, NAO a
altere e NAO formate o valor de outro jeito aqui.

⛔ `xml_raw`, `importacao_id` e `criado_em` NAO entram na saida. Nem os selecione no SQL acima.
NAO invente nenhum campo que nao esteja na lista das 14.

`status` e `cancelado_em` entram SEMPRE. Uma nota nao cancelada sai com `status` igual a `"ok"` e
`cancelado_em` igual a `null` — e assim que quem le o JSON distingue uma venda de uma venda
cancelada.

COMO SERIALIZAR:

```python
import json
return json.dumps(saida, ensure_ascii=False)
```

`ensure_ascii=False` NAO e opcional. O padrao do `json.dumps` e `True`, e com ele um municipio
escrito com til sai como `"S\u00e3o Paulo"` em vez do texto legivel. Ha um teste para isto.

NAO crie a chave `"itens"` ainda — a lista de itens e a proxima tarefa, nao esta.
NAO altere nenhum outro arquivo.

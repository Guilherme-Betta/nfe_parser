Acrescente a funcao `nota_para_json` ao arquivo `src/nfe_parser/serializacao.py`.

```python
def nota_para_json(conexao, chave: str) -> str | None:
    ...
```

Ela recebe uma conexao sqlite3 JA ABERTA e a chave de uma nota, e devolve uma **string** em JSON
com os dados daquela nota. Se a chave nao existir no banco, devolve `None`.

ATENCAO: devolve uma STRING, nao um `dict`.

COMO LER DO BANCO — use exatamente este SELECT:

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

E PROIBIDO mexer em `conexao.row_factory`: a conexao e de quem chamou.

AS CHAVES DA SAIDA — nesta ordem, e SO estas 14:

    chave, modelo, serie, numero, dh_emi, emit_nome, emit_cnpj, emit_municipio,
    emit_uf, valor_total_centavos, valor_total, forma_pagamento, status, cancelado_em

⛔ ESTE E O UNICO DEFEITO DA TENTATIVA ANTERIOR, E A UNICA COISA QUE PRECISA MUDAR DE IDEIA:

**`status` e `cancelado_em` sao COPIADOS DO BANCO SEM NENHUMA TRANSFORMACAO.**

    dados["status"]        ->  vai para a saida exatamente como veio
    dados["cancelado_em"]  ->  vai para a saida exatamente como veio

NAO escreva `if` nenhum em cima desses dois campos. NAO chame `.isoformat()`. NAO teste
`isinstance`. NAO importe `datetime`. NAO force `status` para `"ok"`. NAO troque valor por `None`.

O porque: o SQLite devolve coluna `TEXT` sempre como `str` (ou `None` quando vazia), nunca como
`datetime`. Um `isinstance(..., datetime)` e sempre falso, entao o `else` do ternario apagaria a
data de cancelamento de toda nota cancelada. O banco ja guarda o texto pronto; qualquer conversao
aqui so pode destruir dado.

O DINHEIRO SAI DUAS VEZES, as duas do MESMO inteiro:

    valor_total_centavos  =  o inteiro cru da coluna `notas.valor_total`
    valor_total           =  de_centavos(aquele mesmo inteiro)

`de_centavos` ja esta neste arquivo. Chame-a. NAO a altere.

⛔ `xml_raw`, `importacao_id` e `criado_em` NAO entram, e nem sao selecionados. NAO invente campo
fora da lista das 14.

COMO SERIALIZAR:

```python
import json
return json.dumps(saida, ensure_ascii=False)
```

`ensure_ascii=False` NAO e opcional: o padrao do `json.dumps` e `True`, e com ele um municipio
escrito com til sai ilegivel. Ha um teste para isto.

NAO crie a chave `"itens"` ainda — e a proxima tarefa. NAO altere nenhum outro arquivo.

O arquivo `src/nfe_parser/serializacao.py` JA EXISTE e ja tem TRES funcoes, nesta ordem:
`de_centavos`, `nota_para_json` e `_itens_da_nota`.

Voce vai devolver o arquivo INTEIRO. SO A TERCEIRA FUNCAO MUDA.

`de_centavos` e `nota_para_json` voltam EXATAMENTE como estao hoje: mesmo corpo, mesma docstring,
palavra por palavra. A docstring do topo do modulo tambem volta inteira, palavra por palavra. O
`import json` continua onde esta.

Em `_itens_da_nota` sao DUAS mudancas, e mais nada.


MUDANCA 1 -- O SELECT PASSA A TER DOIS `LEFT JOIN`

Hoje `_itens_da_nota` roda um SELECT direto na tabela `itens`. Troque a consulta inteira por esta,
exatamente assim:

```python
    cursor = conexao.execute(
        "SELECT i.n_item, i.descricao, i.cprod, i.ncm, i.gtin, i.quantidade,"
        " i.unidade, i.valor_unitario, i.valor_linha,"
        " c.slug AS categoria_slug, c.nome AS categoria"
        " FROM itens i"
        " LEFT JOIN produtos p ON p.id = i.produto_id"
        " LEFT JOIN categorias c ON c.id = p.categoria_id"
        " WHERE i.nota_chave = ? ORDER BY i.n_item",
        (chave,),
    )
```

As linhas abaixo dela NAO mudam:

```python
    colunas = [d[0] for d in cursor.description]
```

continua exatamente assim, e o `dict(zip(colunas, linha))` dentro do laco tambem.


MUDANCA 2 -- DUAS CHAVES NOVAS NO DICIONARIO DE SAIDA, NO FIM

O dicionario que o laco acrescenta em `itens` hoje termina em `"valor_linha": de_centavos(centavos)`.
Acrescente DUAS chaves DEPOIS dela, nesta ordem:

```python
                "valor_linha": de_centavos(centavos),
                "categoria_slug": item["categoria_slug"],
                "categoria": item["categoria"],
```

NAO mude nenhuma das dez chaves que ja estao la. NAO mude a ordem delas. `valor_linha_centavos` e
`valor_linha` continuam sendo as duas ultimas antes das novas.


REGRA 1 -- `LEFT JOIN`, E NUNCA `JOIN` NEM `INNER JOIN`. ESTE E O PONTO DA TAREFA.

Item sem produto e caso NORMAL e COMUM: toda nota importada antes desta mudanca tem `produto_id`
NULL. Com `INNER JOIN` esses itens SUMIRIAM da saida, a nota perderia linhas em silencio, e a soma
dos itens deixaria de bater com o total da nota.

Sao DOIS `LEFT JOIN` em sequencia, e o segundo tambem e `LEFT`: produto sem categoria tambem e caso
normal.


REGRA 2 -- AS DUAS CHAVES NOVAS APARECEM SEMPRE.

Quando nao ha produto, ou o produto nao tem categoria, elas valem `None`. NAO faca `if` para omitir a
chave. NAO troque `None` por `""`, por `"-"`, por `"sem categoria"` nem por `0`. NAO invente valor
padrao nenhum.


REGRA 3 -- NAO ACRESCENTE `produto_id` NEM `origem` NA SAIDA.

Sao duas chaves que NAO entram. Nao as ponha no SELECT, nao as ponha no dicionario.


REGRA 4 -- O `ORDER BY i.n_item` CONTINUA NO FIM DA CONSULTA.

Sem ele o SQLite nao garante ordem nenhuma.


REGRA 5 -- A CONSULTA CONTINUA PARAMETRIZADA COM `?` E A TUPLA `(chave,)`.

NAO monte SQL com f-string. NAO concatene a chave dentro do texto da consulta.


REGRA 6 -- NENHUMA LISTA, DICIONARIO OU CONSTANTE NOVA NO NIVEL DO MODULO.


O QUE NAO PODE MUDAR

`nota_para_json` nao muda em nada. Ela continua devolvendo `None` para chave ausente, continua com
`ensure_ascii=False`, continua sem `xml_raw`, sem `importacao_id` e sem `criado_em`, e continua
chamando `_itens_da_nota(conexao, chave)` na mesma linha.

`de_centavos` nao muda em nada.

A funcao continua se chamando `_itens_da_nota`, com o mesmo underscore na frente, a mesma assinatura
`(conexao, chave)` e a mesma docstring.

NAO faca `CREATE TABLE`, `ALTER TABLE` nem `CREATE INDEX`. As tabelas `produtos` e `categorias` ja
existem, com as colunas `id`, `produto_id`, `categoria_id`, `slug` e `nome` que a consulta usa.

NAO escreva nada que grave no banco: esta funcao so LE.

NAO altere nenhum outro arquivo do projeto, e NAO altere teste nenhum. O unico arquivo que voce
escreve e `src/nfe_parser/serializacao.py`. Se qualquer outro arquivo aparecer nesta conversa,
DEIXE-O EXATAMENTE COMO ESTA.

O arquivo `src/nfe_parser/varredura.py` E NOVO e esta VAZIO. Voce escreve o arquivo inteiro, e ele
tem UM import e UMA funcao. Nada mais.


O IMPORT

```python
from nfe_parser.categorizacao import classificar_produto
```

`classificar_produto(conexao, produto_id, ncm)` JA EXISTE e voce NAO a escreve. Ela roda a cascata
sobre UM produto, GRAVA o resultado na tabela `produtos` e devolve a categoria. Voce so a CHAMA.

NAO copie o corpo dela para ca. NAO reimplemente a cascata. NAO escreva nada sobre prefixo de NCM,
sobre a tabela de ancoras, nem sobre qual categoria e o bucket.


A FUNCAO

```python
def classificar_produtos_pendentes(conexao) -> int:
```

O ALGORITMO SAO QUATRO PASSOS, NESTA ORDEM

PASSO 1 -- leia a lista de pendentes INTEIRA, de uma vez, ANTES de qualquer laco:

```python
    pendentes = conexao.execute("SELECT id FROM produtos WHERE origem IS NULL").fetchall()
```

PASSO 2 -- para cada pendente, ache o NCM do item MAIS RECENTE dele:

```python
    for (produto_id,) in pendentes:
        linha = conexao.execute(
            "SELECT ncm FROM itens WHERE produto_id = ? ORDER BY id DESC LIMIT 1",
            (produto_id,),
        ).fetchone()
        ncm = linha[0] if linha else None
```

PASSO 3 -- ainda dentro do laco, classifique e veja se ele saiu do pendente:

```python
        classificar_produto(conexao, produto_id, ncm)
        origem = conexao.execute(
            "SELECT origem FROM produtos WHERE id = ?", (produto_id,)
        ).fetchone()[0]
        if origem is not None:
            resgatados += 1
```

PASSO 4 -- devolva a contagem:

```python
    return resgatados
```

`resgatados` comeca em `0`, numa linha ANTES do laco.


REGRA 1 -- PENDENTE E `origem IS NULL`, E NUNCA `categoria_id IS NULL`. ESTE E O PONTO DA TAREFA.

Produto que caiu no bucket TEM `categoria_id` preenchido e `origem` NULL, e e exatamente ele que esta
varredura existe para resgatar quando o mapa de NCM cresce. Uma consulta que procurasse
`categoria_id IS NULL` nunca mais olharia para o bucket, e o produto ficaria preso la para sempre.

NAO acrescente `AND categoria_id IS NULL`. NAO acrescente `OR categoria_id IS NULL`. A condicao e uma
so: `WHERE origem IS NULL`.


REGRA 2 -- O PASSO 1 LE TUDO ANTES, COM `.fetchall()`.

NAO itere sobre o cursor enquanto grava na mesma tabela. O laco faz UPDATE em `produtos`, e um cursor
aberto sobre `produtos` durante o UPDATE nao tem resultado definido.


REGRA 3 -- `ORDER BY id DESC LIMIT 1`, E O `id` E O DA TABELA `itens`.

Um produto pode ter varios itens, com NCMs diferentes. O que vale e o mais recente, que e o de maior
`id`. Sem `ORDER BY` o SQLite nao garante ordem nenhuma.


REGRA 4 -- PRODUTO SEM ITEM NENHUM NAO E ERRO.

`fetchone()` devolvendo `None` vira `ncm = None`, e `classificar_produto` e chamada assim mesmo. Ela
ja sabe o que fazer com NCM vazio. NAO pule o produto, NAO levante, NAO use `continue`.


REGRA 5 -- A CONTAGEM E DE QUEM SAIU DO PENDENTE, E SO ELA.

Conte `+1` quando a `origem` DEPOIS da classificacao nao for `None`. NAO conte quantos produtos foram
visitados. NAO conte quantos ficaram no bucket. NAO devolva lista, dicionario nem tupla: o retorno e
um `int`.

NAO compare a `origem` com nenhuma string. NAO escreva `origem == "ncm"`, `origem in (...)` nem nada
parecido. A unica comparacao e `is not None`.


REGRA 6 -- A FUNCAO NAO CHAMA `commit`, `rollback`, `BEGIN`, `close` NEM `PRAGMA`.

Quem abriu a transacao e que a fecha, e nao e esta funcao.


REGRA 7 -- A FUNCAO NAO GRAVA NADA POR CONTA PROPRIA.

NAO escreva `UPDATE`, `INSERT` nem `DELETE` nesta funcao. Quem grava e `classificar_produto`. As tres
consultas desta funcao sao todas `SELECT`.


REGRA 8 -- NENHUMA LISTA, DICIONARIO OU CONSTANTE NO NIVEL DO MODULO.

E NENHUMA outra funcao. O arquivo tem um import e uma funcao.


REGRA 9 -- TODA CONSULTA E PARAMETRIZADA COM `?`.

NAO monte SQL com f-string. NAO concatene `produto_id` dentro do texto da consulta.


O QUE NAO PODE ENTRAR

NAO importe nada alem de `classificar_produto`. Sem `sqlite3`, sem `datetime`, sem `json`, sem
`pathlib`, sem `logging`.

NAO faca `CREATE TABLE`, `ALTER TABLE` nem `CREATE INDEX`. As tabelas `produtos` e `itens` ja
existem, com as colunas `id`, `origem`, `produto_id` e `ncm` que as consultas usam.

NAO escreva `if __name__ == "__main__"`, NAO escreva `print`, NAO escreva argparse.

NAO altere nenhum outro arquivo do projeto, e NAO altere teste nenhum. O unico arquivo que voce
escreve e `src/nfe_parser/varredura.py`. Se qualquer outro arquivo aparecer nesta conversa,
DEIXE-O EXATAMENTE COMO ESTA.

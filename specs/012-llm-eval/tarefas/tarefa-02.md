O arquivo `src/nfe_parser/classificacao_llm.py` E NOVO e esta VAZIO. Voce escreve o arquivo inteiro.
Ele tem DOIS imports e UMA funcao. Nada mais.


OS IMPORTS

```python
from datetime import UTC, datetime

from nfe_parser.categorizacao import classificar_produto
```

`classificar_produto(conexao, produto_id, ncm)` JA EXISTE e voce NAO a escreve. Ela roda a cascata
sobre UM produto, GRAVA o resultado e devolve o `id` da categoria. Quando nada casa, ela grava o
bucket com `origem` NULL. Voce so a CHAMA.


A FUNCAO

```python
def classificar_produto_com_llm(conexao, produto_id, ncm, llm=None):
```

`llm` e uma funcao `llm(descricao, slugs)` que devolve `None` ou uma tupla `(slug, confianca)`.


O ALGORITMO SAO SEIS PASSOS, NESTA ORDEM

PASSO 1 -- rode a cascata, SEMPRE, e guarde o resultado:

```python
    categoria = classificar_produto(conexao, produto_id, ncm)
    if llm is None:
        return categoria
```

PASSO 2 -- releia o produto. Se a `origem` NAO e `None`, a cascata resolveu: devolva sem chamar o
`llm`. Se nao ha descricao, tambem:

```python
    origem, descricao = conexao.execute(
        "SELECT origem, descricao_exemplo FROM produtos WHERE id = ?", (produto_id,)
    ).fetchone()
    if origem is not None or not descricao:
        return categoria
```

PASSO 3 -- monte a lista de slugs, SEM o bucket, EM ORDEM:

```python
    slugs = [
        linha[0]
        for linha in conexao.execute(
            "SELECT slug FROM categorias WHERE is_bucket = 0 ORDER BY slug"
        ).fetchall()
    ]
```

PASSO 4 -- pergunte ao `llm`. `None` e "nao sei": devolva o que a cascata deu.

```python
    resposta = llm(descricao, slugs)
    if resposta is None:
        return categoria
    slug, confianca = resposta
```

PASSO 5 -- confira o slug NO BANCO. Nao achou, nao grava:

```python
    linha = conexao.execute(
        "SELECT id FROM categorias WHERE slug = ? AND is_bucket = 0", (slug,)
    ).fetchone()
    if linha is None:
        return categoria
```

PASSO 6 -- grave e devolva:

```python
    conexao.execute(
        "UPDATE produtos SET categoria_id = ?, origem = 'llm', confianca = ?, atualizado_em = ?"
        " WHERE id = ?",
        (linha[0], confianca, datetime.now(UTC).isoformat(), produto_id),
    )
    return linha[0]
```


REGRA 1 -- O `llm` SO E CHAMADO QUANDO A `origem` E `None` DEPOIS DA CASCATA.

Produto com `origem` `'manual'`, `'memoria'` ou `'ncm'` NUNCA chega ao `llm`. NAO compare a `origem`
com nenhuma string. A unica comparacao e `is not None`.


REGRA 2 -- O PASSO 5 NAO SE PULA, MESMO QUE O SLUG ESTEJA EM `slugs`.

O `llm` e um parametro e pode ser QUALQUER funcao. Quem garante que nenhuma categoria e inventada e
a consulta do passo 5. O `AND is_bucket = 0` tambem nao se tira.


REGRA 3 -- A FUNCAO NAO CHAMA `commit`, `rollback`, `BEGIN`, `close` NEM `PRAGMA`.


REGRA 4 -- NAO reimplemente a cascata. NAO escreva nada sobre NCM, prefixo ou ancora. NAO busque o
bucket. Quem cuida disso e `classificar_produto`.


REGRA 5 -- NAO ponha `try`/`except` em volta do `llm`. Se ele levantar, o erro SOBE.


O QUE NAO PODE ENTRAR

NAO importe nada alem dos dois imports acima. NAO faca `CREATE TABLE` nem `ALTER TABLE`: as colunas
`origem`, `confianca`, `descricao_exemplo` e `atualizado_em` ja existem. Toda consulta e
parametrizada com `?`: NAO monte SQL com f-string. NAO escreva `print` nem constante no nivel do
modulo.

NAO altere nenhum outro arquivo do projeto, e NAO altere teste nenhum. O unico arquivo que voce
escreve e `src/nfe_parser/classificacao_llm.py`. Se qualquer outro arquivo aparecer nesta conversa,
DEIXE-O EXATAMENTE COMO ESTA.

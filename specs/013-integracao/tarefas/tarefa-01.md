O arquivo `src/nfe_parser/persistencia.py` JA EXISTE e ja tem UMA funcao: `persistir_nota`.

Voce vai devolver o arquivo INTEIRO. Sao TRES mudancas nele, e mais nada.


MUDANCA 1 -- ACRESCENTE UMA FUNCAO NOVA, ANTES de `persistir_nota`

```python
def resolver_produto_do_item(conexao, item, emit_cnpj):
    if item["gtin"]:
        return resolver_produto_por_gtin(conexao, item["gtin"], item["descricao"])
    return resolver_produto_por_texto(conexao, item["descricao"], emit_cnpj)
```

Ela precisa destas duas funcoes, que JA EXISTEM e que voce NAO escreve. Acrescente esta linha de
import no topo do arquivo, depois dos imports que ja estao la:

```python
from nfe_parser.produtos import resolver_produto_por_gtin, resolver_produto_por_texto
```

`resolver_produto_por_gtin(conexao, gtin, descricao_exemplo)` devolve um `int`, o id do produto.
`resolver_produto_por_texto(conexao, descricao, emit_cnpj)` devolve um `int`, o id do produto.

NAO reescreva nenhuma das duas. NAO copie o corpo delas para ca. Voce so as CHAMA.


MUDANCA 2 -- DENTRO DO LACO DOS ITENS, RESOLVA O PRODUTO E GRAVE O ID

O laco `for item in itens:` de `persistir_nota` hoje monta `valores_itens` e executa um INSERT.

Faca DUAS coisas nele:

(a) A PRIMEIRA linha de dentro do laco passa a ser a resolucao:

```python
    for item in itens:
        produto_id = resolver_produto_do_item(conexao, item, nota["emit_cnpj"])
```

(b) A coluna `produto_id` entra no INSERT. A lista `campos_itens` hoje termina em `"criado_em"`.
Acrescente `"produto_id"` DEPOIS de `"criado_em"`, como ultimo elemento. E na lista `valores_itens`,
acrescente `produto_id` DEPOIS do `datetime.now(UTC).isoformat()`, tambem como ultimo elemento.

AS DUAS LISTAS TEM DE TERMINAR NA MESMA POSICAO: campo `"produto_id"` e valor `produto_id`. Se uma
lista tiver 12 elementos e a outra 11, o INSERT quebra.

NAO mude a ordem dos outros campos. NAO tire campo nenhum. NAO renomeie nada.


MUDANCA 3 -- APAGUE O `commit`

As duas ultimas linhas antes do `return "nova"` sao um comentario e uma chamada:

```python
    # Commitando as mudancas
    conexao.commit()
```

APAGUE AS DUAS. A funcao passa a terminar assim:

```python
        conexao.execute(query_itens, valores_itens)

    return "nova"
```

NAO troque por `rollback`, NAO troque por `BEGIN`, NAO ponha `try`/`except` em volta. So APAGUE.


REGRA 1 -- A ORDEM DENTRO DO LACO IMPORTA, E E ESTA: RESOLVER, DEPOIS INSERIR.

Resolver o produto e inserir o item tem de acontecer na MESMA transacao. E por isso que o `commit`
some: quem abriu a transacao e que a fecha, e nao e esta funcao.


REGRA 2 -- ESTA FUNCAO NAO CLASSIFICA NADA.

NAO escreva `categoria_id`. NAO escreva `origem`. NAO chame nada com "categoria", "cascata",
"classificar", "ncm ancora" ou "bucket" no nome. O produto nasce sem categoria DE PROPOSITO, e quem
classifica e outro modulo, que nao e esta tarefa.


REGRA 3 -- A CHECAGEM DE DUPLICADA CONTINUA ONDE ESTA, E CONTINUA SENDO A PRIMEIRA COISA.

O `return "duplicada"` acontece ANTES de qualquer INSERT e ANTES de qualquer resolucao de produto.
Nota duplicada NAO pode criar produto nenhum.


REGRA 4 -- SE A RESOLUCAO LEVANTAR `ValueError`, DEIXE SUBIR.

NAO ponha `try`/`except` em volta da chamada. NAO devolva None. NAO pule o item. NAO invente um valor
padrao para o CNPJ. O erro tem de subir inteiro.


REGRA 5 -- `resolver_produto_do_item` TEM EXATAMENTE TRES LINHAS DE CORPO.

Um `if`, um `return` dentro dele, um `return` fora. NAO acrescente validacao, NAO acrescente
`try`/`except`, NAO acrescente log, NAO acrescente cache, NAO acrescente dicionario no nivel do
modulo.


REGRA 6 -- NENHUMA LISTA, DICIONARIO OU CONSTANTE NOVA NO NIVEL DO MODULO.


O QUE NAO PODE MUDAR

`persistir_nota` continua com a mesma assinatura, a mesma docstring e os mesmos dois retornos,
`"duplicada"` e `"nova"`.

O INSERT em `notas` nao muda em nada: mesmos campos, mesma ordem, mesmos valores.

Os imports `import sqlite3` e `from datetime import UTC, datetime` continuam no topo, como estao.

NAO faca `CREATE TABLE`, `ALTER TABLE` nem `CREATE INDEX`. A coluna `produto_id` ja existe na tabela.

NAO altere nenhum outro arquivo do projeto, e NAO altere teste nenhum. O unico arquivo que voce
escreve e `src/nfe_parser/persistencia.py`. Se qualquer outro arquivo aparecer nesta conversa,
DEIXE-O EXATAMENTE COMO ESTA.

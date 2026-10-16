Acrescente UMA funcao ao arquivo `src/nfe_parser/produtos.py`:

```python
def resolver_produto_por_texto(conexao, descricao, emit_cnpj):
    ...
```

Ela devolve o `id` (inteiro) da linha de `produtos` que representa aquele produto SEM codigo de
barras, criando a linha se ela ainda nao existir.

E a mesma forma da funcao anterior -- procurar, criar se nao achou, devolver o id -- com outra
chave: em vez do GTIN, o par (descricao normalizada, CNPJ da loja).


AS DUAS FUNCOES QUE JA ESTAO NO ARQUIVO E NAO SE MEXEM

`normalizar_descricao` esta pronta e testada. NAO mexa nela. CHAME-a.

`resolver_produto_por_gtin` esta pronta e testada. NAO mexa nela. Esta tarefa nao a chama.

⛔ Se algum teste desta tarefa parecer pedir uma normalizacao diferente, ele NAO esta pedindo isso.
Ajustar `normalizar_descricao` deixa o modulo de teste dela vermelho.


O ALGORITMO, NESTA ORDEM

1. `normalizada = normalizar_descricao(descricao)`
2. PROCURE com este SELECT, exatamente assim:

```sql
SELECT id FROM produtos
 WHERE gtin IS NULL AND descricao_normalizada = ? AND emit_cnpj = ?
```

3. Se achou, devolva o `id` encontrado e PARE. Nao atualize nada.
4. Se nao achou, INSIRA uma linha nova e devolva `cursor.lastrowid`.

Na linha nova, grave exatamente estes campos e nenhum outro:

| coluna | valor |
| ------ | ----- |
| `identidade_origem` | a string `'texto'` |
| `descricao_normalizada` | o resultado do passo 1 |
| `emit_cnpj` | o `emit_cnpj` recebido |
| `descricao_exemplo` | a `descricao` recebida, CRUA, sem normalizar |
| `criado_em` | `datetime.now(UTC).isoformat()` |
| `atualizado_em` | o mesmo valor de `criado_em` |

`gtin`, `categoria_id`, `origem` e `confianca` NAO entram no INSERT. Ficam NULL, e ha teste
afirmando que `gtin` e NULL.


REGRA 1 -- 🔴 O `gtin IS NULL` DO SELECT NAO E ENFEITE.

A busca por texto so enxerga produtos SEM codigo de barras. Quem tem GTIN e identificado pelo
GTIN, e nunca deve ser devolvido por esta funcao -- nem que a descricao seja identica.

Existe indice unico parcial no banco que so cobre `(descricao_normalizada, emit_cnpj)` quando
`gtin IS NULL`. Um SELECT sem essa condicao procuraria em linhas que aquele indice nem cobre.

Ha teste que cria um produto por GTIN e depois chama esta funcao com a mesma descricao, e exige
DOIS produtos distintos.


REGRA 2 -- 🔴 O CNPJ FAZ PARTE DA CHAVE. ISSO E REQUISITO, NAO DETALHE.

A MESMA descricao vinda de CNPJs DIFERENTES tem de gerar DOIS produtos distintos, com ids
diferentes.

⛔ Nao "melhore" isso casando so pela descricao. Cada loja escreve o `xProd` do seu jeito, e casar
entre lojas sem codigo de barras produziria historico de preco misturando produtos diferentes, sem
ninguem ter como notar. A coluna `identidade_origem = 'texto'` existe exatamente para avisar quem
consome que aquele casamento vale so dentro da loja.

Os dois valores entram no WHERE e os dois entram no INSERT.


REGRA 3 -- ⛔ NADA DE `INSERT OR IGNORE`, `ON CONFLICT` OU `INSERT OR REPLACE`.

Procure primeiro com SELECT, insira so no ramo em que nao achou. Com `OR IGNORE` o INSERT
descartado deixa `lastrowid` com um valor que nao e o id daquela linha, e a funcao devolveria o id
errado na segunda chamada, em silencio. Ha teste que chama duas vezes e compara os ids.


REGRA 4 -- ⛔ NAO CHAME `conexao.commit()`.

Quem abriu a transacao e que a fecha. Este modulo so escreve. Tambem nao chame `rollback`, `BEGIN`
nem `close`.


REGRA 5 -- NENHUMA CATEGORIA.

`categoria_id`, `origem` e `confianca` ficam NULL. Ha teste afirmando isso.


O QUE NAO PODE MUDAR

NAO altere `normalizar_descricao` nem `resolver_produto_por_gtin`.

NAO altere a constante `PERMITIDOS`, e NAO escreva uma segunda copia dela. Ela ja esta no arquivo.

NAO faca `CREATE TABLE`, `ALTER TABLE` nem `CREATE INDEX`. O esquema ja esta pronto.

NAO altere nenhum outro arquivo: nem `banco.py`, nem `migracoes.py`, nem teste nenhum.

Acrescente UMA funcao ao FIM de `src/nfe_parser/categorizacao.py`:

```python
def definir_categoria_manual(conexao, produto_id, categoria_id):
    ...
```

Ela grava a decisao de um HUMANO sobre a categoria de um produto. Nao devolve nada (`None`).

E a contraparte do passo 1 da cascata: `classificar_produto` ja recusa sobrescrever
`origem in ("manual", "memoria")`. Esta funcao e quem POE o `"manual"` la.


O ALGORITMO, NESTA ORDEM

1. CONFIRME que o produto existe:

```python
linha = conexao.execute("SELECT id FROM produtos WHERE id = ?", (produto_id,)).fetchone()
if linha is None:
    raise LookupError(f"produto {produto_id} nao existe")
```

2. GRAVE, com UM unico UPDATE:

```python
conexao.execute(
    "UPDATE produtos SET categoria_id = ?, origem = 'manual', atualizado_em = ? WHERE id = ?",
    (categoria_id, datetime.now(UTC).isoformat(), produto_id),
)
```

3. Nao devolva nada.

O import do relogio ja esta no arquivo, da tarefa anterior:

```python
from datetime import UTC, datetime
```


REGRA 1 -- A `origem` VAI FIXA NO SQL, COMO `'manual'`.

Ela nao e parametro da funcao. Nao existe chamada desta funcao que queira gravar outra origem: se
um humano esta decidindo, a origem E `manual`. ⛔ Nao acrescente um quarto parametro.


REGRA 2 -- 🔴 ELA SOBRESCREVE SEM PERGUNTAR, E ISSO E DE PROPOSITO.

O humano tem a palavra final. Se o produto ja tinha categoria vinda do NCM, a nova apaga a antiga.
⛔ Nao escreva `if origem_atual == "manual": return`, nem checagem nenhuma sobre a categoria que ja
estava la.

⚠️ A assimetria e o ponto da story: a MAO sobrescreve a MAQUINA, e a maquina nunca sobrescreve a
mao. Ha teste que classifica pelo NCM, chama esta funcao por cima, e exige que a nova valha.


REGRA 3 -- ⛔ NAO VALIDE O `categoria_id` CONTRA A TABELA `categorias`.

A coluna ja tem `REFERENCES categorias(id)`, e o `abrir_banco` liga `PRAGMA foreign_keys = ON`. Uma
categoria inexistente ja levanta `sqlite3.IntegrityError` sozinha, vinda do banco.

Ha teste que passa um `categoria_id` inexistente e espera exatamente `sqlite3.IntegrityError`.
Um `SELECT` a mais aqui trocaria essa excecao por outra e deixaria o teste vermelho.


REGRA 4 -- A CHECAGEM DE EXISTENCIA DO PRODUTO E NECESSARIA, E E OUTRA COISA.

Aquela nao sai de graca: `WHERE id = NULL` nao casa com nada, e sem o `if linha is None: raise` o
UPDATE afetaria ZERO linhas em silencio -- a funcao voltaria como se tivesse gravado.

⛔ `LookupError`, NAO `ValueError`: o argumento esta bem formado; o que falta e a linha no banco.


REGRA 5 -- ⛔ NAO CHAME `conexao.commit()`.

Quem abriu a transacao e que a fecha. Nenhum teste pegaria isso (a mesma conexao enxerga o que ela
mesma nao commitou), e por isso a regra esta escrita aqui: e revisao humana, nao teste.

⛔ Tambem nao chame `rollback`, `BEGIN`, `close` nem `execute("PRAGMA ...")`.


REGRA 6 -- ⛔ NENHUMA LISTA OU DICIONARIO NO NIVEL DO MODULO.

Acrescente a funcao DEPOIS da ultima linha do arquivo. O modulo continua sendo imports + funcoes.


O QUE NAO PODE MUDAR

NAO altere `buscar_categoria_por_ncm`, `_categoria_do_bucket` nem `classificar_produto`. As tres ja
passam nos testes delas, e mexer nelas as deixa vermelhas.

⛔ Em especial: NAO mexa no passo 1 de `classificar_produto`. A tupla `("manual", "memoria")` ja
esta certa e ja e o que faz esta tarefa funcionar de ponta a ponta.

NAO faca `CREATE TABLE`, `ALTER TABLE` nem `CREATE INDEX`. O esquema ja esta pronto.

NAO escreva nada sobre LLM nem sobre `confianca`. Nao e desta story.

NAO altere nenhum outro arquivo: nem `banco.py`, nem `migracoes.py`, nem `produtos.py`, nem teste
nenhum.

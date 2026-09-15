Acrescente a SEGUNDA migracao ao arquivo `src/nfe_parser/migracoes.py`.

O executor e a migracao 01 ja estao prontos e passando. NAO mexa em nenhum dos dois.

Escreva uma funcao NOVA e acrescente-a AO FIM de `MIGRACOES`:

```python
def _migracao_02_produto_id_em_itens(conexao):
    ...


MIGRACOES = [_migracao_01_esquema_classificacao, _migracao_02_produto_id_em_itens]
```

Ela roda exatamente dois comandos:

```sql
ALTER TABLE itens ADD COLUMN produto_id INTEGER REFERENCES produtos(id);
CREATE INDEX IF NOT EXISTS idx_itens_produto ON itens(produto_id);
```


REGRA 1 -- CRIE MIGRACAO NOVA. NAO EDITE A 01. Esta e a parte importante da tarefa.

O caminho curto e acrescentar o `ALTER TABLE` dentro de `_migracao_01_esquema_classificacao`, ja
que ela esta logo ali. Isso esta ERRADO, e o motivo nao e estilo.

O executor roda so as migracoes com versao MAIOR que a versao atual do banco. Um banco que ja
rodou a migracao 01 esta marcado com `user_version = 1`. Se o `ALTER TABLE` entrasse dentro da 01,
aquele banco NUNCA receberia a coluna: a versao dele ja diz "01 aplicada", e o executor pularia.
O banco ficaria meio migrado para sempre.

Uma migracao que ja pode ter rodado e imutavel. Mudanca de esquema e sempre uma migracao NOVA.

A funcao 01 tem de terminar esta tarefa com o corpo identico ao que tem agora.


REGRA 2 -- `ALTER TABLE ADD COLUMN` NAO ACEITA `IF NOT EXISTS`, E NAO PRECISA.

O SQLite nao tem `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`. Rodar duas vezes da:

    sqlite3.OperationalError: duplicate column name: produto_id

NAO tente contornar isso. Nao consulte `PRAGMA table_info` antes, nao use `try/except` em volta
do `ALTER`, nao teste se a coluna existe.

O executor JA resolve: ele so chama esta migracao quando `user_version` e menor que 2, e grava a
versao ao terminar. Na segunda abertura do banco a versao ja e 2 e esta funcao nem e chamada. E
para isso que o controle de versao existe.

Um `try/except` em volta do `ALTER` mascararia o unico sintoma de um executor quebrado.

O `CREATE INDEX` mantem o `IF NOT EXISTS` do DDL acima -- ele nao custa nada e e o padrao do
projeto.


REGRA 3 -- A COLUNA NASCE NULA, E ISSO E O CERTO.

Nenhum `DEFAULT`, nenhum `NOT NULL`, nenhum `UPDATE` para preencher.

Um banco que ja tem itens gravados vai ficar com `produto_id` NULL em todas as linhas antigas, e
esse e o comportamento esperado: ninguem sabe ainda qual produto e cada item. Quem preenche e
outra story.

E o `REFERENCES produtos(id)` tem de estar la. Ele faz a chave estrangeira valer para insercoes
novas -- inserir item com `produto_id` que nao existe em `produtos` passa a dar `IntegrityError`.
Ha teste para isso. `ALTER TABLE ADD COLUMN` com `REFERENCES` funciona com
`PRAGMA foreign_keys = ON` porque a coluna nasce com default NULL. Foi medido.


REGRA 4 -- NADA DE `executescript`.

Como nas tarefas anteriores: `executescript` faz COMMIT implicito e destroi a transacao do
executor. Use `conexao.execute(...)`, um comando por chamada.


O QUE NAO PODE MUDAR:

NAO altere `versao_do_banco`, `aplicar_migracoes` nem `_migracao_01_esquema_classificacao`.

NAO altere `banco.py`. A chamada a `aplicar_migracoes` ja esta la e ja esta na ordem certa.

NAO crie tabela nenhuma, nao insira dado nenhum.

NAO altere nenhum outro arquivo.

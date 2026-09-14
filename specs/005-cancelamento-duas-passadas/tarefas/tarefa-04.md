Em `src/nfe_parser/importador.py`, faca o contador `cancelamentos_aplicados` contar de verdade.

Hoje, no `UPDATE importacoes` que fecha a importacao, existe esta linha:

```sql
cancelamentos_aplicados = 0
```

Era um valor fixo porque, ate a tarefa anterior, nenhum evento podia ser aplicado. Agora pode.

TROQUE por uma subconsulta no mesmo formato das outras cinco que ja estao ali:

```sql
cancelamentos_aplicados = (
    SELECT COUNT(*) FROM importacao_arquivos
    WHERE importacao_id = ? AND resultado = 'cancelamento_aplicado'
),
```

ATENCAO AO NUMERO DE PARAMETROS. O `conexao.execute` que dispara esse UPDATE recebe uma tupla de
parametros posicionais. Cada `?` novo exige mais um `importacao_id` nessa tupla, na posicao certa.
Hoje sao seis `?`; passam a ser sete. Se voce esquecer de acrescentar o parametro, o erro vem como
`sqlite3.ProgrammingError: Incorrect number of bindings`.

O contador conta SOMENTE `resultado = 'cancelamento_aplicado'`. Os orfaos
(`'cancelamento_orfao'`) NAO entram nele — eles continuam contando apenas no `total_arquivos`, e
nao existe coluna no banco para orfaos.

NAO mexa em mais nada. As duas passadas ja estao funcionando e os outros cinco contadores ja estao
certos. Esta tarefa e uma troca de linha.

NAO altere nenhum outro arquivo.

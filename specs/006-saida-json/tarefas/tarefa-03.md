Altere a funcao `nota_para_json`, em `src/nfe_parser/serializacao.py`, para incluir os itens da
nota na saida.

Hoje ela devolve so os 14 campos da nota. Acrescente UMA chave nova, `"itens"`, como a ULTIMA
chave da saida. O valor dela e uma lista.

COMO LER OS ITENS — use exatamente este SELECT:

```python
cursor_itens = conexao.execute(
    "SELECT n_item, descricao, cprod, ncm, gtin, quantidade, unidade,"
    " valor_unitario, valor_linha"
    " FROM itens WHERE nota_chave = ? ORDER BY n_item",
    (chave,),
)
```

O `ORDER BY n_item` nao e detalhe: sem ele o SQLite nao garante ordem, e a lista sairia embaralhada
sem aviso. Ha um teste que insere os itens fora de ordem e espera a saida ordenada.

AS CHAVES DE CADA ITEM — nesta ordem, e SO estas 10:

    n_item, descricao, cprod, ncm, gtin, quantidade, unidade, valor_unitario,
    valor_linha_centavos, valor_linha

O DINHEIRO DO ITEM SAI DUAS VEZES, do MESMO inteiro, igual ao da nota:

    valor_linha_centavos  =  o inteiro cru da coluna `itens.valor_linha`
    valor_linha           =  de_centavos(aquele mesmo inteiro)

⛔ `id` e `nota_chave` NAO entram: o primeiro e chave artificial do SQLite, o segundo ja esta na
nota que contem a lista.

NOTA SEM ITEM NENHUM: a chave `"itens"` sai como lista vazia `[]`. NAO sai como `null`, e a funcao
NAO levanta.

CHAVE INEXISTENTE: continua devolvendo `None`, como ja faz. Devolva `None` ANTES de consultar os
itens — nao adianta buscar item de uma nota que nao existe.

O QUE NAO PODE MUDAR:

- as 14 chaves da nota continuam as mesmas, na mesma ordem, com os mesmos valores
- `json.dumps(..., ensure_ascii=False)` continua
- `de_centavos` continua exatamente como esta

Os testes da tarefa anterior continuam rodando. Se voce reescrever `nota_para_json` do zero e mudar
algo daquela lista, eles ficam vermelhos.

NAO altere nenhum outro arquivo.

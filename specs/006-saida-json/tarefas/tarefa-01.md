Crie a funcao `de_centavos` no arquivo `src/nfe_parser/serializacao.py`.

O arquivo ainda NAO existe. Crie-o.

```python
def de_centavos(centavos: int) -> str:
    ...
```

Ela recebe um valor monetario em centavos (inteiro) e devolve a representacao decimal com
EXATAMENTE duas casas, como string.

    12345  ->  "123.45"
    100    ->  "1.00"
    5      ->  "0.05"
    0      ->  "0.00"

REGRA 1 — SO ARITMETICA DE INTEIRO. Esta e a parte importante da tarefa.

E PROIBIDO usar `/`, `float()`, `round()` ou `Decimal` para chegar ao resultado.

O motivo: `centavos / 100` e divisao de ponto flutuante binario, e ponto flutuante binario nao
representa decimais exatamente. O erro nao aparece em 12345, aparece em valores grandes — e existe
um teste com um valor grande o bastante para o float perder o centavo. Se voce usar divisao, aquele
teste fica vermelho.

Use `//` (divisao inteira) para a parte dos reais e `%` (resto) para a parte dos centavos, e
formate os centavos com dois digitos:

```python
f"{reais}.{resto:02d}"
```

O `:02d` nao e enfeite: sem ele, 5 centavos sairiam como "0.5" em vez de "0.05".

REGRA 2 — O SINAL NEGATIVO.

`-5 // 100` da `-1` e `-5 % 100` da `95`. Ou seja, a forma ingenua devolveria "-1.95" para cinco
centavos negativos, que esta errado: o certo e "-0.05".

Separe o sinal ANTES de dividir e opere sobre o valor absoluto:

```python
sinal = "-" if centavos < 0 else ""
valor = abs(centavos)
```

Depois monte o resultado com o sinal na frente. Ha um teste para isto.

NAO faca mais nada neste arquivo. As funcoes `nota_para_json` e a leitura do banco sao as proximas
tarefas, nao esta. NAO importe `json` aqui. NAO altere nenhum outro arquivo.

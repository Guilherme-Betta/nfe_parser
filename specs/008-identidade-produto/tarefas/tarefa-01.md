Crie o arquivo NOVO `src/nfe_parser/produtos.py` com UMA funcao publica:

```python
def normalizar_descricao(descricao: str) -> str:
    ...
```

Ela recebe a descricao crua de um item de nota fiscal (o `xProd` do XML) e devolve uma chave de
igualdade: duas descricoes que sao o mesmo produto escrito de jeitos diferentes tem de sair iguais.

O arquivo comeca vazio. Escreva `import unicodedata`, a constante `PERMITIDOS` e a funcao. NADA
MAIS.


OS QUATRO PASSOS, NESTA ORDEM

1. `descricao.lower()`
2. decompor em NFD com `unicodedata.normalize("NFD", ...)` e DESCARTAR todo caractere cuja
   `unicodedata.category(c)` seja `"Mn"` (marca de combinacao). E isto que tira o acento.
3. todo caractere que NAO estiver em `PERMITIDOS` vira um ESPACO
4. `" ".join(texto.split())` — colapsa espacos repetidos e tira os das bordas

Use exatamente esta constante, no nivel do modulo:

```python
PERMITIDOS = "abcdefghijklmnopqrstuvwxyz0123456789"
```


REGRA 1 -- ⛔ NAO USE `isalnum()`. FOI MEDIDO, E ESTA ERRADO AQUI.

A forma obvia do passo 3 seria `c if c.isalnum() else " "`. Ela NAO serve.

`str.isalnum()` e Unicode-aware: para o Python, `º`, `ø` e `µ` sao letra ou numero. Eles tambem nao
tem acento para o NFD tirar (a barra do `ø` e parte do proprio caractere), entao passam pelo passo
2 E pelo passo 3, e a saida deixa de ser ASCII.

Medido no clone, com o Python deste venv:

| entrada      | com `isalnum()` | com `PERMITIDOS` |
| ------------ | --------------- | ---------------- |
| `1º PRECO`   | `1º preco`  ERRADO | `1 preco`     CERTO |
| `ø10mm`      | `ø10mm`     ERRADO | `10mm`        CERTO |
| `µg VITAMINA`| `µg vitamina` ERRADO | `g vitamina` CERTO |

O teste afirma que a saida so contem `a-z`, `0-9` e espaco, para QUALQUER entrada. Com `isalnum()`
ele fica vermelho.

⛔ Nao use `isalpha`, `isdigit`, `isascii` nem `str.translate` no lugar. Use `c in PERMITIDOS`.


REGRA 2 -- O PASSO 2 VEM ANTES DO PASSO 3. NAO INVERTA.

Se o filtro de `PERMITIDOS` rodar antes da decomposicao NFD, o `ç` nao vira `c` -- ele e jogado
fora inteiro, e `acucar` sai como `a ucar`: dois tokens onde havia um. Ha teste para isso.

Tire o acento PRIMEIRO. Filtre DEPOIS.


REGRA 3 -- PONTUACAO VIRA ESPACO, NAO VIRA VAZIO.

`COCA-COLA 2L` tem de sair como `coca cola 2l`, com o traco virando espaco.

⛔ Nao apague o caractere proibido. Se apagasse, `PAO/QUEIJO` viraria `paoqueijo` -- uma palavra
que nao existe. Trocar por espaco nunca inventa palavra nova.


REGRA 4 -- NAO INTERPRETE NUMERO NEM UNIDADE.

Numero e unidade sao texto como qualquer outro. Eles atravessam a funcao sem tratamento especial.

⛔ Nenhuma conversao de unidade, nenhum arredondamento, nenhuma separacao de `5kg` em `5` e `kg`,
nenhuma remocao de numero. `ARROZ TIPO 1 - 5KG` sai como `arroz tipo 1 5kg`.

Consequencia normal e esperada: `Refrig. 1,5L` sai como `refrig 1 5l`, porque a virgula e
pontuacao como qualquer outra. Isso esta CERTO. Nao tente salvar a virgula dos numeros.


REGRA 5 -- ⛔ NAO IMPORTE `re`, E NAO ESCREVA BARRA INVERTIDA NENHUMA.

Os quatro passos se fazem com `lower`, `unicodedata`, um laco e `split`/`join`. Expressao regular
nao e necessaria e nao e aceita nesta tarefa.

Nenhuma string deste arquivo deve conter barra invertida.


REGRA 6 -- A FUNCAO E TOTAL: NENHUMA EXCECAO.

Entrada vazia devolve `""`. Entrada so de espacos devolve `""`. Entrada so de pontuacao (`"!!!"`)
devolve `""`.

⛔ Nao levante `ValueError`, nao devolva `None`, nao trate `None` na entrada. A funcao recebe `str`
e devolve `str`, sempre.


O QUE NAO PODE MUDAR

NAO altere nenhum outro arquivo. Nem `banco.py`, nem `migracoes.py`, nem teste nenhum.

NAO escreva nenhuma outra funcao neste arquivo. As proximas tarefas acrescentam as delas.

NAO toque no banco de dados. Esta tarefa e so texto: ela nao abre conexao, nao faz SELECT, nao faz
INSERT e nao importa `sqlite3`.

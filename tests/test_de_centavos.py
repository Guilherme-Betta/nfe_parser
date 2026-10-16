"""Testes de `de_centavos` — tarefa 1 da story 006-saida-json.

Escritos ANTES da implementacao (passo 2 do loop) e congelados por commit. O
modelo local recebe este arquivo como LEITURA (`--read`), nunca como arquivo
editavel: se ele puder editar o teste, ele edita o teste para faze-lo passar,
que e o caminho mais curto para o objetivo dado.

⭐ ESTE MODULO E SEPARADO DOS OUTROS DOIS DA STORY de proposito. A story esta
fatiada em tres tarefas, e `story fatiada em N tarefas = testes em N modulos`:
se `nota_para_json` fosse importada aqui, o modulo inteiro falharia na COLETA
depois da tarefa 1, porque aquela funcao ainda nao existiria.

Criterios em `specs/006-saida-json/spec.md` §4, bloco C1.
"""

from nfe_parser.serializacao import de_centavos


def test_de_centavos_converte_o_caso_comum():
    assert de_centavos(12345) == "123.45"


def test_de_centavos_nao_usa_float():
    """⛔ NAO REMOVA. Este teste e a razao de a tarefa existir separada.

    `centavos / 100` e o reflexo que qualquer implementacao escreve primeiro, e
    ele PASSA em 12345. O ponto flutuante binario tem 53 bits de mantissa, entao
    acima de 2**53 ele deixa de representar inteiros exatamente -- e o valor
    abaixo e 2**53 + 1, escolhido para cair fora dessa faixa.

    Com aritmetica de inteiro (`//` e `%`) o resultado e exato em qualquer
    magnitude. Com `/` ou `float()`, o ultimo centavo se perde em silencio.
    """
    assert de_centavos(9007199254740993) == "90071992547409.93"


def test_de_centavos_preenche_o_zero_a_esquerda_dos_centavos():
    """Sem o `:02d`, cinco centavos sairiam como "0.5" -- dez vezes o valor."""
    assert de_centavos(5) == "0.05"


def test_de_centavos_zero():
    assert de_centavos(0) == "0.00"


def test_de_centavos_valor_redondo_mantem_as_duas_casas():
    """ "1.0" nao serve: o contrato e duas casas SEMPRE, para a saida ser uniforme."""
    assert de_centavos(100) == "1.00"


def test_de_centavos_negativo_nao_inverte_o_resto():
    """O que engana: em Python, `-5 // 100` e -1 e `-5 % 100` e 95.

    A forma ingenua com inteiro devolveria "-1.95" para cinco centavos negativos.
    O sinal tem de ser separado antes, com a conta feita sobre o valor absoluto.

    Nao ha valor negativo no banco hoje (`vNF` nao e negativo), mas uma funcao de
    formatacao que erra em silencio e divida esperando para vencer.
    """
    assert de_centavos(-5) == "-0.05"
    assert de_centavos(-12345) == "-123.45"

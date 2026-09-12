"""Testes de `para_centavos` — tarefa 1 da story 002-extrair-nfe-55.

Escritos ANTES da implementacao (passo 2 do loop) e congelados por commit. O
modelo local recebe este arquivo como LEITURA (`--read`), nunca como arquivo
editavel: se ele puder editar o teste, ele edita o teste para faze-lo passar,
que e o caminho mais curto para o objetivo dado.

⭐ POR QUE ESTE ARQUIVO E SEPARADO DO `test_extrator.py`

O `plan.md` fatia a story 002 em DUAS invocacoes do Aider: primeiro
`para_centavos`, depois `extrair_nota`. Se os dois grupos de teste morassem no
mesmo modulo, o `import` no topo pediria as duas funcoes -- e depois da tarefa 1
o modulo inteiro falharia na COLETA, porque `extrair_nota` ainda nao existiria.
O modelo nao teria como ficar verde na tarefa 1, por mais certo que estivesse.

Filtrar com `pytest -k` nao resolve: a coleta quebra antes do filtro rodar.

A regra que fica: **story fatiada em N tarefas = testes em N modulos**, cada um
importando so o que a sua tarefa cria.

Criterios em `specs/002-extrair-nfe-55/spec.md` §5, tabela `para_centavos`.
"""

import pytest

from nfe_parser.extrator import para_centavos


def test_para_centavos_17_converte_exato():
    assert para_centavos("8.04") == 804


def test_para_centavos_18_nao_usa_float():
    """int(float("0.29") * 100) devolve 28. O certo e 29.

    Este teste existe para reprovar a implementacao mais obvia. Nao remova.
    """
    assert para_centavos("0.29") == 29
    assert para_centavos("1.13") == 113
    assert para_centavos("2.01") == 201


def test_para_centavos_19_inteiro_sem_casas_decimais():
    assert para_centavos("10") == 1000


def test_para_centavos_20_zero():
    assert para_centavos("0.00") == 0


def test_para_centavos_21_mais_de_duas_casas_rejeita_em_vez_de_truncar():
    """A Fase 0 passou com int(Decimal("1.005") * 100), que devolve 100.

    Truncar dinheiro em silencio e pior que estourar: o numero errado segue
    para o banco e ninguem percebe. Aqui tem que levantar.
    """
    with pytest.raises(ValueError):
        para_centavos("1.005")


def test_para_centavos_22_texto_nao_numerico_rejeita():
    with pytest.raises(ValueError):
        para_centavos("abc")


def test_para_centavos_23_string_vazia_rejeita():
    with pytest.raises(ValueError):
        para_centavos("")

"""Formatacao de numeros PARA A TELA. O JSON da API nunca passa por aqui.

⛔ Nada de float: a string decimal do XML e exata, e a formatacao e so texto.
"""

import pytest

from nfe_parser.web.comum import decimal_br, reais


@pytest.mark.parametrize(
    ("centavos", "esperado"),
    [(0, "R$ 0,00"), (5, "R$ 0,05"), (123456, "R$ 1.234,56"), (-123456789, "-R$ 1.234.567,89")],
)
def test_reais(centavos, esperado):
    assert reais(centavos) == esperado


@pytest.mark.parametrize(
    ("texto", "minimo", "esperado"),
    [
        ("3.3300000000", 2, "3,33"),
        ("0.9500000000", 2, "0,95"),
        ("12.3456789012", 2, "12,3456789012"),
        ("5.0000000000", 2, "5,00"),
        ("1.5000", 0, "1,5"),
        ("3.0000", 0, "3"),
        ("7", 0, "7"),
        (None, 2, ""),
        ("", 0, ""),
    ],
)
def test_decimal_br_tira_zeros_a_direita_e_usa_virgula(texto, minimo, esperado):
    assert decimal_br(texto, minimo) == esperado

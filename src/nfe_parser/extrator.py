from decimal import Decimal, InvalidOperation

def para_centavos(texto):
    "Converte uma string de valor monetario vinda do XML da NF-e no inteiro de centavos"

    try:
        valor = Decimal(texto)
    except InvalidOperation:
        raise ValueError("Texto não é um número decimal válido")

    if valor < 0:
        raise ValueError("Valor não pode ser negativo")

    partes = str(valor).split('.')
    if len(partes) > 1 and len(partes[1]) > 2:
        raise ValueError("Valor tem mais de duas casas decimais")

    if len(partes) == 1:
        return int(valor) * 100
    else:
        return int(valor * 100)

"""O que a API e as paginas compartilham: conexao por requisicao, upload, dinheiro."""

import re
import tempfile
from pathlib import Path

from fastapi import Request

from nfe_parser import operacoes
from nfe_parser.banco import conectar
from nfe_parser.serializacao import de_centavos

EXTENSOES_ACEITAS = (".zip", ".xml")


class UploadRecusado(Exception):
    """O arquivo enviado nao e `.zip` nem `.xml`. Nada foi gravado."""


def obter_conexao(request: Request):
    """Uma conexao por requisicao, fechada no fim — dependencia do FastAPI.

    ⭐ Com `yield`, o FastAPI roda o `finally` DEPOIS de a resposta sair, entao a
    conexao fecha mesmo quando o endpoint levanta.
    """
    conexao = conectar(request.app.state.caminho_banco)
    try:
        yield conexao
    finally:
        conexao.close()


def importar_upload(conexao, upload):
    """Grava o upload num arquivo temporario e roda o pipeline. Devolve o id do lote.

    ⚠️ O `importar` recebe um CAMINHO e decide zip × xml pela extensao, entao o
    temporario precisa ter a mesma extensao do original. O nome original vira a
    `origem` do lote — e e so o nome, sem pasta: o navegador nao deve ditar caminho.
    """
    nome = Path(upload.filename or "").name
    extensao = Path(nome).suffix.lower()
    if extensao not in EXTENSOES_ACEITAS:
        raise UploadRecusado(
            f"so .zip ou .xml sao aceitos; recebi {nome or 'um arquivo sem nome'!r}"
        )

    with tempfile.TemporaryDirectory() as pasta:
        caminho = Path(pasta) / f"upload{extensao}"
        caminho.write_bytes(upload.file.read())
        return operacoes.importar_e_classificar(conexao, caminho, origem=nome)


def reais(centavos):
    """`123456` → `R$ 1.234,56`. So para EXIBIR; conta se faz com os centavos."""
    texto = de_centavos(centavos)
    sinal = "-" if texto.startswith("-") else ""
    inteiro, decimal = texto.lstrip("-").split(".")
    milhares = f"{int(inteiro):,}".replace(",", ".")
    return f"{sinal}R$ {milhares},{decimal}"


def centavos_de_reais(texto):
    """`"1.234,56"` (ou `"1234.56"`, `"R$ 80"`) → `123456`. Para o valor DIGITADO na tela.

    ⭐ Com virgula, o formato e o brasileiro: ponto e milhar, virgula e decimal.
    Sem virgula, o ponto e decimal. Depois disso so sobra `digitos[.d[d]]`, e o
    resto e recusado — inclusive `1,234`: tres casas nao sao centavo, e adivinhar
    se era milhar seria pior que pedir de novo.

    ⛔ So texto e inteiro, nunca float: `float("0.29") * 100` da `28.999...`.
    """
    limpo = (texto or "").replace("R$", "").strip()
    if "," in limpo:
        limpo = limpo.replace(".", "").replace(",", ".", 1)
    if not re.fullmatch(r"\d+(\.\d{1,2})?", limpo):
        raise ValueError(f"valor invalido: {texto!r}; use, por exemplo, 1.234,56")
    reais_, _, centavos = limpo.partition(".")
    return int(reais_) * 100 + int(centavos.ljust(2, "0"))


def decimal_br(texto, minimo=0):
    """`"3.3300000000"` → `"3,33"`: tira zeros a direita, guarda `minimo` casas, usa virgula.

    ⛔ So operacao de texto, nunca `float(texto)`: a string do XML e exata (vUnCom
    com 10 casas), e passar por float binario poderia trocar o ultimo digito.
    """
    if not texto:
        return ""
    inteiro, _, fracao = texto.partition(".")
    fracao = fracao.rstrip("0").ljust(minimo, "0")
    return f"{inteiro},{fracao}" if fracao else inteiro

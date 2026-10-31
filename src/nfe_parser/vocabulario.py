"""Os vocabularios fechados do projeto, um `StrEnum` por coluna ou contrato.

Antes, cada valor era uma string solta (`"cancelada"`, `"ncm"`) repetida em varios
modulos; um erro de digitacao so aparecia no CHECK do banco, na hora de gravar.
Com o enum, o nome errado falha no import.

⭐ `StrEnum`, e nao `Enum`: cada membro E uma `str`. `StatusNota.OK == "ok"`,
`str(StatusNota.OK) == "ok"`, o `sqlite3` grava `"ok"`, o `json` escreve `"ok"` e o
template compara com `"ok"`. Nada fora do Python muda. `test_vocabulario.py` confere
que cada enum tem exatamente os valores do CHECK correspondente em `banco.py` e
`migracoes.py`: valor novo entra nos dois lugares, ou o teste quebra.

⚠️ O que vem do banco continua `str` pura; o enum e para o que o Python ESCREVE e
COMPARA. Comparar `linha["status"] == StatusNota.CANCELADA` funciona porque o
membro e uma `str`.
"""

from enum import StrEnum


class StatusNota(StrEnum):
    """`notas.status`. Cancelada nunca conta como gasto."""

    OK = "ok"
    CANCELADA = "cancelada"


class TipoXml(StrEnum):
    """O que `tipo_do_xml` devolve: o roteamento do ARQUIVO antes de qualquer parser."""

    NFE = "nfe"
    EVENTO = "evento"
    INVALIDA = "invalida"
    NAO_SUPORTADO_SAT = "nao_suportado_sat"


class ResultadoArquivo(StrEnum):
    """`importacao_arquivos.resultado`: o desfecho de cada arquivo no log do lote."""

    NOVA = "nova"
    DUPLICADA = "duplicada"
    INVALIDA = "invalida"
    CANCELAMENTO_APLICADO = "cancelamento_aplicado"
    CANCELAMENTO_ORFAO = "cancelamento_orfao"
    NAO_SUPORTADO_SAT = "nao_suportado_sat"
    EVENTO_REGISTRADO = "evento_registrado"


class OrigemClassificacao(StrEnum):
    """`produtos.origem`: quem decidiu a categoria. `None` (bucket) nao e membro de
    proposito — a coluna aceita NULL, e "bucket" como string o CHECK recusaria."""

    MANUAL = "manual"
    MEMORIA = "memoria"
    NCM = "ncm"
    LLM = "llm"


class IdentidadeProduto(StrEnum):
    """`produtos.identidade_origem`: `texto` e o casamento aproximado, so dentro da loja."""

    GTIN = "gtin"
    TEXTO = "texto"

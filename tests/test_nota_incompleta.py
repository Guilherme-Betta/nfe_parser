"""NF-e que abre mas esta incompleta e `'invalida'` — achado 2 da revisao de 2026-10-14.

Escrito ANTES da correcao e congelado por commit: quem corrigir nao edita este
arquivo.

🔴 O contrato e o C4 da `specs/004-lote-zip-dedup/spec.md`: `importar` nunca
levanta por causa do CONTEUDO de um arquivo, e `ValueError` vindo de
`extrair_nota` vira linha `'invalida'` (C4.4). O buraco: `extrair_nota` so
traduz para `ValueError` o XML que nao ABRE. Um XML bem formado sem um bloco
obrigatorio passa pelo parser — o `xsdata` nao confere obrigatoriedade —, o
bloco vira `None`, e ler um campo de `None` levanta outra coisa. Ninguem
captura essa outra coisa, e o lote inteiro cai.

⭐ As quatro remocoes cobrem as TRES familias de erro que aparecem hoje, medidas
uma a uma: `AttributeError` (bloco ausente: `pag`, `prod`), `IndexError` (lista
vazia: `detPag`) e `TypeError` (valor ausente numa conversao: `vNF`). Uma
correcao que capture so a primeira passa em dois casos e reprova nos outros.

⚠️ Todas mantem o `<mod>55</mod>`, entao `tipo_do_xml` continua dizendo
"nfe" e o arquivo chega de fato a `extrair_nota`. Remover o `<ide>` inteiro nao
serviria: a nota seria barrada antes, pelo roteamento.

⛔ Tolerar o bloco ausente — gravar `forma_pagamento` NULL, por exemplo — NAO
passa aqui. Os quatro sao obrigatorios no leiaute 4.00: nota sem eles e nota
invalida, e o log tem de dizer isso.
"""

import re
import zipfile
from pathlib import Path

import pytest

from nfe_parser.extrator import extrair_nota
from nfe_parser.importador import importar

FIXTURES = Path(__file__).parent / "fixtures"

REMOCOES = {
    "sem_pag": r"<pag>.*?</pag>",
    "sem_detPag": r"<detPag>.*?</detPag>",
    "sem_vNF": r"<vNF>.*?</vNF>",
    "sem_prod": r"<prod>.*?</prod>",
}


def _zip(tmp_path, nome, membros):
    """Monta um `.zip` em `tmp_path`. A ordem de `membros` vira a ordem interna."""
    caminho = tmp_path / nome
    with zipfile.ZipFile(caminho, "w") as arquivo_zip:
        for interno, conteudo in membros.items():
            arquivo_zip.writestr(interno, conteudo)
    return caminho


def _fixture(nome):
    return (FIXTURES / nome).read_text(encoding="utf-8")


def _incompleta(padrao):
    """A nota de 1 item sem o bloco que `padrao` casa."""
    xml, removidos = re.subn(padrao, "", _fixture("nfe_55_1item.xml"), flags=re.DOTALL)
    assert removidos == 1, "a fixture mudou; a remocao tem de achar o bloco exatamente uma vez"
    return xml


@pytest.mark.parametrize("padrao", list(REMOCOES.values()), ids=list(REMOCOES))
def test_extrair_nota_incompleta_levanta_value_error(padrao):
    with pytest.raises(ValueError):
        extrair_nota(_incompleta(padrao))


@pytest.mark.parametrize("padrao", list(REMOCOES.values()), ids=list(REMOCOES))
def test_nota_incompleta_vira_linha_invalida_e_o_lote_segue(conexao, tmp_path, padrao):
    """⭐ A incompleta vem PRIMEIRO no `.zip`: a nota boa depois dela prova que o
    lote seguiu, e nao so que terminou antes de chegar ao arquivo ruim.
    """
    lote = _zip(
        tmp_path,
        "lote.zip",
        {"a_incompleta.xml": _incompleta(padrao), "b_boa.xml": _fixture("nfe_65_1item.xml")},
    )

    importar(conexao, lote)

    log = dict(conexao.execute("SELECT arquivo, resultado FROM importacao_arquivos"))
    assert log == {"a_incompleta.xml": "invalida", "b_boa.xml": "nova"}

    detalhe = conexao.execute(
        "SELECT detalhe FROM importacao_arquivos WHERE arquivo = 'a_incompleta.xml'"
    ).fetchone()[0]
    assert detalhe  # C4.6: a mensagem do erro, nunca vazia

    assert conexao.execute("SELECT COUNT(*) FROM notas").fetchone()[0] == 1

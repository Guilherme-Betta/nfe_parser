"""Testes do contador `cancelamentos_aplicados` — tarefa 4 da story 005.

Escritos ANTES da implementacao (passo 2 do loop) e congelados por commit. O
modelo local recebe este arquivo como LEITURA (`--read`), nunca como editavel.

⭐ POR QUE ISTO E UMA TAREFA SEPARADA DA 3: "varrer duas vezes" e "somar o
contador" sao dois defeitos (regra 2 do fatiamento). O segundo e uma troca de
linha de SQL; pedido junto com o refactor das passadas, ele vira uma edicao no
meio de um diff grande que ninguem consegue revisar.

A coluna nao e invencao desta story: o DDL da story 001 ja a criou, e a story
004 a preenchia com um `0` fixo — corretamente, porque la nenhum evento podia
ser aplicado.

Criterios em `specs/005-cancelamento-duas-passadas/spec.md` §3, bloco C4.
"""

import zipfile
from pathlib import Path

import pytest

from nfe_parser.banco import abrir_banco
from nfe_parser.importador import importar

FIXTURES = Path(__file__).parent / "fixtures"

NS = "http://www.portalfiscal.inf.br/nfe"

CHAVE_1ITEM = "35260499999999000199550010000000011000000017"
CHAVE_65 = "35260499999999000199650010000000021000000025"
CHAVE_AUSENTE = "35260499999999000199550019999999991000000099"

CONTADORES = (
    "total_arquivos",
    "notas_novas",
    "duplicadas",
    "invalidas",
    "cancelamentos_aplicados",
    "nao_suportadas",
)


def _evento(chave):
    return (
        f'<procEventoNFe xmlns="{NS}" versao="1.00"><evento versao="1.00"><infEvento>'
        f"<chNFe>{chave}</chNFe><dhEvento>2026-04-10T10:00:00-03:00</dhEvento>"
        "<tpEvento>110111</tpEvento></infEvento></evento></procEventoNFe>"
    )


@pytest.fixture
def conexao(tmp_path):
    con = abrir_banco(tmp_path / "nfe.db")
    yield con
    con.close()


def _texto(nome):
    return (FIXTURES / nome).read_text(encoding="utf-8")


def _zip(tmp_path, nome, membros):
    caminho = tmp_path / nome
    with zipfile.ZipFile(caminho, "w") as arquivo_zip:
        for interno, conteudo in membros.items():
            arquivo_zip.writestr(interno, conteudo)
    return caminho


def _contadores(con, importacao_id):
    """Os seis contadores como dict, para a falha dizer QUAL deles errou."""
    linha = con.execute(
        f"SELECT {', '.join(CONTADORES)} FROM importacoes WHERE id = ?", (importacao_id,)
    ).fetchone()
    return dict(zip(CONTADORES, linha))


# --- C4.1 -------------------------------------------------------------------
def test_um_cancelamento_aplicado_conta_um(conexao, tmp_path):
    caminho = _zip(
        tmp_path,
        "lote.zip",
        {"nota.xml": _texto("nfe_55_1item.xml"), "evento.xml": _evento(CHAVE_1ITEM)},
    )

    importacao_id = importar(conexao, caminho)

    assert _contadores(conexao, importacao_id)["cancelamentos_aplicados"] == 1


def test_dois_cancelamentos_contam_dois(conexao, tmp_path):
    caminho = _zip(
        tmp_path,
        "lote.zip",
        {
            "1_nota.xml": _texto("nfe_55_1item.xml"),
            "2_outra.xml": _texto("nfe_65_1item.xml"),
            "3_evento.xml": _evento(CHAVE_1ITEM),
            "4_evento.xml": _evento(CHAVE_65),
        },
    )

    importacao_id = importar(conexao, caminho)

    assert _contadores(conexao, importacao_id)["cancelamentos_aplicados"] == 2


# --- C4.2 -------------------------------------------------------------------
def test_orfao_nao_entra_no_contador(conexao, tmp_path):
    """🔒 O criterio 5 aprovado pelo Gui, literal: conta os aplicados, nao os
    orfaos. Um `COUNT` que pegue os dois resultados passa nos testes acima e
    reprova aqui."""
    caminho = _zip(
        tmp_path,
        "lote.zip",
        {
            "1_nota.xml": _texto("nfe_55_1item.xml"),
            "2_evento.xml": _evento(CHAVE_1ITEM),
            "3_orfao.xml": _evento(CHAVE_AUSENTE),
        },
    )

    importacao_id = importar(conexao, caminho)

    assert _contadores(conexao, importacao_id)["cancelamentos_aplicados"] == 1


# --- C4.3 -------------------------------------------------------------------
def test_o_lote_inteiro_fecha_com_os_seis_contadores_certos(conexao, tmp_path):
    """O evento entra no `total_arquivos` como qualquer outro arquivo."""
    caminho = _zip(
        tmp_path,
        "lote.zip",
        {
            "1_nota.xml": _texto("nfe_55_1item.xml"),
            "2_evento.xml": _evento(CHAVE_1ITEM),
            "3_orfao.xml": _evento(CHAVE_AUSENTE),
            "4_sat.xml": f'<CFe xmlns="{NS}"><infCFe><ide><mod>59</mod></ide></infCFe></CFe>',
            "5_quebrada.xml": "<nfeProc><quebrado",
        },
    )

    importacao_id = importar(conexao, caminho)

    assert _contadores(conexao, importacao_id) == {
        "total_arquivos": 5,
        "notas_novas": 1,
        "duplicadas": 0,
        "invalidas": 1,
        "cancelamentos_aplicados": 1,
        "nao_suportadas": 1,
    }


# --- C4.4 -------------------------------------------------------------------
def test_os_contadores_nao_acumulam_entre_lotes(conexao, tmp_path):
    """O evento do segundo lote aplica numa nota do primeiro (C3.3) — entao o
    primeiro fecha com zero e o segundo com um, sem um somar no outro."""
    primeiro = _zip(tmp_path, "abril.zip", {"nota.xml": _texto("nfe_55_1item.xml")})
    segundo = _zip(tmp_path, "maio.zip", {"evento.xml": _evento(CHAVE_1ITEM)})

    um = importar(conexao, primeiro)
    dois = importar(conexao, segundo)

    assert _contadores(conexao, um)["cancelamentos_aplicados"] == 0
    assert _contadores(conexao, dois)["cancelamentos_aplicados"] == 1

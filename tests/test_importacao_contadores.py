"""Testes dos contadores de `importacoes` — tarefa 6 da story 004-lote-zip-dedup.

Escritos ANTES da implementacao (passo 2 do loop) e congelados por commit. O
modelo local recebe este arquivo como LEITURA (`--read`), nunca como editavel.

⭐ POR QUE ISTO E UMA TAREFA SEPARADA DA 4: "ler o lote sem derrubar" e "fechar
a linha da importacao com os numeros certos" sao dois defeitos. A tarefa 4 ja e
a maior das seis; somar os contadores nela seria pedir dois de uma vez, que e a
regra 2 do fatiamento — a mesma que ja corrompeu arquivo neste projeto.

As colunas nao sao invencao desta story: o DDL da story 001 ja as criou. Sem
preencher, elas ficam nos zeros do `DEFAULT` para sempre.

Criterios em `specs/004-lote-zip-dedup/spec.md` §3, bloco C6.
"""

import zipfile
from pathlib import Path

import pytest

from nfe_parser.banco import abrir_banco
from nfe_parser.importador import importar

FIXTURES = Path(__file__).parent / "fixtures"

NS = "http://www.portalfiscal.inf.br/nfe"

XML_QUEBRADO = "<nfeProc><quebrado"
CFE_MINIMO = f'<CFe xmlns="{NS}"><infCFe><ide><mod>59</mod></ide></infCFe></CFe>'
EVENTO_MINIMO = (
    f'<procEventoNFe xmlns="{NS}"><evento><infEvento>'
    "<tpEvento>110111</tpEvento></infEvento></evento></procEventoNFe>"
)

CONTADORES = (
    "total_arquivos",
    "notas_novas",
    "duplicadas",
    "invalidas",
    "cancelamentos_aplicados",
    "nao_suportadas",
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


# --- C6.1 -------------------------------------------------------------------
def test_total_arquivos_bate_com_as_linhas_do_log(conexao, tmp_path):
    caminho = _zip(
        tmp_path,
        "lote.zip",
        {
            "1_nfe.xml": _texto("nfe_55_1item.xml"),
            "2_sat.xml": CFE_MINIMO,
            "3_quebrada.xml": XML_QUEBRADO,
        },
    )

    importacao_id = importar(conexao, caminho)

    linhas_do_log = conexao.execute(
        "SELECT COUNT(*) FROM importacao_arquivos WHERE importacao_id = ?", (importacao_id,)
    ).fetchone()[0]

    assert linhas_do_log == 3
    assert _contadores(conexao, importacao_id)["total_arquivos"] == 3


def test_o_que_nao_e_xml_nao_entra_no_total(conexao, tmp_path):
    """C4.7 diz que membros nao-XML nao viram linha; o total tem de concordar."""
    caminho = _zip(
        tmp_path,
        "lote.zip",
        {"boa.xml": _texto("nfe_55_1item.xml"), "leiame.txt": "nao e nota"},
    )

    importacao_id = importar(conexao, caminho)

    assert _contadores(conexao, importacao_id)["total_arquivos"] == 1


# --- C6.2 -------------------------------------------------------------------
def test_cada_desfecho_cai_no_seu_contador(conexao, tmp_path):
    """Um lote com os quatro desfechos, contados de uma vez.

    ⚠️ O `cancelamento_orfao` do evento entra no `total_arquivos` e em NENHUM
    contador especifico — nao existe coluna para ele no DDL da story 001, e
    `cancelamentos_aplicados` conta o que foi APLICADO, que nesta story e nada
    (C6.3). Somar o evento ali seria inventar um numero.
    """
    caminho = _zip(
        tmp_path,
        "lote.zip",
        {
            "1_nfe.xml": _texto("nfe_55_1item.xml"),
            "2_outra.xml": _texto("nfe_65_1item.xml"),
            "3_sat.xml": CFE_MINIMO,
            "4_evento.xml": EVENTO_MINIMO,
            "5_quebrada.xml": XML_QUEBRADO,
        },
    )

    importacao_id = importar(conexao, caminho)

    assert _contadores(conexao, importacao_id) == {
        "total_arquivos": 5,
        "notas_novas": 2,
        "duplicadas": 0,
        "invalidas": 1,
        "cancelamentos_aplicados": 0,
        "nao_suportadas": 1,
    }


def test_a_segunda_importacao_conta_duplicada_e_nao_nova(conexao, tmp_path):
    caminho = _zip(tmp_path, "lote.zip", {"boa.xml": _texto("nfe_55_1item.xml")})

    primeira = importar(conexao, caminho)
    segunda = importar(conexao, caminho)

    assert _contadores(conexao, primeira)["notas_novas"] == 1
    assert _contadores(conexao, primeira)["duplicadas"] == 0

    assert _contadores(conexao, segunda)["notas_novas"] == 0
    assert _contadores(conexao, segunda)["duplicadas"] == 1


def test_os_contadores_sao_por_importacao_e_nao_acumulam(conexao, tmp_path):
    """Duas importacoes diferentes nao podem somar uma na linha da outra."""
    um = _zip(tmp_path, "a.zip", {"boa.xml": _texto("nfe_55_1item.xml")})
    outro = _zip(tmp_path, "b.zip", {"outra.xml": _texto("nfe_65_1item.xml")})

    primeira = importar(conexao, um)
    segunda = importar(conexao, outro)

    assert _contadores(conexao, primeira)["total_arquivos"] == 1
    assert _contadores(conexao, segunda)["total_arquivos"] == 1


def test_um_lote_vazio_fecha_com_todos_os_contadores_em_zero(conexao, tmp_path):
    caminho = _zip(tmp_path, "lote.zip", {"leiame.txt": "nada aqui"})

    importacao_id = importar(conexao, caminho)

    assert _contadores(conexao, importacao_id) == dict.fromkeys(CONTADORES, 0)


# --- C6.3 -------------------------------------------------------------------
def test_cancelamentos_aplicados_fica_zero_nesta_story(conexao, tmp_path):
    """A 004 classifica evento; APLICAR o cancelamento e a story 005.

    Um contador diferente de zero aqui significaria que a implementacao passou
    do escopo — e passar do escopo no meio da medicao contamina a medicao.
    """
    caminho = _zip(
        tmp_path,
        "lote.zip",
        {"nfe.xml": _texto("nfe_55_1item.xml"), "evento.xml": EVENTO_MINIMO},
    )

    importacao_id = importar(conexao, caminho)

    assert _contadores(conexao, importacao_id)["cancelamentos_aplicados"] == 0

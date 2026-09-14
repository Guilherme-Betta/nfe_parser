"""Testes das duas passadas — tarefa 3 da story 005-cancelamento-duas-passadas.

Escritos ANTES da implementacao (passo 2 do loop) e congelados por commit. O
modelo local recebe este arquivo como LEITURA (`--read`), nunca como editavel.

⭐ AQUI MORA A INVARIANTE-TITULO da story: "cancelamento aplicado inclusive com
evento antes da nota". Ela e o §5 da `specs/01_spec_parser_modelo.md` e e a
ultima invariante daquele paragrafo que nenhuma story fechou.

🔴 OS `.zip` NASCEM EM `tmp_path` E NUNCA SAO COMMITADOS. O `nfe_parser` e
repositorio publico e a checagem de privacidade da transferencia procura
exatamente por `.zip` entrando no repo. Se um aparecer no diff desta story,
algo saiu errado aqui — nao e falso positivo.

Criterios em `specs/005-cancelamento-duas-passadas/spec.md` §3, bloco C3.
"""

import zipfile
from pathlib import Path

import pytest

from nfe_parser.banco import abrir_banco
from nfe_parser.importador import importar

FIXTURES = Path(__file__).parent / "fixtures"

NS = "http://www.portalfiscal.inf.br/nfe"

CHAVE_1ITEM = "35260499999999000199550010000000011000000017"
CHAVE_AUSENTE = "35260499999999000199550019999999991000000099"

# ⚠️ Sem namespace de proposito: o `classificar_xml` aceita a tag crua e devolve
# "evento", mas o parser do `nfelib` recusa. E o C3.5.
EVENTO_QUE_NAO_ABRE = (
    f"<procEventoNFe><evento><infEvento><chNFe>{CHAVE_1ITEM}</chNFe>"
    "<tpEvento>110111</tpEvento></infEvento></evento></procEventoNFe>"
)


def _evento(chave=CHAVE_1ITEM):
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
    """Monta um `.zip` em `tmp_path`. A ordem de `membros` vira a ordem interna."""
    caminho = tmp_path / nome
    with zipfile.ZipFile(caminho, "w") as arquivo_zip:
        for interno, conteudo in membros.items():
            arquivo_zip.writestr(interno, conteudo)
    return caminho


def _log(con, importacao_id):
    return con.execute(
        "SELECT arquivo, resultado FROM importacao_arquivos"
        " WHERE importacao_id = ? ORDER BY arquivo",
        (importacao_id,),
    ).fetchall()


def _nota(con, chave=CHAVE_1ITEM):
    return con.execute(
        "SELECT status, cancelado_em FROM notas WHERE chave = ?", (chave,)
    ).fetchone()


# --- C3.1, C3.2 -------------------------------------------------------------
def test_evento_antes_da_nota_aplica_o_cancelamento(conexao, tmp_path):
    """🔒 A invariante-titulo. Numa passada so, este teste e impossivel: quando
    o evento e lido, a nota ainda nao esta no banco."""
    caminho = _zip(
        tmp_path,
        "lote.zip",
        {"1_evento.xml": _evento(), "2_nota.xml": _texto("nfe_55_1item.xml")},
    )

    importacao_id = importar(conexao, caminho)

    status, cancelado_em = _nota(conexao)
    assert status == "cancelada"
    assert cancelado_em
    assert _log(conexao, importacao_id) == [
        ("1_evento.xml", "cancelamento_aplicado"),
        ("2_nota.xml", "nova"),
    ]


def test_as_duas_ordens_produzem_o_mesmo_estado_final(tmp_path):
    """⭐ A invariante escrita como comparacao, e nao como caso particular.

    Dois bancos independentes, dois `.zip` com os mesmos dois arquivos em ordem
    trocada. O que se compara e o estado final — nao o caminho.
    """
    membros = {"evento.xml": _evento(), "nota.xml": _texto("nfe_55_1item.xml")}

    estados = []
    for rotulo, ordem in (("a", ["evento.xml", "nota.xml"]), ("b", ["nota.xml", "evento.xml"])):
        con = abrir_banco(tmp_path / f"nfe_{rotulo}.db")
        caminho = _zip(tmp_path, f"lote_{rotulo}.zip", {n: membros[n] for n in ordem})

        importacao_id = importar(con, caminho)

        status, cancelado_em = _nota(con)
        estados.append((status, cancelado_em is not None, sorted(_log(con, importacao_id))))
        con.close()

    assert estados[0] == estados[1]
    assert estados[0][0] == "cancelada"


# --- C3.3 -------------------------------------------------------------------
def test_evento_aplica_em_nota_de_importacao_anterior(conexao, tmp_path):
    """A nota chegou num lote de abril; o evento chega no lote de maio."""
    primeiro = _zip(tmp_path, "abril.zip", {"nota.xml": _texto("nfe_55_1item.xml")})
    segundo = _zip(tmp_path, "maio.zip", {"evento.xml": _evento()})

    importar(conexao, primeiro)
    importacao_id = importar(conexao, segundo)

    assert _nota(conexao)[0] == "cancelada"
    assert _log(conexao, importacao_id) == [("evento.xml", "cancelamento_aplicado")]


# --- C3.4 -------------------------------------------------------------------
def test_evento_orfao_registra_e_nao_cria_nota_fantasma(conexao, tmp_path):
    caminho = _zip(
        tmp_path,
        "lote.zip",
        {"nota.xml": _texto("nfe_55_1item.xml"), "orfao.xml": _evento(chave=CHAVE_AUSENTE)},
    )

    importacao_id = importar(conexao, caminho)

    assert conexao.execute("SELECT COUNT(*) FROM notas").fetchone()[0] == 1
    assert _log(conexao, importacao_id) == [
        ("nota.xml", "nova"),
        ("orfao.xml", "cancelamento_orfao"),
    ]


# --- C3.5 -------------------------------------------------------------------
def test_evento_que_nao_abre_vira_invalida_e_o_lote_segue(conexao, tmp_path):
    """Um `ParserError` escapando daqui derruba o lote inteiro — inclusive a
    nota boa, que nao tem culpa nenhuma."""
    caminho = _zip(
        tmp_path,
        "lote.zip",
        {"1_ruim.xml": EVENTO_QUE_NAO_ABRE, "2_boa.xml": _texto("nfe_55_1item.xml")},
    )

    importacao_id = importar(conexao, caminho)

    assert _log(conexao, importacao_id) == [("1_ruim.xml", "invalida"), ("2_boa.xml", "nova")]
    assert conexao.execute("SELECT COUNT(*) FROM notas").fetchone()[0] == 1
    detalhe = conexao.execute(
        "SELECT detalhe FROM importacao_arquivos WHERE arquivo = '1_ruim.xml'"
    ).fetchone()[0]
    assert detalhe  # texto nao vazio explicando o que houve


# --- C3.6 -------------------------------------------------------------------
def test_a_chave_do_evento_entra_na_coluna_chave_do_log(conexao, tmp_path):
    caminho = _zip(tmp_path, "lote.zip", {"evento.xml": _evento(chave=CHAVE_AUSENTE)})

    importacao_id = importar(conexao, caminho)

    assert (
        conexao.execute(
            "SELECT chave FROM importacao_arquivos WHERE importacao_id = ?", (importacao_id,)
        ).fetchone()[0]
        == CHAVE_AUSENTE
    )


# --- C3.7 -------------------------------------------------------------------
def test_reimportar_o_mesmo_lote_nao_duplica_nem_move_o_carimbo(conexao, tmp_path):
    caminho = _zip(
        tmp_path,
        "lote.zip",
        {"evento.xml": _evento(), "nota.xml": _texto("nfe_55_1item.xml")},
    )

    importar(conexao, caminho)
    carimbo = _nota(conexao)[1]
    segunda = importar(conexao, caminho)

    assert conexao.execute("SELECT COUNT(*) FROM notas").fetchone()[0] == 1
    assert _nota(conexao) == ("cancelada", carimbo)
    assert _log(conexao, segunda) == [
        ("evento.xml", "cancelamento_aplicado"),
        ("nota.xml", "duplicada"),
    ]


# --- acrescentado no passo 4, pela cobertura ---------------------------------
def test_evento_chega_tambem_como_xml_avulso(conexao, tmp_path):
    """Escrito na REVISAO, nao no passo 2: a cobertura acusou o ramo do `.xml`
    avulso que classifica um evento (`importador.py`, a linha do
    `eventos.append` fora do `.zip`) como a unica linha nova sem teste.

    Nao e linha morta — e o C5 da story 004, que exige que o `.zip` e o avulso
    desemboquem no mesmo caminho de codigo. Sem este teste, "os dois caminhos
    convergem" valia para nota e nao valia para evento, e ninguem saberia.
    """
    nota = tmp_path / "nota.xml"
    nota.write_text(_texto("nfe_55_1item.xml"), encoding="utf-8")
    evento = tmp_path / "evento.xml"
    evento.write_text(_evento(), encoding="utf-8")

    importar(conexao, nota)
    importacao_id = importar(conexao, evento)

    assert _nota(conexao)[0] == "cancelada"
    assert _log(conexao, importacao_id) == [("evento.xml", "cancelamento_aplicado")]

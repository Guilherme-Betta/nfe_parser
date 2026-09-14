"""Testes de `importar` sobre um `.zip` — tarefa 4 da story 004-lote-zip-dedup.

Escritos ANTES da implementacao (passo 2 do loop) e congelados por commit. O
modelo local recebe este arquivo como LEITURA (`--read`), nunca como editavel.

⭐ ESTE MODULO COBRE SO O C4. O C5 — `.xml` avulso pelo mesmo caminho de codigo
— esta em `test_importar_avulso.py`, porque sao dois defeitos e porque juntos os
dois modulos davam ~3,4k de `--read`, levando o turno 1 a ~6,0k contra o teto
empirico de 6k da regra 5 do `plan.md`. Medido no passo 2, nao estimado.

🔴 O `.zip` DE TESTE E MONTADO EM `tmp_path`, NUNCA COMMITADO. O `nfe_parser` e
repositorio publico e a checagem de privacidade da transferencia procura
exatamente por `.zip` entrando no repo. Se um `.zip` aparecer no diff desta
story, algo saiu errado aqui — nao e falso positivo.

Criterios em `specs/004-lote-zip-dedup/spec.md` §3, bloco C4.
"""

import hashlib
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

CHAVE_1ITEM = "35260499999999000199550010000000011000000017"


@pytest.fixture
def conexao(tmp_path):
    con = abrir_banco(tmp_path / "nfe.db")
    yield con
    con.close()


def _texto(nome):
    return (FIXTURES / nome).read_text(encoding="utf-8")


def _zip(tmp_path, nome, membros):
    """Monta um `.zip` em `tmp_path`. `membros` = {nome_dentro_do_zip: texto}."""
    caminho = tmp_path / nome
    with zipfile.ZipFile(caminho, "w") as arquivo_zip:
        for interno, conteudo in membros.items():
            arquivo_zip.writestr(interno, conteudo)
    return caminho


def _sha256(texto):
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _conta(con, tabela):
    return con.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]


def _log(con, importacao_id):
    return con.execute(
        "SELECT arquivo, resultado FROM importacao_arquivos"
        " WHERE importacao_id = ? ORDER BY arquivo",
        (importacao_id,),
    ).fetchall()


# --- C4.1 -------------------------------------------------------------------
def test_um_arquivo_corrompido_nao_derruba_o_lote(conexao, tmp_path):
    """🔒 O criterio central da story: o bom entra mesmo com o ruim do lado.

    Um `importar` que deixe a excecao subir falha aqui de duas formas ao mesmo
    tempo — levanta, e deixa a nota boa de fora.
    """
    caminho = _zip(
        tmp_path,
        "lote.zip",
        {"boa.xml": _texto("nfe_55_1item.xml"), "quebrada.xml": XML_QUEBRADO},
    )

    importacao_id = importar(conexao, caminho)

    assert _conta(conexao, "notas") == 1
    assert _log(conexao, importacao_id) == [("boa.xml", "nova"), ("quebrada.xml", "invalida")]


def test_a_ordem_dos_arquivos_no_zip_nao_muda_o_resultado(conexao, tmp_path):
    """O ruim primeiro. Se a implementacao abortar no primeiro erro, a boa some."""
    caminho = _zip(
        tmp_path,
        "lote.zip",
        {"1_quebrada.xml": XML_QUEBRADO, "2_boa.xml": _texto("nfe_55_1item.xml")},
    )

    importacao_id = importar(conexao, caminho)

    assert _conta(conexao, "notas") == 1
    assert _log(conexao, importacao_id) == [
        ("1_quebrada.xml", "invalida"),
        ("2_boa.xml", "nova"),
    ]


def test_devolve_o_id_da_importacao(conexao, tmp_path):
    caminho = _zip(tmp_path, "lote.zip", {"boa.xml": _texto("nfe_55_1item.xml")})

    importacao_id = importar(conexao, caminho)

    assert isinstance(importacao_id, int)
    assert (
        conexao.execute(
            "SELECT COUNT(*) FROM importacoes WHERE id = ?", (importacao_id,)
        ).fetchone()[0]
        == 1
    )


# --- C4.2 -------------------------------------------------------------------
def test_cria_uma_linha_de_importacao_com_origem_e_os_dois_carimbos(conexao, tmp_path):
    caminho = _zip(tmp_path, "lote.zip", {"boa.xml": _texto("nfe_55_1item.xml")})

    importacao_id = importar(conexao, caminho)

    assert _conta(conexao, "importacoes") == 1
    origem, iniciado_em, finalizado_em = conexao.execute(
        "SELECT origem, iniciado_em, finalizado_em FROM importacoes WHERE id = ?",
        (importacao_id,),
    ).fetchone()

    assert origem
    assert "lote.zip" in origem
    assert iniciado_em is not None
    assert finalizado_em is not None  # ⭐ so preenche no FIM: prova que o lote fechou


def test_a_origem_explicita_vence_o_caminho(conexao, tmp_path):
    caminho = _zip(tmp_path, "lote.zip", {"boa.xml": _texto("nfe_55_1item.xml")})

    importacao_id = importar(conexao, caminho, origem="portal-sefaz-abril")

    assert (
        conexao.execute("SELECT origem FROM importacoes WHERE id = ?", (importacao_id,)).fetchone()[
            0
        ]
        == "portal-sefaz-abril"
    )


# --- C4.3 -------------------------------------------------------------------
def test_cada_arquivo_vira_uma_linha_com_nome_hash_e_chave(conexao, tmp_path):
    texto = _texto("nfe_55_1item.xml")
    caminho = _zip(tmp_path, "lote.zip", {"boa.xml": texto})

    importacao_id = importar(conexao, caminho)

    assert conexao.execute(
        "SELECT arquivo, arquivo_hash, chave FROM importacao_arquivos WHERE importacao_id = ?",
        (importacao_id,),
    ).fetchone() == ("boa.xml", _sha256(texto), CHAVE_1ITEM)


def test_sem_chave_conhecida_a_coluna_chave_sai_null(conexao, tmp_path):
    """Num XML que nao da para abrir nao ha chave para registrar."""
    caminho = _zip(tmp_path, "lote.zip", {"quebrada.xml": XML_QUEBRADO})

    importacao_id = importar(conexao, caminho)

    assert (
        conexao.execute(
            "SELECT chave FROM importacao_arquivos WHERE importacao_id = ?", (importacao_id,)
        ).fetchone()[0]
        is None
    )


# --- C4.4 -------------------------------------------------------------------
def test_o_mapa_de_classificacao_para_resultado(conexao, tmp_path):
    """Os quatro desfechos de `classificar_xml`, num lote so.

    O evento vira `cancelamento_orfao` — decisao (a) da §5 da spec: dos seis
    valores que o CHECK do DDL aceita, e o unico que descreve um evento que nao
    alterou nota nenhuma, que e o que a 004 faz com todo evento. A story 005
    refina isso, e o refinamento e esperado.
    """
    caminho = _zip(
        tmp_path,
        "lote.zip",
        {
            "1_nfe.xml": _texto("nfe_55_1item.xml"),
            "2_sat.xml": CFE_MINIMO,
            "3_evento.xml": EVENTO_MINIMO,
            "4_quebrada.xml": XML_QUEBRADO,
        },
    )

    importacao_id = importar(conexao, caminho)

    assert _log(conexao, importacao_id) == [
        ("1_nfe.xml", "nova"),
        ("2_sat.xml", "nao_suportado_sat"),
        ("3_evento.xml", "cancelamento_orfao"),
        ("4_quebrada.xml", "invalida"),
    ]


def test_o_evento_e_classificado_e_nao_aplicado(conexao, tmp_path):
    """Escopo: a 004 registra o evento no log e nao encosta na tabela `notas`."""
    caminho = _zip(
        tmp_path,
        "lote.zip",
        {"nfe.xml": _texto("nfe_55_1item.xml"), "evento.xml": EVENTO_MINIMO},
    )

    importar(conexao, caminho)

    assert conexao.execute("SELECT status FROM notas").fetchone()[0] == "ok"
    assert conexao.execute("SELECT cancelado_em FROM notas").fetchone()[0] is None


# --- C4.5 -------------------------------------------------------------------
def test_o_mesmo_zip_importado_duas_vezes_nao_duplica_as_notas(conexao, tmp_path):
    caminho = _zip(tmp_path, "lote.zip", {"boa.xml": _texto("nfe_55_1item.xml")})

    primeira = importar(conexao, caminho)
    segunda = importar(conexao, caminho)

    assert _conta(conexao, "notas") == 1
    assert _conta(conexao, "itens") == 1
    assert _log(conexao, primeira) == [("boa.xml", "nova")]
    assert _log(conexao, segunda) == [("boa.xml", "duplicada")]


def test_duas_importacoes_sao_duas_linhas_em_importacoes(conexao, tmp_path):
    caminho = _zip(tmp_path, "lote.zip", {"boa.xml": _texto("nfe_55_1item.xml")})

    primeira = importar(conexao, caminho)
    segunda = importar(conexao, caminho)

    assert primeira != segunda
    assert _conta(conexao, "importacoes") == 2


# --- C4.6 -------------------------------------------------------------------
def test_detalhe_explica_a_falha_e_fica_null_no_sucesso(conexao, tmp_path):
    caminho = _zip(
        tmp_path,
        "lote.zip",
        {"boa.xml": _texto("nfe_55_1item.xml"), "quebrada.xml": XML_QUEBRADO},
    )

    importacao_id = importar(conexao, caminho)

    linhas = dict(
        conexao.execute(
            "SELECT arquivo, detalhe FROM importacao_arquivos WHERE importacao_id = ?",
            (importacao_id,),
        ).fetchall()
    )

    assert linhas["boa.xml"] is None
    assert linhas["quebrada.xml"]  # texto nao vazio explicando o que houve


# --- C4.7 -------------------------------------------------------------------
def test_membros_que_nao_sao_xml_sao_ignorados(conexao, tmp_path):
    """Portais mandam `.pdf` e `README.txt` junto. Isso nao e arquivo do lote."""
    caminho = _zip(
        tmp_path,
        "lote.zip",
        {
            "boa.xml": _texto("nfe_55_1item.xml"),
            "leiame.txt": "isto nao e uma nota",
            "danfe.pdf": "%PDF-1.4 nem isto",
        },
    )

    importacao_id = importar(conexao, caminho)

    assert _log(conexao, importacao_id) == [("boa.xml", "nova")]


def test_a_extensao_xml_e_reconhecida_em_maiuscula(conexao, tmp_path):
    caminho = _zip(tmp_path, "lote.zip", {"BOA.XML": _texto("nfe_55_1item.xml")})

    importacao_id = importar(conexao, caminho)

    assert _log(conexao, importacao_id) == [("BOA.XML", "nova")]


def test_entradas_de_diretorio_nao_viram_linha(conexao, tmp_path):
    caminho = tmp_path / "lote.zip"
    with zipfile.ZipFile(caminho, "w") as arquivo_zip:
        arquivo_zip.writestr("notas/", "")  # entrada de diretorio, sem conteudo
        arquivo_zip.writestr("notas/boa.xml", _texto("nfe_55_1item.xml"))

    importacao_id = importar(conexao, caminho)

    assert _log(conexao, importacao_id) == [("notas/boa.xml", "nova")]


# --- um lote sem nenhum XML nao e erro -------------------------------------
def test_um_zip_sem_nenhum_xml_fecha_a_importacao_sem_erro(conexao, tmp_path):
    caminho = _zip(tmp_path, "lote.zip", {"leiame.txt": "nada aqui"})

    importacao_id = importar(conexao, caminho)

    assert _log(conexao, importacao_id) == []
    assert (
        conexao.execute(
            "SELECT finalizado_em FROM importacoes WHERE id = ?", (importacao_id,)
        ).fetchone()[0]
        is not None
    )

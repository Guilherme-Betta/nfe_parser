"""Pipeline de importacao via HTTP — spec 03 §3, criterios C4 a C9."""

from fastapi.testclient import TestClient

from nfe_parser.web.app import criar_app
from tests.apoio import (
    ACHOCOLATADO,
    CFE_SAT,
    CHAVE_1ITEM,
    TOMATE,
    XML_QUEBRADO,
    LlmEspiao,
    chave,
    enviar,
    evento,
    produto,
    texto,
    variante,
    zip_de,
)


def _conta(conexao, tabela):
    return conexao.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]


def _status(conexao, chave_nota):
    return conexao.execute("SELECT status FROM notas WHERE chave = ?", (chave_nota,)).fetchone()[0]


# C4
def test_lote_misto_nao_quebra_e_cada_arquivo_vai_ao_log(cliente):
    lote = zip_de(
        {"boa.xml": texto("nfe_55_1item.xml"), "quebrada.xml": XML_QUEBRADO, "sat.xml": CFE_SAT}
    )

    resposta = enviar(cliente, "lote.zip", lote)

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["contadores"] == {
        "total_arquivos": 3,
        "notas_novas": 1,
        "duplicadas": 0,
        "invalidas": 1,
        "cancelamentos_aplicados": 0,
        "nao_suportadas": 1,
    }
    detalhe = cliente.get(f"/api/importacoes/{corpo['importacao_id']}").json()
    assert detalhe["contadores"] == corpo["contadores"]
    assert detalhe["origem"] == "lote.zip"
    assert [(a["arquivo"], a["resultado"]) for a in detalhe["arquivos"]] == [
        ("boa.xml", "nova"),
        ("quebrada.xml", "invalida"),
        ("sat.xml", "nao_suportado_sat"),
    ]
    assert detalhe["arquivos"][0]["chave"] == CHAVE_1ITEM


# C5
def test_reimportar_o_mesmo_zip_so_conta_duplicadas(cliente, banco):
    lote = zip_de({"a.xml": texto("nfe_55_1item.xml"), "b.xml": texto("nfe_65_1item.xml")})
    enviar(cliente, "lote.zip", lote)

    segunda = enviar(cliente, "lote.zip", lote).json()

    assert segunda["contadores"]["notas_novas"] == 0
    assert segunda["contadores"]["duplicadas"] == 2
    assert _conta(banco, "notas") == 2


# C6 (a)
def test_evento_antes_da_nota_no_mesmo_zip_cancela(cliente, banco):
    lote = zip_de({"1_evento.xml": evento(CHAVE_1ITEM), "2_nota.xml": texto("nfe_55_1item.xml")})

    corpo = enviar(cliente, "lote.zip", lote).json()

    assert corpo["contadores"]["cancelamentos_aplicados"] == 1
    assert _status(banco, CHAVE_1ITEM) == "cancelada"


# C6 (b)
def test_evento_em_upload_posterior_cancela(cliente, banco):
    enviar(cliente, "nota.xml", texto("nfe_55_1item.xml"))

    enviar(cliente, "evento.xml", evento(CHAVE_1ITEM))

    assert _status(banco, CHAVE_1ITEM) == "cancelada"


# C7
def test_extensao_que_nao_e_zip_nem_xml_e_recusada(cliente, banco):
    resposta = enviar(cliente, "notas.txt", texto("nfe_55_1item.xml"))

    assert resposta.status_code == 400
    assert _conta(banco, "importacoes") == 0


def test_extensao_em_maiusculas_e_aceita(cliente):
    assert enviar(cliente, "NOTA.XML", texto("nfe_55_1item.xml")).status_code == 201


# C8
def test_classificacao_base_roda_no_import(cliente, banco):
    """TOMATE tem NCM do mapa; o ACHOCOLATADO desta variante, nao."""
    fora_do_mapa = variante("nfe_65_1item.xml", chave(1), ncm=("18069000", "99999999"))
    lote = zip_de({"tomate.xml": texto("nfe_55_1item.xml"), "choco.xml": fora_do_mapa})

    corpo = enviar(cliente, "lote.zip", lote).json()

    assert produto(banco, TOMATE)[1:] == ("vegetais", "ncm")
    assert produto(banco, ACHOCOLATADO)[1:] == ("uncategorized", None)
    assert corpo["classificacao"] == {"produtos": 2, "memoria": 0, "ncm": 1, "llm": 0, "bucket": 1}
    resumo = cliente.get(f"/api/importacoes/{corpo['importacao_id']}").json()["classificacao"]
    assert resumo == corpo["classificacao"]


# C9
def test_llm_nao_dispara_no_import_nem_ligado(caminho_banco):
    espiao = LlmEspiao(resposta=("mercado", 0.9))
    cliente = TestClient(criar_app(caminho_banco, llm=espiao))
    fora_do_mapa = variante("nfe_65_1item.xml", chave(1), ncm=("18069000", "99999999"))

    corpo = enviar(cliente, "choco.xml", fora_do_mapa).json()

    assert espiao.chamadas == []
    assert corpo["classificacao"]["bucket"] == 1


def test_disparo_do_llm_classifica_os_pendentes(caminho_banco):
    espiao = LlmEspiao(resposta=("mercado", 0.9))
    cliente = TestClient(criar_app(caminho_banco, llm=espiao))
    fora_do_mapa = variante("nfe_65_1item.xml", chave(1), ncm=("18069000", "99999999"))
    enviar(cliente, "choco.xml", fora_do_mapa)

    resposta = cliente.post("/api/llm/classificar")

    assert resposta.status_code == 200
    assert resposta.json() == {"classificados": 1}
    assert espiao.chamadas == [ACHOCOLATADO]
    item = cliente.get(f"/api/notas/{chave(1)}").json()["itens"][0]
    assert item["categoria_slug"] == "mercado"


def test_disparo_do_llm_desligado_e_409(cliente):
    assert cliente.post("/api/llm/classificar").status_code == 409

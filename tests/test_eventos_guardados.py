"""Todo evento que abre e traz chave e GUARDADO — spec 01 §2 e §6.2.

Decisao do Gui de 2026-10-16 (rodada 02): coerencia com o `xml_raw` das notas, e
a informacao nao se perde se o arquivo original sumir. A carta de correcao real,
que o leitor de cancelamento recusava (virava `invalida`), passa a ser
`evento_registrado`, com o texto da correcao guardado.
"""

import sqlite3
from contextlib import closing

from nfe_parser.banco import abrir_banco, criar_esquema
from nfe_parser.importador import importar
from nfe_parser.migracoes import MIGRACOES, aplicar_migracoes
from tests.apoio import CHAVE_1ITEM, carta_de_correcao, evento, texto, zip_de

CORRECAO = "Onde se le Rua A, 10, leia-se Rua A, 100."
DH_CCE = "2026-07-02T09:00:00-03:00"


def _importar(conexao, tmp_path, membros):
    lote = tmp_path / "lote.zip"
    lote.write_bytes(zip_de(membros))
    return importar(conexao, lote)


def _arquivos(conexao):
    return conexao.execute(
        "SELECT arquivo, resultado, detalhe FROM importacao_arquivos ORDER BY id"
    ).fetchall()


def _eventos(conexao):
    return conexao.execute(
        "SELECT chave, tp_evento, n_seq, dh_evento, correcao FROM eventos ORDER BY id"
    ).fetchall()


def test_carta_de_correcao_e_registrada_e_guardada_com_o_texto(conexao, tmp_path):
    cce = carta_de_correcao(CHAVE_1ITEM, CORRECAO, n_seq=2)

    _importar(conexao, tmp_path, {"nota.xml": texto("nfe_55_1item.xml"), "cce.xml": cce})

    assert ("cce.xml", "evento_registrado", "Carta de Correcao") in _arquivos(conexao)
    assert _eventos(conexao) == [(CHAVE_1ITEM, "110110", 2, DH_CCE, CORRECAO)]
    assert conexao.execute("SELECT xml_raw FROM eventos").fetchone()[0] == cce


def test_evento_de_nota_que_ainda_nao_chegou_tambem_e_guardado(conexao, tmp_path):
    """Quando a nota chegar, a correcao ja esta la."""
    _importar(conexao, tmp_path, {"cce.xml": carta_de_correcao(CHAVE_1ITEM, CORRECAO)})

    assert _arquivos(conexao) == [("cce.xml", "evento_registrado", "Carta de Correcao")]
    assert len(_eventos(conexao)) == 1
    assert conexao.execute("SELECT COUNT(*) FROM notas").fetchone()[0] == 0


def test_cancelamento_tambem_e_guardado_e_continua_cancelando(conexao, tmp_path):
    _importar(
        conexao, tmp_path, {"nota.xml": texto("nfe_55_1item.xml"), "canc.xml": evento(CHAVE_1ITEM)}
    )

    assert ("canc.xml", "cancelamento_aplicado", None) in _arquivos(conexao)
    assert [(tp, n_seq) for _, tp, n_seq, _, _ in _eventos(conexao)] == [("110111", 1)]


def test_reimportar_nao_duplica_eventos(conexao, tmp_path):
    membros = {"cce.xml": carta_de_correcao(CHAVE_1ITEM, CORRECAO)}

    _importar(conexao, tmp_path, membros)
    _importar(conexao, tmp_path, membros)

    assert len(_eventos(conexao)) == 1


def test_banco_antigo_migra_sem_perder_o_log_de_importacao(tmp_path):
    """Um banco na v4 ja tem linhas em `importacao_arquivos`. A v5 reconstroi a
    tabela para o CHECK aceitar `evento_registrado` — sem perder nenhuma linha."""
    caminho = tmp_path / "nfe.db"
    with closing(sqlite3.connect(caminho)) as antigo:
        criar_esquema(antigo)
        aplicar_migracoes(antigo, MIGRACOES[:4])
        antigo.execute("INSERT INTO importacoes (id, origem, iniciado_em) VALUES (1, 'x', 'agora')")
        antigo.execute(
            "INSERT INTO importacao_arquivos (importacao_id, arquivo, resultado)"
            " VALUES (1, 'velho.xml', 'nova')"
        )
        antigo.commit()

    conexao = abrir_banco(caminho)
    try:
        assert _arquivos(conexao) == [("velho.xml", "nova", None)]
        conexao.execute(
            "INSERT INTO importacao_arquivos (importacao_id, arquivo, resultado)"
            " VALUES (1, 'cce.xml', 'evento_registrado')"
        )
    finally:
        conexao.close()


def test_evento_sem_tipo_continua_orfao_e_nao_e_guardado(conexao, tmp_path):
    """Sem `tpEvento` nao se sabe o que o evento e: nao se guarda, e o resultado
    continua o de antes (orfao) — "registrado" diria que esta guardado."""
    sem_tipo = evento(CHAVE_1ITEM).replace("<tpEvento>110111</tpEvento>", "")

    _importar(conexao, tmp_path, {"nota.xml": texto("nfe_55_1item.xml"), "x.xml": sem_tipo})

    assert ("x.xml", "cancelamento_orfao", None) in _arquivos(conexao)
    assert _eventos(conexao) == []

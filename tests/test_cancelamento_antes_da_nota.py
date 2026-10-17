"""Cancelamento que chega num lote ANTERIOR ao da nota — spec 01 §3 e §6.2.

O bug (achado em 2026-10-17): em abril chega o cancelamento de uma nota que ainda
nao esta no banco — `cancelamento_orfao`, e desde a v5 o evento fica guardado em
`eventos`. Em maio chega a nota, e entrava como `ok`: ninguem olhava o evento
guardado, e a nota cancelada CONTAVA COMO GASTO para sempre.

Decisoes de 2026-10-17 (`docs/decisoes.md`): a linha da nota continua `nova`, com
o detalhe dizendo de onde veio o cancelamento; o contador do lote nao a conta.
"""

import sqlite3
from contextlib import closing

from nfe_parser.banco import abrir_banco, criar_esquema
from nfe_parser.importador import importar
from nfe_parser.migracoes import MIGRACOES, aplicar_migracoes
from tests.apoio import (
    CHAVE_1ITEM,
    CHAVE_3ITENS,
    CHAVE_65,
    carta_de_correcao,
    evento,
    texto,
    zip_de,
)

DH_EVENTO = "2026-07-01T10:00:00-03:00"  # o que `apoio.evento` escreve no XML


def _lote(tmp_path, nome, membros):
    lote = tmp_path / nome
    lote.write_bytes(zip_de(membros))
    return lote


def _cancelamento_depois_a_nota(conexao, tmp_path, xml_do_evento):
    """Lote de abril so com o evento; lote de maio so com a nota. Devolve os dois ids."""
    abril = importar(conexao, _lote(tmp_path, "abril.zip", {"canc.xml": xml_do_evento}))
    maio = importar(conexao, _lote(tmp_path, "maio.zip", {"nota.xml": texto("nfe_55_1item.xml")}))
    return abril, maio


def _nota(conexao, chave=CHAVE_1ITEM):
    return conexao.execute(
        "SELECT status, cancelado_em FROM notas WHERE chave = ?", (chave,)
    ).fetchone()


def _log(conexao, importacao_id):
    return conexao.execute(
        "SELECT arquivo, resultado, detalhe FROM importacao_arquivos"
        " WHERE importacao_id = ? ORDER BY id",
        (importacao_id,),
    ).fetchall()


def test_nota_que_chega_depois_do_cancelamento_entra_cancelada(conexao, tmp_path):
    _cancelamento_depois_a_nota(conexao, tmp_path, evento(CHAVE_1ITEM))

    assert _nota(conexao) == ("cancelada", DH_EVENTO)


def test_a_linha_da_nota_continua_nova_e_diz_de_onde_veio_o_cancelamento(conexao, tmp_path):
    abril, maio = _cancelamento_depois_a_nota(conexao, tmp_path, evento(CHAVE_1ITEM))

    assert _log(conexao, maio) == [
        ("nota.xml", "nova", f"cancelada: o cancelamento chegou antes, na importação {abril}")
    ]


def test_a_linha_do_lote_antigo_continua_orfao(conexao, tmp_path):
    """O log registra o desfecho daquele lote: em abril, o cancelamento nao achou nota."""
    abril, _ = _cancelamento_depois_a_nota(conexao, tmp_path, evento(CHAVE_1ITEM))

    assert _log(conexao, abril) == [("canc.xml", "cancelamento_orfao", None)]


def test_o_contador_de_cancelamentos_do_lote_da_nota_nao_a_conta(conexao, tmp_path):
    """O cartao "cancelamentos" conta arquivos de cancelamento; o lote de maio nao tem nenhum."""
    _, maio = _cancelamento_depois_a_nota(conexao, tmp_path, evento(CHAVE_1ITEM))

    assert conexao.execute(
        "SELECT total_arquivos, notas_novas, cancelamentos_aplicados FROM importacoes WHERE id = ?",
        (maio,),
    ).fetchone() == (1, 1, 0)


def test_evento_guardado_sem_dh_evento_ainda_carimba_a_nota(conexao, tmp_path):
    """Fora do leiaute, mas nota cancelada nunca fica sem carimbo (spec 01 §6.2)."""
    sem_hora = evento(CHAVE_1ITEM).replace(f"<dhEvento>{DH_EVENTO}</dhEvento>", "")

    _cancelamento_depois_a_nota(conexao, tmp_path, sem_hora)

    status, cancelado_em = _nota(conexao)
    assert status == "cancelada"
    assert cancelado_em


def test_carta_de_correcao_guardada_nao_cancela_a_nota_que_chega(conexao, tmp_path):
    _, maio = _cancelamento_depois_a_nota(
        conexao, tmp_path, carta_de_correcao(CHAVE_1ITEM, "Onde se le A, leia-se B.")
    )

    assert _nota(conexao) == ("ok", None)
    assert _log(conexao, maio) == [("nota.xml", "nova", None)]


def test_cancelamento_guardado_de_outra_nota_nao_encosta_nesta(conexao, tmp_path):
    _cancelamento_depois_a_nota(conexao, tmp_path, evento(CHAVE_65))

    assert _nota(conexao) == ("ok", None)


def test_reimportar_a_nota_e_so_duplicada_sem_repetir_o_detalhe(conexao, tmp_path):
    """O detalhe conta o que aconteceu NAQUELE lote; num reenvio, nada aconteceu."""
    _cancelamento_depois_a_nota(conexao, tmp_path, evento(CHAVE_1ITEM))
    junho = importar(conexao, _lote(tmp_path, "junho.zip", {"nota.xml": texto("nfe_55_1item.xml")}))

    assert _log(conexao, junho) == [("nota.xml", "duplicada", None)]
    assert _nota(conexao) == ("cancelada", DH_EVENTO)


# --- migracao v6: banco que ja ficou com o defeito --------------------------


def _banco_v5_com_o_defeito(caminho):
    """Um banco na v5, como a v0.3.0 o deixava: cada nota com o seu evento guardado.

    - CHAVE_1ITEM: `ok`, com cancelamento guardado — o defeito.
    - CHAVE_65: `ok`, so com carta de correcao guardada — tem de continuar `ok`.
    - CHAVE_3ITENS: ja `cancelada` com outro carimbo — o primeiro carimbo vence.

    ⚠️ O evento entra por SQL cru, e nao por `importar`: com a correcao, importar
    o cancelamento e depois a nota ja nao produz o defeito que a v6 conserta.
    """
    with closing(sqlite3.connect(caminho)) as antigo:
        antigo.execute("PRAGMA foreign_keys = ON")
        criar_esquema(antigo)
        aplicar_migracoes(antigo, MIGRACOES[:5])
        notas = {
            "a.xml": texto("nfe_55_1item.xml"),
            "b.xml": texto("nfe_65_1item.xml"),
            "c.xml": texto("nfe_55_3itens.xml"),
        }
        importacao_id = importar(antigo, _lote(caminho.parent, "notas.zip", notas))
        antigo.execute(
            "UPDATE notas SET status = 'cancelada', cancelado_em = '2026-06-30T08:00:00-03:00'"
            " WHERE chave = ?",
            (CHAVE_3ITENS,),
        )
        for chave, tp_evento in (
            (CHAVE_1ITEM, "110111"),
            (CHAVE_65, "110110"),
            (CHAVE_3ITENS, "110111"),
        ):
            antigo.execute(
                "INSERT INTO eventos (chave, tp_evento, n_seq, dh_evento, xml_raw,"
                " importacao_id, criado_em) VALUES (?, ?, 1, ?, '<xml/>', ?, 'agora')",
                (chave, tp_evento, DH_EVENTO, importacao_id),
            )
        antigo.commit()


def test_migracao_v6_cancela_a_nota_ok_que_tem_cancelamento_guardado(tmp_path):
    caminho = tmp_path / "nfe.db"
    _banco_v5_com_o_defeito(caminho)

    with closing(abrir_banco(caminho)) as conexao:
        assert _nota(conexao, CHAVE_1ITEM) == ("cancelada", DH_EVENTO)


def test_migracao_v6_nao_mexe_em_quem_nao_tem_cancelamento_nem_no_carimbo_antigo(tmp_path):
    caminho = tmp_path / "nfe.db"
    _banco_v5_com_o_defeito(caminho)

    with closing(abrir_banco(caminho)) as conexao:
        assert _nota(conexao, CHAVE_65) == ("ok", None)
        assert _nota(conexao, CHAVE_3ITENS) == ("cancelada", "2026-06-30T08:00:00-03:00")


def test_migracao_v6_carimba_mesmo_sem_dh_evento(tmp_path):
    caminho = tmp_path / "nfe.db"
    _banco_v5_com_o_defeito(caminho)
    with closing(sqlite3.connect(caminho)) as antigo:
        antigo.execute("UPDATE eventos SET dh_evento = NULL WHERE chave = ?", (CHAVE_1ITEM,))
        antigo.commit()

    with closing(abrir_banco(caminho)) as conexao:
        status, cancelado_em = _nota(conexao, CHAVE_1ITEM)
        assert status == "cancelada"
        assert cancelado_em

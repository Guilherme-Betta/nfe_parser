"""`cancelado_em` e a hora do CANCELAMENTO, nao a da importacao — spec 01 §6.2 e §6.3 item 2.

Decisao do Gui de 2026-10-16: "datas como no XML". Uma compra de 02/10 cancelada
no mesmo dia, cujo evento so e importado em 16/10, guarda 02/10.
"""

from datetime import datetime

from nfe_parser.importador import importar
from tests.apoio import CHAVE_1ITEM, evento, texto, zip_de

DH_EVENTO = "2026-07-01T10:00:00-03:00"  # o que `apoio.evento` escreve no XML


def _cancelado_em(conexao, tmp_path, xml_do_evento):
    lote = tmp_path / "lote.zip"
    lote.write_bytes(zip_de({"nota.xml": texto("nfe_55_1item.xml"), "evento.xml": xml_do_evento}))
    importar(conexao, lote)
    return conexao.execute(
        "SELECT cancelado_em FROM notas WHERE chave = ?", (CHAVE_1ITEM,)
    ).fetchone()[0]


def test_cancelado_em_guarda_o_dh_evento_como_veio_no_xml(conexao, tmp_path):
    xml = evento(CHAVE_1ITEM)
    assert f"<dhEvento>{DH_EVENTO}</dhEvento>" in xml, "apoio.evento mudou; o teste depende dele"

    assert _cancelado_em(conexao, tmp_path, xml) == DH_EVENTO


def test_evento_sem_dh_evento_usa_a_hora_da_importacao(conexao, tmp_path):
    """Fora do leiaute, mas nota cancelada nunca fica sem carimbo."""
    xml = evento(CHAVE_1ITEM).replace(f"<dhEvento>{DH_EVENTO}</dhEvento>", "")

    carimbo = _cancelado_em(conexao, tmp_path, xml)

    assert carimbo
    assert datetime.fromisoformat(carimbo).year >= 2026

"""`aplicar_cancelamento` nao commita — achado 1a da revisao geral de 2026-10-14.

Escrito ANTES da correcao e congelado por commit: quem corrigir nao edita este
arquivo.

🔴 A regra e a D3 da `specs/013-integracao/spec.md`: quem abriu a transacao e
que a fecha, e quem abre o lote e `importar`. A 013 tirou o `commit()` de
`persistir_nota` (C1.5), e o mesmo `commit()` ficou aqui, na funcao que a
SEGUNDA passada do lote chama. Com ele, um lote com evento de cancelamento
deixa de ser uma transacao so: tudo o que veio antes do evento ja esta no disco
quando o resto do lote falha.

⭐ O teste e o mesmo do C1.5: grava, desfaz com `rollback()`, e confere que nada
ficou. Se a funcao commitasse, o `rollback()` nao teria o que desfazer.
"""

import pytest

from nfe_parser.banco import abrir_banco
from nfe_parser.cancelamento import aplicar_cancelamento

CHAVE = "35260499999999000199550010000000011000000017"


@pytest.fixture
def conexao(tmp_path):
    con = abrir_banco(tmp_path / "nfe.db")
    # Linha de base: a nota entra commitada, fora do que o `rollback` desfaz.
    con.execute(
        "INSERT INTO notas (chave, modelo, dh_emi, valor_total, xml_raw, criado_em)"
        " VALUES (?, 55, '2026-04-10T09:00:00-03:00', 1000, '<xml/>',"
        " '2026-04-10T12:00:00+00:00')",
        (CHAVE,),
    )
    con.commit()
    yield con
    con.close()


def _status(conexao):
    return conexao.execute("SELECT status FROM notas WHERE chave = ?", (CHAVE,)).fetchone()[0]


def test_aplicar_cancelamento_nao_commita_e_o_rollback_desfaz(conexao):
    """⚠️ A assercao do meio nao e redundante: sem ela, uma funcao que nao
    fizesse NADA tambem passaria, porque o `rollback()` acharia a nota intacta.
    """
    evento = {"ch_nfe": CHAVE, "tp_evento": "110111", "dh_evento": "2026-04-10T10:00:00-03:00"}

    assert aplicar_cancelamento(conexao, evento) == "cancelamento_aplicado"
    assert _status(conexao) == "cancelada"  # gravou...

    conexao.rollback()

    assert _status(conexao) == "ok"  # ...mas nao confirmou

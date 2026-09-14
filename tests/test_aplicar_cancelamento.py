"""Testes de `aplicar_cancelamento` — tarefa 2 da story 005-cancelamento-duas-passadas.

Escritos ANTES da implementacao (passo 2 do loop) e congelados por commit. O
modelo local recebe este arquivo como LEITURA (`--read`), nunca como editavel.

⭐ POR QUE ISTO E UMA TAREFA SEPARADA DA 1: "ler o XML" e "escrever no banco"
sao dois defeitos, e a regra 2 do fatiamento ja corrompeu arquivo neste projeto
quando os dois foram pedidos juntos.

As notas destes testes sao inseridas com SQL direto, nao pelo `persistir_nota`.
De proposito: o que esta sob teste aqui e o UPDATE, e uma falha do extrator ou
da persistencia nao pode aparecer como falha desta tarefa.

Criterios em `specs/005-cancelamento-duas-passadas/spec.md` §3, bloco C2.
"""

import pytest
from nfe_parser.cancelamento import aplicar_cancelamento

from nfe_parser.banco import abrir_banco

CHAVE_A = "35260499999999000199550010000000011000000017"
CHAVE_B = "35260499999999000199650010000000021000000025"
CHAVE_AUSENTE = "35260499999999000199550019999999991000000099"


@pytest.fixture
def conexao(tmp_path):
    con = abrir_banco(tmp_path / "nfe.db")
    yield con
    con.close()


def _nota(conexao, chave):
    """Insere uma nota `status='ok'` com o minimo que o DDL exige."""
    conexao.execute(
        "INSERT INTO notas (chave, modelo, dh_emi, valor_total, xml_raw, criado_em)"
        " VALUES (?, 55, '2026-04-10T09:00:00-03:00', 1000, '<xml/>', '2026-04-10T12:00:00+00:00')",
        (chave,),
    )
    conexao.commit()


def _evento(ch_nfe=CHAVE_A, tp_evento="110111"):
    return {"ch_nfe": ch_nfe, "tp_evento": tp_evento, "dh_evento": "2026-04-10T10:00:00-03:00"}


def _estado(conexao, chave):
    return conexao.execute(
        "SELECT status, cancelado_em FROM notas WHERE chave = ?", (chave,)
    ).fetchone()


# --- C2.1 -------------------------------------------------------------------
def test_evento_que_bate_com_nota_cancela_e_devolve_aplicado(conexao):
    _nota(conexao, CHAVE_A)

    assert aplicar_cancelamento(conexao, _evento()) == "cancelamento_aplicado"

    status, cancelado_em = _estado(conexao, CHAVE_A)
    assert status == "cancelada"
    assert cancelado_em  # carimbo preenchido, nao vazio nem NULL


# --- C2.2 -------------------------------------------------------------------
def test_evento_sem_nota_correspondente_e_orfao(conexao):
    _nota(conexao, CHAVE_A)

    assert aplicar_cancelamento(conexao, _evento(ch_nfe=CHAVE_AUSENTE)) == "cancelamento_orfao"


def test_orfao_nao_cria_nota_fantasma(conexao):
    """🔒 O criterio que separa esta story de uma implementacao ingenua.

    Um `INSERT OR IGNORE` ou um `INSERT` defensivo passaria no teste acima e
    reprovaria aqui — e o banco ficaria com uma nota sem emitente, sem valor e
    sem XML, inventada a partir de um evento.
    """
    aplicar_cancelamento(conexao, _evento(ch_nfe=CHAVE_AUSENTE))

    assert conexao.execute("SELECT COUNT(*) FROM notas").fetchone()[0] == 0


# --- C2.3 -------------------------------------------------------------------
def test_evento_sem_chave_e_orfao_e_nao_toca_em_nota_nenhuma(conexao):
    _nota(conexao, CHAVE_A)

    assert aplicar_cancelamento(conexao, _evento(ch_nfe=None)) == "cancelamento_orfao"
    assert _estado(conexao, CHAVE_A) == ("ok", None)


# --- C2.4 -------------------------------------------------------------------
@pytest.mark.parametrize("tp_evento", ["110110", None, "ABC"])
def test_evento_que_nao_e_cancelamento_nao_cancela(conexao, tp_evento):
    """`110110` e carta de correcao. Cancelar por causa dela seria apagar uma
    venda real do relatorio do Gui."""
    _nota(conexao, CHAVE_A)

    resultado = aplicar_cancelamento(conexao, _evento(tp_evento=tp_evento))

    assert resultado == "cancelamento_orfao"
    assert _estado(conexao, CHAVE_A) == ("ok", None)


# --- C2.5 -------------------------------------------------------------------
def test_aplicar_duas_vezes_nao_move_o_carimbo(conexao):
    """⭐ Idempotencia: o estado final depois de duas aplicacoes e identico ao
    de uma. O `AND status = 'ok'` do UPDATE e o que garante isso."""
    _nota(conexao, CHAVE_A)

    assert aplicar_cancelamento(conexao, _evento()) == "cancelamento_aplicado"
    primeiro_carimbo = _estado(conexao, CHAVE_A)[1]

    assert aplicar_cancelamento(conexao, _evento()) == "cancelamento_aplicado"

    assert _estado(conexao, CHAVE_A) == ("cancelada", primeiro_carimbo)


# --- C2.6 -------------------------------------------------------------------
def test_cancelar_uma_nota_nao_encosta_nas_outras(conexao):
    _nota(conexao, CHAVE_A)
    _nota(conexao, CHAVE_B)

    aplicar_cancelamento(conexao, _evento(ch_nfe=CHAVE_A))

    assert _estado(conexao, CHAVE_A)[0] == "cancelada"
    assert _estado(conexao, CHAVE_B) == ("ok", None)

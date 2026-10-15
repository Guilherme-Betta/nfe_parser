"""Nucleo do orcamento — spec 04 §2 e §3, criterios O1 a O6.

O cenario de junho/2026 (todas as notas da loja das fixtures, exceto onde dito):
- CHAVE_3ITENS: ACHOCOLATADO 6,66 + ARROZ 2,85 (mercado-mercearia → rollup `mercado`)
  e TOMATE 8,04 (`vegetais`);
- um TOMATE de OUTRA loja, com NCM fora do mapa: 8,04 no bucket → nao classificado;
- um ACHOCOLATADO de 12,34 CANCELADO — nao conta;
- e as notas de abril e maio, que nao sao de junho.
"""

import pytest

from nfe_parser.banco import abrir_banco
from nfe_parser.migracoes import MIGRACOES, versao_do_banco
from nfe_parser.operacoes import importar_e_classificar
from nfe_parser.orcamento import (
    alterar_limite,
    apagar_orcamento,
    definir_orcamento,
    orcamento,
    orcamentos_do_mes,
)
from nfe_parser.seed import carregar_seed_padrao
from nfe_parser.taxonomia import apagar_categoria, criar_categoria
from tests.apoio import chave, evento, texto, variante

JUNHO = "2026-06"


@pytest.fixture
def con(conexao, tmp_path):
    with conexao:
        carregar_seed_padrao(conexao)
    arquivos = {
        "abril.xml": texto("nfe_55_1item.xml"),
        "maio.xml": texto("nfe_65_1item.xml"),
        "junho.xml": texto("nfe_55_3itens.xml"),
        "sem_categoria.xml": variante(
            "nfe_55_1item.xml",
            chave(1),
            cnpj="88888888000188",
            ncm=("07020000", "99999999"),
            dh_emi="2026-06-10T12:00:00-03:00",
        ),
        "cancelada.xml": variante("nfe_65_1item.xml", chave(2), dh_emi="2026-06-15T12:00:00-03:00"),
        "evento.xml": evento(chave(2)),
    }
    for nome, xml in arquivos.items():
        caminho = tmp_path / nome
        caminho.write_text(xml, encoding="utf-8")
        importar_e_classificar(conexao, caminho, nome)
    return conexao


def _linhas(con, mes=JUNHO):
    return {linha["categoria_slug"]: linha for linha in orcamentos_do_mes(con, mes)["linhas"]}


def _definir(con, slug, limite, mes=JUNHO):
    with con:
        return definir_orcamento(con, slug, mes, limite)


# O1 + O2 + O5
def test_realizado_soma_ao_centavo_com_rollup_sem_cancelada_e_sem_outro_mes(con):
    readout = orcamentos_do_mes(con, JUNHO)

    gastos = {linha["categoria_slug"]: linha["gasto"] for linha in readout["linhas"]}
    assert gastos == {"mercado": 666 + 285, "vegetais": 804}
    assert readout["nao_classificado"] == {"gasto": 804}
    assert readout["mes"] == JUNHO


def test_gasto_sem_teto_aparece_com_limite_nulo(con):
    linha = _linhas(con)["mercado"]

    assert linha == {
        "orcamento_id": None,
        "categoria_slug": "mercado",
        "nome": linha["nome"],
        "limite": None,
        "gasto": 951,
        "saldo": None,
        "pct": None,
        "estouro": False,
    }


def test_teto_sem_gasto_aparece_com_gasto_zero(con):
    orcamento_id = _definir(con, "bebidas", 10000)

    linha = _linhas(con)["bebidas"]

    assert (linha["orcamento_id"], linha["gasto"], linha["saldo"]) == (orcamento_id, 0, 10000)
    assert linha["pct"] == 0.0


# O4
def test_saldo_negativo_e_estouro(con):
    _definir(con, "mercado", 900)

    linha = _linhas(con)["mercado"]

    assert (linha["limite"], linha["saldo"], linha["estouro"]) == (900, -51, True)
    assert linha["pct"] == round(951 / 900, 4)


def test_totais_somam_limites_e_todo_o_gasto_do_mes(con):
    _definir(con, "mercado", 2000)
    _definir(con, "bebidas", 500)

    assert orcamentos_do_mes(con, JUNHO)["totais"] == {"limite": 2500, "gasto": 951 + 804 + 804}


def test_mes_sem_nada_tem_linhas_vazias(con):
    readout = orcamentos_do_mes(con, "2025-01")

    assert readout["linhas"] == []
    assert readout["nao_classificado"] == {"gasto": 0}
    assert readout["totais"] == {"limite": 0, "gasto": 0}


# O3
def test_definir_devolve_o_orcamento(con):
    orcamento_id = _definir(con, "mercado", 150000)

    assert orcamento(con, orcamento_id) == {
        "id": orcamento_id,
        "categoria_slug": "mercado",
        "mes": JUNHO,
        "limite": 150000,
    }


def test_repetir_categoria_e_mes_levanta(con):
    _definir(con, "mercado", 1000)

    with pytest.raises(ValueError):
        _definir(con, "mercado", 2000)


@pytest.mark.parametrize("slug", ["mercado-mercearia", "uncategorized"])
def test_subcategoria_ou_bucket_levanta(con, slug):
    with pytest.raises(ValueError):
        _definir(con, slug, 1000)


@pytest.mark.parametrize("limite", [0, -1, 10.5, "1000", True, None])
def test_limite_tem_de_ser_inteiro_positivo(con, limite):
    """`True` e int em Python; aqui nao vale como centavo."""
    with pytest.raises(ValueError):
        _definir(con, "mercado", limite)


@pytest.mark.parametrize("mes", ["2026-13", "2026-00", "2026-6", "junho", "", None])
def test_mes_fora_do_formato_levanta(con, mes):
    with pytest.raises(ValueError):
        _definir(con, "mercado", 1000, mes=mes)


def test_categoria_inexistente_levanta_lookup(con):
    with pytest.raises(LookupError):
        _definir(con, "nao-existe", 1000)


def test_alterar_limite(con):
    orcamento_id = _definir(con, "mercado", 1000)

    with con:
        alterar_limite(con, orcamento_id, 3000)

    assert orcamento(con, orcamento_id)["limite"] == 3000


def test_alterar_limite_invalido_ou_inexistente(con):
    orcamento_id = _definir(con, "mercado", 1000)

    with pytest.raises(ValueError):
        alterar_limite(con, orcamento_id, 0)
    with pytest.raises(LookupError):
        alterar_limite(con, 999, 1000)


def test_apagar(con):
    orcamento_id = _definir(con, "mercado", 1000)

    with con:
        apagar_orcamento(con, orcamento_id)

    assert orcamento(con, orcamento_id) is None
    with pytest.raises(LookupError):
        apagar_orcamento(con, orcamento_id)


# O6
def test_migracao_idempotente(tmp_path):
    caminho = tmp_path / "nfe.db"
    abrir_banco(caminho).close()

    conexao = abrir_banco(caminho)
    try:
        assert versao_do_banco(conexao) == len(MIGRACOES)
        assert conexao.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'orcamentos'"
        ).fetchone()
    finally:
        conexao.close()


def test_apagar_categoria_apaga_o_orcamento_dela(con):
    with con:
        criar_categoria(con, "Pets")
    _definir(con, "pets", 1000)

    with con:
        apagar_categoria(con, "pets")

    assert con.execute("SELECT COUNT(*) FROM orcamentos").fetchone()[0] == 0

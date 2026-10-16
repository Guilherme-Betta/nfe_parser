"""Agregacoes da visualizacao — spec 05 §3, criterios V1 a V7.

O cenario (lojas A = fixtures, B e C = variantes):
- abril  (A): TOMATE 8,04 (1.5 kg a 5,36)                          → vegetais
- maio   (A): ACHOCOLATADO 12,34 (2 un a 6,17)                      → mercado-mercearia
- junho  (A): ACHOCOLATADO 6,66 (2 un) + TOMATE 8,04 + ARROZ 2,85 (3 pc)
- junho  (C): TOMATE de outra loja, NCM fora do mapa: 8,04          → bucket
- junho  (A): ACHOCOLATADO 12,34 CANCELADO                          → nao conta
- julho:      nada                                                  → 0 na serie
- agosto (B): TOMATE de outra loja: 8,04                            → vegetais
"""

import pytest

from nfe_parser import relatorios
from nfe_parser.operacoes import importar_e_classificar
from nfe_parser.seed import carregar_seed_padrao
from tests.apoio import ACHOCOLATADO, CNPJ_FIXTURE, chave, evento, texto, variante

LOJA_A, LOJA_B, LOJA_C = CNPJ_FIXTURE, "88888888000188", "77777777000177"


@pytest.fixture
def con(conexao, tmp_path):
    with conexao:
        carregar_seed_padrao(conexao)
    arquivos = {
        "abril.xml": texto("nfe_55_1item.xml"),
        "maio.xml": texto("nfe_65_1item.xml"),
        "junho.xml": texto("nfe_55_3itens.xml"),
        "agosto.xml": variante(
            "nfe_55_1item.xml", chave(1), cnpj=LOJA_B, dh_emi="2026-08-05T10:00:00-03:00"
        ),
        "bucket.xml": variante(
            "nfe_55_1item.xml",
            chave(3),
            cnpj=LOJA_C,
            ncm=("07020000", "99999999"),
            dh_emi="2026-06-25T10:00:00-03:00",
        ),
        "cancelada.xml": variante("nfe_65_1item.xml", chave(2), dh_emi="2026-06-20T10:00:00-03:00"),
        "evento.xml": evento(chave(2)),
    }
    for nome, xml in arquivos.items():
        caminho = tmp_path / nome
        caminho.write_text(xml, encoding="utf-8")
        importar_e_classificar(conexao, caminho, nome)
    return conexao


def _id(con, descricao, loja=LOJA_A):
    """O produto pela descricao; para o TOMATE (identidade por texto), tambem pela loja."""
    return con.execute(
        "SELECT id FROM produtos WHERE descricao_exemplo = ?"
        " AND (identidade_origem = 'gtin' OR emit_cnpj = ?)",
        (descricao, loja),
    ).fetchone()[0]


def _serie(lista):
    return [(ponto["mes"], ponto["gasto"]) for ponto in lista]


# --- V2 gasto-mensal ------------------------------------------------------------


def test_mensal_em_ordem_com_zero_no_mes_vazio_e_sem_cancelada(con):
    assert _serie(relatorios.gasto_mensal(con)) == [
        ("2026-04", 804),
        ("2026-05", 1234),
        ("2026-06", 666 + 804 + 285 + 804),
        ("2026-07", 0),
        ("2026-08", 804),
    ]


def test_mensal_respeita_o_intervalo_e_preenche_ate_as_pontas(con):
    assert _serie(relatorios.gasto_mensal(con, de="2026-03", ate="2026-05")) == [
        ("2026-03", 0),
        ("2026-04", 804),
        ("2026-05", 1234),
    ]


def test_mensal_por_categoria_faz_rollup(con):
    """Os produtos estao em `mercado-mercearia`; o filtro e por `mercado`."""
    assert _serie(relatorios.gasto_mensal(con, categoria_slug="mercado")) == [
        ("2026-05", 1234),
        ("2026-06", 666 + 285),
    ]


def test_mensal_por_loja_e_por_produto(con):
    assert _serie(relatorios.gasto_mensal(con, loja_cnpj=LOJA_B)) == [("2026-08", 804)]
    achocolatado = _id(con, ACHOCOLATADO)
    assert _serie(relatorios.gasto_mensal(con, produto_id=achocolatado)) == [
        ("2026-05", 1234),
        ("2026-06", 666),
    ]


def test_mensal_sem_nada_e_lista_vazia(con):
    assert relatorios.gasto_mensal(con, loja_cnpj="00000000000000") == []


# --- V3 gasto-categoria ---------------------------------------------------------


def test_categoria_com_rollup_e_bucket_a_parte(con):
    resultado = relatorios.gasto_categoria(con)

    assert {(l["categoria_slug"], l["gasto"]) for l in resultado["linhas"]} == {
        ("mercado", 1234 + 666 + 285),
        ("vegetais", 804 * 3),
    }
    assert resultado["nao_classificado"] == {"gasto": 804}


def test_categoria_filtrada_por_loja(con):
    resultado = relatorios.gasto_categoria(con, loja_cnpj=LOJA_A)

    assert {(l["categoria_slug"], l["gasto"]) for l in resultado["linhas"]} == {
        ("mercado", 2185),
        ("vegetais", 1608),
    }
    assert resultado["nao_classificado"] == {"gasto": 0}


# --- V4 gasto-loja ----------------------------------------------------------------


def test_loja_maior_primeiro_e_empate_pelo_cnpj(con):
    lojas = [(l["emit_cnpj"], l["gasto"]) for l in relatorios.gasto_loja(con)]

    assert lojas == [(LOJA_A, 804 + 1234 + 1755), (LOJA_C, 804), (LOJA_B, 804)]
    assert relatorios.gasto_loja(con)[0]["emit_nome"]


def test_loja_filtrada_por_categoria(con):
    lojas = [
        (l["emit_cnpj"], l["gasto"]) for l in relatorios.gasto_loja(con, categoria_slug="vegetais")
    ]

    assert lojas == [(LOJA_A, 1608), (LOJA_B, 804)]


# --- V5 top-produtos ------------------------------------------------------------


def test_top_por_valor(con):
    top = relatorios.top_produtos(con)

    assert [(p["produto_id"], p["gasto"]) for p in top] == [
        (_id(con, ACHOCOLATADO), 1900),
        (_id(con, "TOMATE ITALIANO KG"), 1608),
        (_id(con, "TOMATE ITALIANO KG", LOJA_B), 804),
        (_id(con, "TOMATE ITALIANO KG", LOJA_C), 804),
        (_id(con, "ARROZ BRANCO TIPO 1 1KG"), 285),
    ]
    assert top[0]["quantidade"] == "4.0000"
    assert (top[0]["identidade_origem"], top[0]["aproximado"]) == ("gtin", False)
    assert (top[1]["identidade_origem"], top[1]["aproximado"]) == ("texto", True)


def test_top_diz_a_loja_do_produto_por_texto(con):
    """Tres TOMATEs de lojas diferentes sao tres produtos (identidade por texto + CNPJ).
    Sem a loja, o ranking mostraria tres linhas iguais. Por GTIN, a loja nao se aplica."""
    lojas = {p["produto_id"]: p["emit_cnpj"] for p in relatorios.top_produtos(con)}

    assert lojas[_id(con, "TOMATE ITALIANO KG", LOJA_B)] == LOJA_B
    assert lojas[_id(con, "TOMATE ITALIANO KG", LOJA_C)] == LOJA_C
    assert lojas[_id(con, ACHOCOLATADO)] is None


def test_top_por_quantidade_soma_em_decimal_exato(con):
    top = relatorios.top_produtos(con, ordenar="quantidade")

    assert [(p["descricao_exemplo"][:6], p["quantidade"]) for p in top] == [
        ("ACHOCO", "4.0000"),
        ("TOMATE", "3.0000"),
        ("ARROZ ", "3.0000"),
        ("TOMATE", "1.5000"),
        ("TOMATE", "1.5000"),
    ]


def test_top_respeita_o_limite(con):
    assert len(relatorios.top_produtos(con, limite=2)) == 2


def test_top_recusa_ordem_desconhecida(con):
    with pytest.raises(ValueError):
        relatorios.top_produtos(con, ordenar="preco")


# --- V6 preco-no-tempo ----------------------------------------------------------


def test_preco_no_tempo_em_ordem_sem_cancelada(con):
    resultado = relatorios.preco_no_tempo(con, _id(con, ACHOCOLATADO))

    assert [(p["data"][:10], p["valor_unitario"]) for p in resultado["pontos"]] == [
        ("2026-05-20", "6.1700000000"),
        ("2026-06-02", "3.3300000000"),
    ]
    assert (resultado["identidade_origem"], resultado["aproximado"]) == ("gtin", False)
    assert resultado["pontos"][0]["emit_cnpj"] == LOJA_A
    assert resultado["descricao_exemplo"] == ACHOCOLATADO


def test_preco_no_tempo_de_produto_por_texto_e_aproximado(con):
    resultado = relatorios.preco_no_tempo(con, _id(con, "TOMATE ITALIANO KG"))

    assert resultado["aproximado"] is True
    assert len(resultado["pontos"]) == 2


def test_preco_no_tempo_de_produto_inexistente_levanta(con):
    with pytest.raises(LookupError):
        relatorios.preco_no_tempo(con, 999)


# --- filtros inexistentes e V7 read-only ------------------------------------------


@pytest.mark.parametrize(
    "filtro", [{"categoria_slug": "nao-existe"}, {"produto_id": 999}], ids=["categoria", "produto"]
)
def test_filtro_inexistente_levanta(con, filtro):
    with pytest.raises(LookupError):
        relatorios.gasto_mensal(con, **filtro)
    with pytest.raises(LookupError):
        relatorios.gasto_loja(con, **filtro)


def test_nada_aqui_escreve_no_banco(con):
    antes = con.total_changes
    achocolatado = _id(con, ACHOCOLATADO)

    relatorios.gasto_mensal(con, categoria_slug="mercado")
    relatorios.gasto_categoria(con, de="2026-01")
    relatorios.gasto_loja(con, ate="2026-12")
    relatorios.top_produtos(con, ordenar="quantidade")
    relatorios.preco_no_tempo(con, achocolatado)

    assert con.total_changes == antes

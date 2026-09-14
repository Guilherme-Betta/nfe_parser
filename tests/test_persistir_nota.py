"""Testes de `persistir_nota` — tarefa 1 da story 004-lote-zip-dedup.

Escritos ANTES da implementacao (passo 2 do loop) e congelados por commit. O
modelo local recebe este arquivo como LEITURA (`--read`), nunca como arquivo
editavel: se ele puder editar o teste, ele edita o teste para faze-lo passar,
que e o caminho mais curto para o objetivo dado.

⭐ ESTE MODULO NAO TESTA DEDUP. Insercao e dedup sao dois defeitos, e a regra 2
do fatiamento manda um pedido por defeito. O dedup esta em `test_dedup.py`
(tarefa 2), e a ordem importa: pedidos juntos, a saida curta e um
`INSERT OR REPLACE`, que sobrescreve o `criado_em` e reprova em C2.3.

Criterios em `specs/004-lote-zip-dedup/spec.md` §3, bloco C1.
"""

from datetime import datetime
from pathlib import Path

import pytest

from nfe_parser.banco import abrir_banco
from nfe_parser.extrator import extrair_nota
from nfe_parser.persistencia import persistir_nota

FIXTURES = Path(__file__).parent / "fixtures"

CHAVE_1ITEM = "35260499999999000199550010000000011000000017"

# Colunas NOT NULL do DDL da story 001. C1.5 confere que nenhuma sai NULL.
NOT_NULL_NOTAS = ("chave", "modelo", "dh_emi", "valor_total", "xml_raw", "criado_em")
NOT_NULL_ITENS = ("nota_chave", "n_item", "descricao", "quantidade", "valor_linha", "criado_em")


@pytest.fixture
def conexao(tmp_path):
    """Um banco novo por teste, fechado no fim."""
    con = abrir_banco(tmp_path / "nfe.db")
    yield con
    con.close()


def _extraido(nome):
    """O `dict` que `extrair_nota` devolve — a entrada exata de `persistir_nota`."""
    return extrair_nota((FIXTURES / nome).read_text(encoding="utf-8"))


@pytest.fixture
def extraido_1item():
    return _extraido("nfe_55_1item.xml")


def _conta(con, tabela):
    return con.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]


# --- C1.1 -------------------------------------------------------------------
def test_persiste_uma_nota_e_um_item(conexao, extraido_1item):
    persistir_nota(conexao, extraido_1item)

    assert _conta(conexao, "notas") == 1
    assert _conta(conexao, "itens") == 1


# --- C1.2 -------------------------------------------------------------------
def test_persiste_os_tres_itens_de_uma_nota(conexao):
    persistir_nota(conexao, _extraido("nfe_55_3itens.xml"))

    assert _conta(conexao, "notas") == 1
    assert _conta(conexao, "itens") == 3

    n_itens = conexao.execute("SELECT n_item FROM itens ORDER BY n_item").fetchall()
    assert [linha[0] for linha in n_itens] == [1, 2, 3]


# --- C1.3 -------------------------------------------------------------------
def test_dinheiro_vai_para_o_banco_em_centavos_inteiros(conexao, extraido_1item):
    """`vNF` "8.04" ja chegou como 804 no dict; a persistencia so nao pode desfazer."""
    persistir_nota(conexao, extraido_1item)

    (valor_total,) = conexao.execute("SELECT valor_total FROM notas").fetchone()
    (valor_linha,) = conexao.execute("SELECT valor_linha FROM itens").fetchone()

    assert valor_total == 804
    assert valor_linha == 804
    assert isinstance(valor_total, int)
    assert isinstance(valor_linha, int)


# --- C1.4 -------------------------------------------------------------------
def test_quantidade_e_valor_unitario_sao_a_string_exata_do_xml(conexao, extraido_1item):
    """O que engana: passar por `float` ou `Decimal` transforma "1.5000" em "1.5".

    A conversao nao levanta erro nenhum — ela so apaga os zeros, em silencio, e
    nenhuma outra assercao deste modulo alcancaria isso.
    """
    persistir_nota(conexao, extraido_1item)

    quantidade, valor_unitario = conexao.execute(
        "SELECT quantidade, valor_unitario FROM itens"
    ).fetchone()

    assert quantidade == "1.5000"
    assert valor_unitario == "5.3600000000"


# --- C1.5 -------------------------------------------------------------------
def test_nenhuma_coluna_not_null_sai_vazia(conexao, extraido_1item):
    persistir_nota(conexao, extraido_1item)

    nota = conexao.execute(f"SELECT {', '.join(NOT_NULL_NOTAS)} FROM notas").fetchone()
    item = conexao.execute(f"SELECT {', '.join(NOT_NULL_ITENS)} FROM itens").fetchone()

    assert all(valor is not None for valor in nota)
    assert all(valor is not None for valor in item)


# --- C1.5 (os campos do emitente, que nao sao NOT NULL mas nao podem se perder) ---
def test_os_campos_do_emitente_chegam_ao_banco(conexao, extraido_1item):
    linha = conexao.execute(
        "SELECT emit_nome, emit_cnpj, emit_municipio, emit_uf FROM notas"
    ).fetchone()
    assert linha is None  # ainda nao persistiu — guarda contra um fixture vazando

    persistir_nota(conexao, extraido_1item)

    assert conexao.execute(
        "SELECT emit_nome, emit_cnpj, emit_municipio, emit_uf FROM notas"
    ).fetchone() == ("MERCEARIA EXEMPLO LTDA", "99999999000199", "SAO PAULO", "SP")


# --- C1.5 (chave, modelo e identificacao) -----------------------------------
def test_chave_modelo_serie_e_numero_chegam_ao_banco(conexao, extraido_1item):
    persistir_nota(conexao, extraido_1item)

    assert conexao.execute("SELECT chave, modelo, serie, numero FROM notas").fetchone() == (
        CHAVE_1ITEM,
        55,
        1,
        1,
    )


# --- C1.6 -------------------------------------------------------------------
def test_criado_em_e_um_iso_8601_legivel(conexao, extraido_1item):
    """⛔ Nao congele o relogio e nao compare com literal.

    O que interessa e o FORMATO: um `criado_em` que o `fromisoformat` nao le
    torna a coluna inutil para ordenar importacoes depois.
    """
    persistir_nota(conexao, extraido_1item)

    (criado_nota,) = conexao.execute("SELECT criado_em FROM notas").fetchone()
    (criado_item,) = conexao.execute("SELECT criado_em FROM itens").fetchone()

    assert isinstance(criado_nota, str)
    assert isinstance(criado_item, str)
    datetime.fromisoformat(criado_nota)
    datetime.fromisoformat(criado_item)


# --- C1.7 -------------------------------------------------------------------
def test_status_sai_ok_pelo_default_do_ddl(conexao, extraido_1item):
    persistir_nota(conexao, extraido_1item)

    assert conexao.execute("SELECT status FROM notas").fetchone()[0] == "ok"


# --- C1.8 -------------------------------------------------------------------
def test_gtin_sai_null_quando_o_xml_dizia_sem_gtin(conexao, extraido_1item):
    """O `extrair_nota` ja resolveu "SEM GTIN" -> None. Aqui so nao pode desfazer."""
    assert extraido_1item["itens"][0]["gtin"] is None

    persistir_nota(conexao, extraido_1item)

    assert conexao.execute("SELECT gtin FROM itens").fetchone()[0] is None


# --- C1.9 -------------------------------------------------------------------
def test_sem_importacao_id_a_coluna_sai_null(conexao, extraido_1item):
    persistir_nota(conexao, extraido_1item)

    assert conexao.execute("SELECT importacao_id FROM notas").fetchone()[0] is None


def test_o_importacao_id_recebido_chega_a_nota(conexao, extraido_1item):
    """O `PRAGMA foreign_keys` esta ligado, entao a importacao tem de existir antes."""
    cursor = conexao.execute(
        "INSERT INTO importacoes (origem, iniciado_em) VALUES ('lote.zip', '2026-01-01T00:00:00')"
    )
    importacao_id = cursor.lastrowid

    persistir_nota(conexao, extraido_1item, importacao_id)

    assert conexao.execute("SELECT importacao_id FROM notas").fetchone()[0] == importacao_id


# --- C1.10 ------------------------------------------------------------------
def test_devolve_a_string_nova(conexao, extraido_1item):
    assert persistir_nota(conexao, extraido_1item) == "nova"

"""Testes de `resolver_produto_por_gtin` — contrato da story 008, tarefa 2.

Escritos ANTES da implementacao (passo 2 do loop) e congelados por commit. O
modelo local recebe este arquivo como LEITURA (`--read`), nunca como editavel.

Criterios em `specs/008-identidade-produto/spec.md` §4, bloco C2.

⚠️ Toda leitura aqui seleciona AS COLUNAS PELO NOME. E o remedio do risco R1 do
recorte: a story 012 passa a gravar `origem` e `confianca`, e a 009 o
`categoria_id`. Um `SELECT *` comparado como tupla ficaria vermelho la, numa
story que nao mexeu em nada disto.
"""

import pytest

from nfe_parser.banco import abrir_banco
from nfe_parser.produtos import resolver_produto_por_gtin

GTIN = "7891234567890"
OUTRO_GTIN = "7899876543210"


@pytest.fixture
def conexao(tmp_path):
    con = abrir_banco(tmp_path / "nfe.db")
    yield con
    con.close()


def _campo(con, produto_id, coluna):
    linha = con.execute(f"SELECT {coluna} FROM produtos WHERE id = ?", (produto_id,)).fetchone()
    return linha[0]


def _quantas_linhas(con):
    return con.execute("SELECT COUNT(*) FROM produtos").fetchone()[0]


# --- C2.1 -------------------------------------------------------------------
def test_gtin_inedito_cria_a_linha_e_devolve_o_id(conexao):
    produto_id = resolver_produto_por_gtin(conexao, GTIN, "ARROZ TIPO 1 5KG")

    assert isinstance(produto_id, int)
    assert _quantas_linhas(conexao) == 1


# --- C2.2 -------------------------------------------------------------------
def test_a_linha_criada_tem_identidade_gtin(conexao):
    produto_id = resolver_produto_por_gtin(conexao, GTIN, "ARROZ TIPO 1 5KG")

    assert _campo(conexao, produto_id, "identidade_origem") == "gtin"
    assert _campo(conexao, produto_id, "gtin") == GTIN


# --- C2.3 -------------------------------------------------------------------
def test_o_par_de_texto_fica_nulo_em_produto_de_gtin(conexao):
    """Quem tem codigo de barras nao e identificado por descricao.

    Deixar `descricao_normalizada` preenchida aqui seria pior que inutil: o
    indice unico parcial `ux_produtos_texto` so cobre linhas com `gtin IS NULL`,
    entao esses valores nao teriam unicidade garantida e ainda poderiam ser
    devolvidos por engano pela busca por texto.
    """
    produto_id = resolver_produto_por_gtin(conexao, GTIN, "ARROZ TIPO 1 5KG")

    assert _campo(conexao, produto_id, "descricao_normalizada") is None
    assert _campo(conexao, produto_id, "emit_cnpj") is None


# --- C2.4 -------------------------------------------------------------------
def test_descricao_exemplo_guarda_o_texto_cru(conexao):
    """Crua, e nao normalizada: este campo e so para leitura humana."""
    produto_id = resolver_produto_por_gtin(conexao, GTIN, "ARROZ Tipo 1 - 5KG")

    assert _campo(conexao, produto_id, "descricao_exemplo") == "ARROZ Tipo 1 - 5KG"


# --- C2.5 -------------------------------------------------------------------
def test_o_mesmo_gtin_e_o_mesmo_produto_com_outra_descricao(conexao):
    """🔴 O casamento cross-loja do §3, e a razao de o GTIN ser confiavel.

    Duas lojas escrevem o `xProd` do seu jeito e vendem o mesmo produto. O
    codigo de barras e global: a segunda chamada tem de encontrar a linha da
    primeira, nao criar outra.
    """
    primeiro = resolver_produto_por_gtin(conexao, GTIN, "ARROZ TIPO 1 5KG")
    segundo = resolver_produto_por_gtin(conexao, GTIN, "ARR T1 5KG PCT")

    assert segundo == primeiro
    assert _quantas_linhas(conexao) == 1


# --- C2.6 -------------------------------------------------------------------
def test_gtins_diferentes_sao_produtos_diferentes(conexao):
    primeiro = resolver_produto_por_gtin(conexao, GTIN, "ARROZ TIPO 1 5KG")
    segundo = resolver_produto_por_gtin(conexao, OUTRO_GTIN, "FEIJAO CARIOCA 1KG")

    assert segundo != primeiro
    assert _quantas_linhas(conexao) == 2


# --- C2.7 -------------------------------------------------------------------
def test_os_carimbos_sao_gravados_e_a_categoria_fica_nula(conexao):
    """⛔ Categoria nao e desta story: `categoria_id` nasce NULL e fica."""
    produto_id = resolver_produto_por_gtin(conexao, GTIN, "ARROZ TIPO 1 5KG")

    assert _campo(conexao, produto_id, "criado_em") is not None
    assert _campo(conexao, produto_id, "atualizado_em") is not None
    assert _campo(conexao, produto_id, "categoria_id") is None

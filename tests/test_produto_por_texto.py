"""Testes de `resolver_produto_por_texto` — contrato da story 008, tarefa 3.

Escritos ANTES da implementacao (passo 2 do loop) e congelados por commit. O
modelo local recebe este arquivo como LEITURA (`--read`), nunca como editavel.

Criterios e o porque de cada um: `specs/008-identidade-produto/spec.md` §4, C3.

🔴 `test_o_mesmo_texto_em_lojas_diferentes...` e o requisito da story: a spec 02
§3 so aceita casamento entre lojas por GTIN.

⚠️ As colunas sao lidas PELO NOME, nunca a linha inteira — risco R1 do recorte.
"""

import pytest

from nfe_parser.banco import abrir_banco
from nfe_parser.produtos import normalizar_descricao, resolver_produto_por_texto

CNPJ = "12345678000199"
OUTRO_CNPJ = "98765432000111"
DH = "2026-01-02T10:00:00-03:00"


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


# --- C3.1 -------------------------------------------------------------------
def test_descricao_inedita_cria_produto_de_identidade_texto(conexao):
    produto_id = resolver_produto_por_texto(conexao, "ARROZ TIPO 1 - 5KG", CNPJ)

    assert isinstance(produto_id, int)
    assert _campo(conexao, produto_id, "identidade_origem") == "texto"
    assert _campo(conexao, produto_id, "gtin") is None


# --- C3.2 -------------------------------------------------------------------
def test_grava_a_chave_normalizada_o_cnpj_e_a_descricao_crua(conexao):
    """A esperada sai da propria funcao: escrever a string a mao amarraria este
    modulo ao formato da tarefa 1, que tem modulo proprio (risco R4)."""
    crua = "ARROZ Tipo 1 - 5KG"
    produto_id = resolver_produto_por_texto(conexao, crua, CNPJ)

    assert _campo(conexao, produto_id, "descricao_normalizada") == normalizar_descricao(crua)
    assert _campo(conexao, produto_id, "emit_cnpj") == CNPJ
    assert _campo(conexao, produto_id, "descricao_exemplo") == crua


# --- C3.3 -------------------------------------------------------------------
def test_o_mesmo_texto_em_lojas_diferentes_sao_produtos_distintos(conexao):
    """🔴 A honestidade do §3, e o criterio que define esta story.

    Cada loja escreve `xProd` do seu jeito. Casar por descricao entre lojas
    misturaria produtos diferentes no historico de preco, sem sintoma nenhum.
    """
    loja_a = resolver_produto_por_texto(conexao, "ARROZ TIPO 1 - 5KG", CNPJ)
    loja_b = resolver_produto_por_texto(conexao, "ARROZ TIPO 1 - 5KG", OUTRO_CNPJ)

    assert loja_a != loja_b
    assert _quantas_linhas(conexao) == 2


# --- C3.4 -------------------------------------------------------------------
def test_variacoes_de_escrita_na_mesma_loja_casam_no_mesmo_produto(conexao):
    """E para isto que a normalizacao existe: caixa, acento e pontuacao nao
    podem virar tres produtos."""
    primeiro = resolver_produto_por_texto(conexao, "Açúcar Mascavo 1Kg", CNPJ)
    segundo = resolver_produto_por_texto(conexao, "ACUCAR MASCAVO 1KG", CNPJ)
    terceiro = resolver_produto_por_texto(conexao, "  açúcar  mascavo - 1kg ", CNPJ)

    assert segundo == primeiro
    assert terceiro == primeiro
    assert _quantas_linhas(conexao) == 1


# --- C3.5 -------------------------------------------------------------------
def test_chamada_repetida_identica_nao_cria_linha_nova(conexao):
    primeiro = resolver_produto_por_texto(conexao, "FEIJAO CARIOCA 1KG", CNPJ)
    segundo = resolver_produto_por_texto(conexao, "FEIJAO CARIOCA 1KG", CNPJ)

    assert segundo == primeiro
    assert _quantas_linhas(conexao) == 1


# --- C3.6 -------------------------------------------------------------------
def test_produto_que_tem_gtin_nunca_e_devolvido_pela_busca_por_texto(conexao):
    """🔴 O teste do `gtin IS NULL` no SELECT, e ele precisa deste preparo.

    A linha entra por SQL direto com gtin E par de texto preenchidos. Nenhuma
    funcao desta story cria isso (C2.3), mas o esquema permite. Sem o preparo o
    teste passaria por acidente, com a normalizada NULL na linha de GTIN.
    """
    conexao.execute(
        "INSERT INTO produtos (identidade_origem, gtin, descricao_normalizada,"
        " emit_cnpj, criado_em, atualizado_em) VALUES (?, ?, ?, ?, ?, ?)",
        ("gtin", "7891234567890", normalizar_descricao("ARROZ TIPO 1 - 5KG"), CNPJ, DH, DH),
    )
    com_gtin = conexao.execute("SELECT id FROM produtos").fetchone()[0]

    por_texto = resolver_produto_por_texto(conexao, "ARROZ TIPO 1 - 5KG", CNPJ)

    assert por_texto != com_gtin
    assert _quantas_linhas(conexao) == 2


# --- C3.7 -------------------------------------------------------------------
def test_os_carimbos_sao_gravados_e_a_categoria_fica_nula(conexao):
    """⛔ Categoria nao e desta story: `categoria_id` nasce NULL e fica."""
    produto_id = resolver_produto_por_texto(conexao, "FEIJAO CARIOCA 1KG", CNPJ)

    assert _campo(conexao, produto_id, "criado_em") is not None
    assert _campo(conexao, produto_id, "atualizado_em") is not None
    assert _campo(conexao, produto_id, "categoria_id") is None

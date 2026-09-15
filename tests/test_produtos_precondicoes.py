"""Precondicoes das duas resolucoes de `produtos.py` — escrito no PASSO 4.

⚠️ Modulo separado de proposito. Os tres `test_normalizar_descricao`,
`test_produto_por_gtin` e `test_produto_por_texto` sao o oraculo congelado antes
da implementacao, e sao a evidencia do que o modelo local tinha de alcancar.
Acrescentar teste dentro deles depois do passo 3 apagaria essa fronteira.

O que se guarda aqui foi encontrado na revisao do passo 4, e a cobertura de 100%
nao o enxergava — as linhas existiam e eram executadas, so que nenhuma chamada
passava por elas com chave vazia.

🔴 O defeito seria MUDO. Em SQL, `WHERE coluna = NULL` nao casa com nada, nem
com outra linha que tenha NULL ali. As duas funcoes procuram antes de inserir,
entao a busca falharia sempre e cada chamada criaria uma linha nova. E os
indices unicos parciais nao pegariam: `ux_produtos_gtin` so cobre
`gtin IS NOT NULL`, e `ux_produtos_texto` indexa um par que, com NULL dentro,
nao colide com outro par igual. A tabela encheria de produtos fantasma sem nada
quebrar.

⭐ Os quatro testes foram validados por mutacao: com o `raise` removido, os
quatro ficam vermelhos. Teste que nunca se viu falhar nao e guarda, e decoracao.
"""

import pytest

from nfe_parser.banco import abrir_banco
from nfe_parser.produtos import resolver_produto_por_gtin, resolver_produto_por_texto

CNPJ = "12345678000199"


@pytest.fixture
def conexao(tmp_path):
    con = abrir_banco(tmp_path / "nfe.db")
    yield con
    con.close()


def _quantas_linhas(con):
    return con.execute("SELECT COUNT(*) FROM produtos").fetchone()[0]


@pytest.mark.parametrize("gtin_vazio", [None, ""])
def test_resolver_por_gtin_recusa_gtin_vazio(conexao, gtin_vazio):
    """Item sem codigo de barras se resolve por texto, nao por aqui."""
    with pytest.raises(ValueError):
        resolver_produto_por_gtin(conexao, gtin_vazio, "ARROZ TIPO 1 5KG")

    assert _quantas_linhas(conexao) == 0


@pytest.mark.parametrize("cnpj_vazio", [None, ""])
def test_resolver_por_texto_recusa_cnpj_vazio(conexao, cnpj_vazio):
    """A chave de texto so identifica um produto DENTRO de uma loja.

    Sem CNPJ ela nao identifica nada, e aceitar isso seria pior que recusar:
    produziria linhas que nunca mais casariam com nada.
    """
    with pytest.raises(ValueError):
        resolver_produto_por_texto(conexao, "ARROZ TIPO 1 - 5KG", cnpj_vazio)

    assert _quantas_linhas(conexao) == 0


def test_as_chaves_validas_continuam_passando(conexao):
    """A guarda recusa o vazio e mais nada — nenhum caminho legitimo fechou."""
    por_gtin = resolver_produto_por_gtin(conexao, "7891234567890", "ARROZ TIPO 1 5KG")
    por_texto = resolver_produto_por_texto(conexao, "FEIJAO CARIOCA 1KG", CNPJ)

    assert por_gtin != por_texto
    assert _quantas_linhas(conexao) == 2

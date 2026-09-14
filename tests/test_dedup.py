"""Testes do dedup idempotente por `chave` — tarefa 2 da story 004-lote-zip-dedup.

Escritos ANTES da implementacao (passo 2 do loop) e congelados por commit. O
modelo local recebe este arquivo como LEITURA (`--read`), nunca como editavel.

⭐ POR QUE ESTE MODULO E SEPARADO DE `test_persistir_nota.py`

Porque "insere" e "nao insere de novo" sao **dois defeitos**, e a regra 2 do
fatiamento manda um pedido por defeito. Juntos, o caminho mais curto para o
modelo e um `INSERT OR REPLACE`: ele passa em C2.1 e C2.2 e **reprova em C2.3**,
porque reescreve a linha inteira. Separados, a tarefa 2 chega com a insercao ja
verde e um problema so na mesa.

Criterios em `specs/004-lote-zip-dedup/spec.md` §3, bloco C2.
"""

from pathlib import Path

import pytest

from nfe_parser.banco import abrir_banco
from nfe_parser.extrator import extrair_nota
from nfe_parser.persistencia import persistir_nota

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def conexao(tmp_path):
    con = abrir_banco(tmp_path / "nfe.db")
    yield con
    con.close()


def _extraido(nome):
    return extrair_nota((FIXTURES / nome).read_text(encoding="utf-8"))


@pytest.fixture
def extraido_1item():
    return _extraido("nfe_55_1item.xml")


def _conta(con, tabela):
    return con.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]


def _retrato(con):
    """Todas as linhas das duas tabelas, em ordem estavel.

    E o retrato que C2.3 compara antes e depois: "o banco fica identico" e uma
    afirmacao sobre os VALORES, nao sobre a contagem.
    """
    notas = con.execute("SELECT * FROM notas ORDER BY chave").fetchall()
    itens = con.execute("SELECT * FROM itens ORDER BY nota_chave, n_item").fetchall()
    return notas, itens


# --- C2.1 -------------------------------------------------------------------
def test_a_segunda_importacao_da_mesma_nota_devolve_duplicada(conexao, extraido_1item):
    assert persistir_nota(conexao, extraido_1item) == "nova"
    assert persistir_nota(conexao, extraido_1item) == "duplicada"


# --- C2.2 -------------------------------------------------------------------
def test_a_segunda_importacao_nao_recontabiliza(conexao, extraido_1item):
    persistir_nota(conexao, extraido_1item)
    persistir_nota(conexao, extraido_1item)

    assert _conta(conexao, "notas") == 1
    assert _conta(conexao, "itens") == 1


def test_a_segunda_importacao_de_uma_nota_de_tres_itens_nao_duplica_os_itens(conexao):
    extraido = _extraido("nfe_55_3itens.xml")

    persistir_nota(conexao, extraido)
    persistir_nota(conexao, extraido)

    assert _conta(conexao, "notas") == 1
    assert _conta(conexao, "itens") == 3


# --- C2.3 -------------------------------------------------------------------
def test_a_segunda_importacao_nao_sobrescreve_a_linha(conexao, extraido_1item):
    """🔒 O teste que separa dedup de `INSERT OR REPLACE`.

    Um `REPLACE` apaga e reinsere: a contagem volta a 1 e os dois testes acima
    passam. O que ele nao consegue e preservar uma alteracao feita entre as duas
    passagens. Marcar a linha e depois reimportar torna a sobrescrita VISIVEL,
    e de forma deterministica — comparar `criado_em` dependeria de o relogio
    ter avancado entre as duas chamadas.
    """
    persistir_nota(conexao, extraido_1item)
    conexao.execute("UPDATE notas SET emit_nome = 'MARCA-DE-AGUA'")
    conexao.execute("UPDATE itens SET descricao = 'MARCA-DE-AGUA'")

    persistir_nota(conexao, extraido_1item)

    assert conexao.execute("SELECT emit_nome FROM notas").fetchone()[0] == "MARCA-DE-AGUA"
    assert conexao.execute("SELECT descricao FROM itens").fetchone()[0] == "MARCA-DE-AGUA"


def test_o_banco_inteiro_fica_identico(conexao, extraido_1item):
    persistir_nota(conexao, extraido_1item)
    antes = _retrato(conexao)

    persistir_nota(conexao, extraido_1item)

    assert _retrato(conexao) == antes


# --- C2.4 -------------------------------------------------------------------
def test_notas_de_chaves_diferentes_convivem(conexao):
    um = _extraido("nfe_55_1item.xml")
    outro = _extraido("nfe_65_1item.xml")
    assert um["nota"]["chave"] != outro["nota"]["chave"]  # premissa do teste, explicita

    assert persistir_nota(conexao, um) == "nova"
    assert persistir_nota(conexao, outro) == "nova"

    assert _conta(conexao, "notas") == 2


def test_o_dedup_olha_a_chave_e_nao_o_modelo(conexao):
    """Duas notas de modelos diferentes nao sao duplicata uma da outra."""
    persistir_nota(conexao, _extraido("nfe_55_1item.xml"))
    persistir_nota(conexao, _extraido("nfe_65_1item.xml"))

    modelos = conexao.execute("SELECT modelo FROM notas ORDER BY modelo").fetchall()
    assert [linha[0] for linha in modelos] == [55, 65]


# --- C2.5 -------------------------------------------------------------------
def test_o_caminho_duplicado_nao_levanta_excecao(conexao, extraido_1item):
    """Sem o dedup, a `PRIMARY KEY` da `notas` levanta `IntegrityError` sozinha.

    Um dedup que se apoia em capturar a excecao passaria aqui, mas o
    `test_a_segunda_importacao_nao_sobrescreve_a_linha` continua valendo: o que
    nao pode e a segunda passagem mexer no que ja estava gravado.
    """
    persistir_nota(conexao, extraido_1item)

    persistir_nota(conexao, extraido_1item)  # se levantar, o teste falha aqui
    persistir_nota(conexao, extraido_1item)  # e uma terceira vez tambem nao pode

    assert _conta(conexao, "notas") == 1

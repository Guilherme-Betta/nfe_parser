"""Testes de `nota_para_json` — tarefa 2 da story 006-saida-json.

Escritos ANTES da implementacao (passo 2 do loop) e congelados por commit. O
modelo local recebe este arquivo como LEITURA (`--read`), nunca como arquivo
editavel.

⭐ ESTE MODULO NAO TESTA OS ITENS. A chave `itens` e a tarefa 3, e mora em
`tests/test_itens_no_json.py`. Aqui a saida ainda tem so os campos da nota.

⭐ POR QUE O BANCO E MONTADO COM `INSERT` CRU, e nao com `extrair_nota` +
`persistir_nota`: a 006 le o banco, entao o que interessa e o ESTADO da tabela,
nao o caminho que o dado percorreu para chegar la. Insercao direta deixa o teste
controlar cada campo -- inclusive o municipio com acento e a nota cancelada, que
nenhum fixture XML produz.

Criterios em `specs/006-saida-json/spec.md` §4, bloco C2.
"""

import json

import pytest

from nfe_parser.banco import abrir_banco
from nfe_parser.serializacao import nota_para_json

CHAVE = "35260499999999000199550010000000011000000017"
CHAVE_CANCELADA = "35260499999999000199550010000000022000000024"
CHAVE_AUSENTE = "35260499999999000199550010000000099000000099"

# ⚠️ O acento aqui e o proprio criterio 6. Nao "conserte" para SAO PAULO.
MUNICIPIO = "São Paulo"

XML_RAW = "<NFe>este texto nao pode aparecer na saida</NFe>"

# A ordem e o conteudo da lista sao o criterio 5: conjunto FECHADO.
CHAVES_DA_NOTA = [
    "chave",
    "modelo",
    "serie",
    "numero",
    "dh_emi",
    "emit_nome",
    "emit_cnpj",
    "emit_municipio",
    "emit_uf",
    "valor_total_centavos",
    "valor_total",
    "forma_pagamento",
    "status",
    "cancelado_em",
]


def _inserir_nota(con, **mudancas):
    """Insere uma nota completa, deixando o teste sobrescrever o que precisar."""
    campos = {
        "chave": CHAVE,
        "modelo": 55,
        "serie": 1,
        "numero": 1,
        "dh_emi": "2026-04-01T10:00:00-03:00",
        "emit_nome": "MERCEARIA EXEMPLO LTDA",
        "emit_cnpj": "99999999000199",
        "emit_municipio": MUNICIPIO,
        "emit_uf": "SP",
        "valor_total": 12345,
        "forma_pagamento": "01",
        "status": "ok",
        "cancelado_em": None,
        "xml_raw": XML_RAW,
        "criado_em": "2026-04-01T10:00:05",
    }
    campos.update(mudancas)
    colunas = ", ".join(campos)
    marcas = ", ".join("?" for _ in campos)
    con.execute(f"INSERT INTO notas ({colunas}) VALUES ({marcas})", tuple(campos.values()))
    return campos


@pytest.fixture
def conexao(tmp_path):
    """Um banco novo por teste, com uma nota 'ok' ja dentro."""
    con = abrir_banco(tmp_path / "nfe.db")
    _inserir_nota(con)
    yield con
    con.close()


# --- C2, criterio 1 ---------------------------------------------------------
def test_devolve_uma_string_que_json_loads_le_de_volta(conexao):
    """⭐ O contrato e STRING, nao `dict`.

    Um `dict` passaria em quase toda assercao deste modulo, entao esta e a unica
    que separa as duas coisas. `json.loads` recusa `dict`, e e isso que garante
    que a serializacao realmente aconteceu.
    """
    saida = nota_para_json(conexao, CHAVE)

    assert isinstance(saida, str)
    assert isinstance(json.loads(saida), dict)


# --- C2, criterio 5 ---------------------------------------------------------
def test_as_chaves_sao_exatamente_estas_e_nesta_ordem(conexao):
    """Conjunto FECHADO: nada inventado, e `xml_raw` de fora.

    `importacao_id` e `criado_em` tambem ficam de fora -- sao escrituracao
    interna do banco, nao fazem parte da nota.
    """
    dados = json.loads(nota_para_json(conexao, CHAVE))

    # ⚠️ PREFIXO, nao igualdade. A tarefa 3 acrescenta a chave `itens` a esta
    # mesma saida (spec §4, C3), entao uma igualdade estrita aqui passaria na
    # tarefa 2 e quebraria na 3 -- foi exatamente o que aconteceu. A igualdade
    # estrita, ja com `itens`, mora em test_itens_no_json.py.
    assert list(dados)[: len(CHAVES_DA_NOTA)] == CHAVES_DA_NOTA
    assert set(dados) - set(CHAVES_DA_NOTA) <= {"itens"}
    assert XML_RAW not in nota_para_json(conexao, CHAVE)


# --- C2, criterio 2 ---------------------------------------------------------
def test_o_dinheiro_sai_nos_dois_campos_e_eles_concordam(conexao):
    """O inteiro e a fonte de verdade; a string e derivada dele na serializacao."""
    dados = json.loads(nota_para_json(conexao, CHAVE))

    assert dados["valor_total_centavos"] == 12345
    assert isinstance(dados["valor_total_centavos"], int)
    assert dados["valor_total"] == "123.45"
    assert isinstance(dados["valor_total"], str)


# --- C2, criterio 3 ---------------------------------------------------------
def test_nota_nao_cancelada_diz_ok_e_cancelado_em_nulo(conexao):
    dados = json.loads(nota_para_json(conexao, CHAVE))

    assert dados["status"] == "ok"
    assert dados["cancelado_em"] is None


def test_nota_cancelada_mostra_o_status_e_a_data(conexao):
    """⭐ Sem isto, a story 005 inteira fica invisivel na unica saida que existe.

    Quem le o JSON nao teria como distinguir uma venda de uma venda cancelada.
    """
    _inserir_nota(
        conexao,
        chave=CHAVE_CANCELADA,
        status="cancelada",
        cancelado_em="2026-04-02T09:30:00-03:00",
    )

    dados = json.loads(nota_para_json(conexao, CHAVE_CANCELADA))

    assert dados["status"] == "cancelada"
    assert dados["cancelado_em"] == "2026-04-02T09:30:00-03:00"


# --- C2, criterio 4 ---------------------------------------------------------
def test_chave_inexistente_devolve_none_e_nao_json_vazio(conexao):
    """⛔ `"{}"` seria o pior desfecho: um JSON valido que mente.

    Quem recebesse `"{}"` acharia que existe uma nota sem nenhum campo. `None`
    diz "nao achei", e quem chama distingue com `if resultado is None`.
    """
    resultado = nota_para_json(conexao, CHAVE_AUSENTE)

    assert resultado is None


# --- C2, criterio 6 ---------------------------------------------------------
def test_o_acento_sobrevive_a_ida_e_a_volta(conexao):
    """`json.dumps` escapa acento POR PADRAO: o default erra este criterio.

    O defeito so aparece em quem abre o arquivo depois -- `"S\\u00e3o Paulo"` e
    JSON valido, e `json.loads` ate o le de volta certo. O que se perde e a
    legibilidade do arquivo, que e metade da razao de existir uma saida em JSON.
    """
    bruto = nota_para_json(conexao, CHAVE)

    assert MUNICIPIO in bruto
    # ⚠️ O `r` NAO e enfeite: numa string Python comum a sequencia de escape
    # JA E o caractere acentuado, entao esta assercao contradiria a de cima e o
    # teste seria IMPOSSIVEL de passar. O que se procura aqui e a sequencia de
    # escape literal, de seis caracteres, dentro do texto do JSON.
    assert r"\u00e3" not in bruto
    assert json.loads(bruto)["emit_municipio"] == MUNICIPIO

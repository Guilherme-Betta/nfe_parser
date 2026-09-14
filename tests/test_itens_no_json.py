"""Testes da chave `itens` — tarefa 3 da story 006-saida-json.

Escritos ANTES da implementacao (passo 2 do loop) e congelados por commit. O
modelo local recebe este arquivo como LEITURA (`--read`), nunca como arquivo
editavel.

⭐ ESTE MODULO E O GUARDA-COSTAS DA TAREFA 2. A tarefa 3 EDITA uma funcao que ja
estava verde, e o risco nomeado no `plan.md` (R5) e ela ser reescrita do zero e
levar junto o que ja funcionava. Por isso o ultimo teste daqui repete as 14
chaves da nota: a regressao aparece neste modulo, nao so no outro.

Criterios em `specs/006-saida-json/spec.md` §4, bloco C3.
"""

import json

import pytest

from nfe_parser.banco import abrir_banco
from nfe_parser.serializacao import nota_para_json

CHAVE = "35260499999999000199550010000000011000000017"
CHAVE_SEM_ITEM = "35260499999999000199550010000000033000000031"
CHAVE_AUSENTE = "35260499999999000199550010000000099000000099"

CHAVES_DO_ITEM = [
    "n_item",
    "descricao",
    "cprod",
    "ncm",
    "gtin",
    "quantidade",
    "unidade",
    "valor_unitario",
    "valor_linha_centavos",
    "valor_linha",
]

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


def _inserir_nota(con, chave=CHAVE):
    campos = {
        "chave": chave,
        "modelo": 55,
        "serie": 1,
        "numero": 1,
        "dh_emi": "2026-04-01T10:00:00-03:00",
        "emit_nome": "MERCEARIA EXEMPLO LTDA",
        "emit_cnpj": "99999999000199",
        "emit_municipio": "São Paulo",
        "emit_uf": "SP",
        "valor_total": 12345,
        "forma_pagamento": "01",
        "status": "ok",
        "cancelado_em": None,
        "xml_raw": "<NFe>este texto nao pode aparecer na saida</NFe>",
        "criado_em": "2026-04-01T10:00:05",
    }
    colunas = ", ".join(campos)
    marcas = ", ".join("?" for _ in campos)
    con.execute(f"INSERT INTO notas ({colunas}) VALUES ({marcas})", tuple(campos.values()))


def _inserir_item(con, n_item, descricao, valor_linha, chave=CHAVE, gtin=None):
    campos = {
        "nota_chave": chave,
        "n_item": n_item,
        "descricao": descricao,
        "cprod": f"COD{n_item}",
        "ncm": "21069090",
        "gtin": gtin,
        "quantidade": "1.5000",
        "unidade": "UN",
        "valor_unitario": "5.3600000000",
        "valor_linha": valor_linha,
        "criado_em": "2026-04-01T10:00:05",
    }
    colunas = ", ".join(campos)
    marcas = ", ".join("?" for _ in campos)
    con.execute(f"INSERT INTO itens ({colunas}) VALUES ({marcas})", tuple(campos.values()))


@pytest.fixture
def conexao(tmp_path):
    """Uma nota com TRES itens, inseridos FORA de ordem de proposito."""
    con = abrir_banco(tmp_path / "nfe.db")
    _inserir_nota(con)
    _inserir_item(con, 3, "CAFE 500G", 2000)
    _inserir_item(con, 1, "ARROZ 5KG", 804, gtin="7891234567895")
    _inserir_item(con, 2, "FEIJAO 1KG", 950)
    yield con
    con.close()


# --- C3 ---------------------------------------------------------------------
def test_a_saida_ganha_a_chave_itens_como_lista(conexao):
    dados = json.loads(nota_para_json(conexao, CHAVE))

    assert isinstance(dados["itens"], list)
    assert len(dados["itens"]) == 3


def test_as_chaves_de_cada_item_sao_exatamente_estas(conexao):
    """⛔ `id` e `nota_chave` de fora: chave artificial do SQLite e redundancia."""
    dados = json.loads(nota_para_json(conexao, CHAVE))

    for item in dados["itens"]:
        assert list(item) == CHAVES_DO_ITEM


def test_os_itens_saem_ordenados_por_n_item(conexao):
    """O fixture insere 3, 1, 2. Sem `ORDER BY`, o SQLite nao garante ordem.

    E o tipo de defeito que passa despercebido: a ordem de insercao COINCIDE com
    a ordenada na maioria dos bancos pequenos, entao so um fixture embaralhado
    de proposito reprova a implementacao sem `ORDER BY`.
    """
    dados = json.loads(nota_para_json(conexao, CHAVE))

    assert [item["n_item"] for item in dados["itens"]] == [1, 2, 3]
    assert [item["descricao"] for item in dados["itens"]] == [
        "ARROZ 5KG",
        "FEIJAO 1KG",
        "CAFE 500G",
    ]


def test_o_dinheiro_do_item_sai_nos_dois_campos(conexao):
    """Mesma regra da nota: o inteiro e a fonte, a string e derivada dele."""
    primeiro = json.loads(nota_para_json(conexao, CHAVE))["itens"][0]

    assert primeiro["valor_linha_centavos"] == 804
    assert isinstance(primeiro["valor_linha_centavos"], int)
    assert primeiro["valor_linha"] == "8.04"
    assert isinstance(primeiro["valor_linha"], str)


def test_nota_sem_item_devolve_lista_vazia_e_nao_levanta(conexao):
    """`[]` e nao `null`: quem consome itera sem precisar checar antes."""
    _inserir_nota(conexao, chave=CHAVE_SEM_ITEM)

    dados = json.loads(nota_para_json(conexao, CHAVE_SEM_ITEM))

    assert dados["itens"] == []


def test_chave_inexistente_continua_devolvendo_none(conexao):
    """A tarefa 3 nao pode quebrar o criterio 4 buscando item de nota que nao ha."""
    assert nota_para_json(conexao, CHAVE_AUSENTE) is None


# --- regressao da tarefa 2 (risco R5 do plan.md) -----------------------------
def test_as_14_chaves_da_nota_continuam_e_itens_e_a_ultima(conexao):
    dados = json.loads(nota_para_json(conexao, CHAVE))

    assert list(dados) == CHAVES_DA_NOTA + ["itens"]
    assert dados["valor_total_centavos"] == 12345
    assert dados["valor_total"] == "123.45"
    assert dados["emit_municipio"] == "São Paulo"

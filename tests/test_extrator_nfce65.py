"""Testes da NFC-e modelo 65 — tarefa 1 da story 003.

Escritos ANTES da implementacao (passo 2 do loop) e congelados por commit. O
modelo local recebe este arquivo como LEITURA (`--read`), nunca como arquivo
editavel. Se ele puder editar o oraculo, ele conserta o oraculo em vez do codigo.

Criterio C1 de `specs/003-nfce-65-multi-item/spec.md` §3, assercoes 1.1 a 1.9.

O que este modulo NAO cobre, de proposito: contagem de itens (C2, em
`test_extrator_multi_item.py`) e anotacao de tipo (C4, em `test_anotacoes.py`).
Cada sub-tarefa do modelo local precisa de um oraculo que fale so dela.
"""

from pathlib import Path

import pytest

from nfe_parser.extrator import extrair_nota

FIXTURES = Path(__file__).parent / "fixtures"
FIXTURE_65 = FIXTURES / "nfe_65_1item.xml"
FIXTURE_55 = FIXTURES / "nfe_55_1item.xml"

# Os conjuntos de chaves da §2 da spec, escritos por extenso de proposito.
# Comparar com um `set` literal e o que torna "mesmos campos da 55" uma
# assercao: um dicionario que ganha UMA chave a mais so na 65 quebraria o
# INSERT do banco la na frente, e passaria despercebido numa checagem que so
# olhasse as chaves que ela espera encontrar.
CHAVES_NOTA = {
    "chave",
    "modelo",
    "serie",
    "numero",
    "dh_emi",
    "emit_nome",
    "emit_cnpj",
    "emit_municipio",
    "emit_uf",
    "valor_total",
    "forma_pagamento",
    "xml_raw",
}

CHAVES_ITEM = {
    "n_item",
    "descricao",
    "cprod",
    "ncm",
    "gtin",
    "quantidade",
    "valor_unitario",
    "valor_linha",
    "unidade",
}


@pytest.fixture
def resultado():
    return extrair_nota(FIXTURE_65.read_text(encoding="utf-8"))


@pytest.fixture
def nota(resultado):
    return resultado["nota"]


# --- C1.1 --------------------------------------------------------------------

def test_1_1_devolve_dicionario_com_nota_e_itens(resultado):
    assert isinstance(resultado, dict)
    assert set(resultado.keys()) == {"nota", "itens"}


# --- C1.2 e C1.3 -------------------------------------------------------------

def test_1_2_nota_tem_exatamente_as_chaves_do_ddl(nota):
    assert set(nota.keys()) == CHAVES_NOTA


def test_1_3_item_tem_exatamente_as_chaves_do_ddl(resultado):
    assert len(resultado["itens"]) == 1
    assert set(resultado["itens"][0].keys()) == CHAVES_ITEM


# --- C1.4 --------------------------------------------------------------------

def test_1_4_modelo_e_o_int_65(nota):
    # `inf.ide.mod` chega como enum Tmod.VALUE_65. str() dele devolveria
    # "Tmod.VALUE_65"; so `.value` da "65".
    assert nota["modelo"] == 65
    assert isinstance(nota["modelo"], int)
    assert not isinstance(nota["modelo"], bool)


# --- C1.5 e C1.6 -------------------------------------------------------------

def test_1_5_chave_tem_44_digitos_sem_o_prefixo_nfe(nota):
    chave = nota["chave"]
    assert isinstance(chave, str)
    assert len(chave) == 44
    assert chave.isdigit()
    assert not chave.startswith("NFe")


def test_1_6_a_chave_carrega_o_modelo_65(nota):
    # Posicoes 21-22 da chave (indices 20 e 21) sao o modelo. Se o campo disser
    # 65 e a chave disser 55, a fixture esta incoerente consigo mesma — e o
    # teste tem que reprovar, nao acomodar.
    assert nota["chave"][20:22] == "65"


# --- C1.7 --------------------------------------------------------------------

def test_1_7_valor_total_e_int_em_centavos(nota):
    # 12.34 e armadilha de float: int(float("12.34") * 100) == 1233.
    assert nota["valor_total"] == 1234
    assert isinstance(nota["valor_total"], int)


def test_1_7_dh_emi_e_a_string_exata_do_xml(nota):
    # Sem passar por datetime e voltar: qualquer ida e volta perde o offset ou
    # troca o separador.
    assert nota["dh_emi"] == "2026-05-20T19:05:00-03:00"
    assert isinstance(nota["dh_emi"], str)


# --- C1.8 --------------------------------------------------------------------

def test_1_8_uf_e_string_nao_enum(nota):
    # `enderEmit.UF` chega como TufEmi.SP.
    assert nota["emit_uf"] == "SP"
    assert isinstance(nota["emit_uf"], str)


# --- os demais campos da 65, para "mesmos campos" nao ficar so no conjunto ----

def test_demais_campos_da_nota_65(nota):
    assert nota["serie"] == 1
    assert nota["numero"] == 2
    assert nota["emit_nome"] == "MERCEARIA EXEMPLO LTDA"
    assert nota["emit_cnpj"] == "99999999000199"
    assert nota["emit_municipio"] == "SAO PAULO"
    assert nota["forma_pagamento"] == "01"


def test_item_da_65_com_gtin_presente(resultado):
    item = resultado["itens"][0]
    assert item["n_item"] == 1
    assert item["descricao"] == "ACHOCOLATADO EM PO 400G"
    assert item["cprod"] == "SKU-0002"
    assert item["ncm"] == "18069000"
    # Contraste deliberado com a nfe_55_1item.xml, que tem "SEM GTIN": aqui o
    # GTIN existe e NAO pode virar None.
    assert item["gtin"] == "7891000100103"
    assert item["unidade"] == "UN"
    # Quantidade e valor unitario saem como a string EXATA do XML, com os zeros
    # a direita. Passar por float ou Decimal e voltar transformaria "2.0000" em
    # "2.0" e "6.1700000000" em "6.17".
    assert item["quantidade"] == "2.0000"
    assert item["valor_unitario"] == "6.1700000000"
    assert item["valor_linha"] == 1234


def test_xml_raw_e_o_texto_que_entrou(nota):
    assert nota["xml_raw"] == FIXTURE_65.read_text(encoding="utf-8")


# --- C1.9 --------------------------------------------------------------------

def test_1_9_suportar_a_65_nao_custa_a_55():
    """Regressao. O oraculo completo da 55 sao os modulos da story 002, que
    continuam rodando sem alteracao; esta assercao existe para que a quebra
    apareca JUNTO das da 65, e nao num modulo distante que o modelo local nem
    recebeu no `--read` da tarefa 1."""
    r55 = extrair_nota(FIXTURE_55.read_text(encoding="utf-8"))
    assert set(r55["nota"].keys()) == CHAVES_NOTA
    assert r55["nota"]["modelo"] == 55
    assert r55["nota"]["valor_total"] == 804

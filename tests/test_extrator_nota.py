"""Testes do bloco "nota" de `extrair_nota` — tarefa 2a da story 002.

Escritos ANTES da implementacao (passo 2 do loop) e congelados por commit. O
modelo local recebe este arquivo como LEITURA (`--read`), nunca como arquivo
editavel.

⭐ POR QUE ESTE ARQUIVO E SEPARADO

A tarefa 2 original mandou **8,9k tokens** contra um `num_ctx` de 8192: o
contexto foi truncado em silencio, o modelo nao chegou a ver a tabela da API do
`nfelib` e inventou nomes que nao existem. Medido em 2026-09-12.

O conserto foi fatiar de novo. Mas fatiar a tarefa obriga a fatiar o modulo de
teste, porque um `import` de funcao inexistente quebra a COLETA do modulo
inteiro e impede a sub-tarefa de ficar verde. Ver `test_para_centavos.py`.

Aqui: so o bloco `"nota"` e o caminho de erro. Os itens estao em
`test_extrator_itens.py`.

Criterios em `specs/002-extrair-nfe-55/spec.md` §5 (1-9) e §6 (24-26).
"""

from pathlib import Path

import pytest

from nfe_parser.extrator import extrair_nota

FIXTURE = Path(__file__).parent / "fixtures" / "nfe_55_1item.xml"

CHAVE = "35260499999999000199550010000000011000000017"
DH_EMI = "2026-04-15T10:30:00-03:00"


@pytest.fixture
def xml_texto():
    """O texto cru da fixture, que e tambem o que deve voltar em xml_raw."""
    return FIXTURE.read_text(encoding="utf-8")


@pytest.fixture
def nota(xml_texto):
    return extrair_nota(xml_texto)["nota"]


def test_extrair_nota_01_chave_sem_prefixo_e_com_44_digitos(nota):
    """inf.Id vem como "NFe3526...". A chave sao os 44 digitos depois do prefixo."""
    assert nota["chave"] == CHAVE
    assert len(nota["chave"]) == 44
    assert nota["chave"].isdigit()


def test_extrair_nota_02_modelo_e_inteiro_55(nota):
    """ide.mod e um enum (Tmod.VALUE_55), nao uma string. A coluna e INTEGER."""
    assert nota["modelo"] == 55
    assert type(nota["modelo"]) is int


def test_extrair_nota_03_serie_e_numero_sao_inteiros(nota):
    assert nota["serie"] == 1
    assert nota["numero"] == 1
    assert type(nota["serie"]) is int
    assert type(nota["numero"]) is int


def test_extrair_nota_04_dh_emi_igual_ao_xml_com_offset(nota):
    """Ja chega ISO-8601 com offset. Converter para datetime e voltar perde o offset."""
    assert nota["dh_emi"] == DH_EMI


def test_extrair_nota_05_emitente_completo(nota):
    assert nota["emit_nome"] == "MERCEARIA EXEMPLO LTDA"
    assert nota["emit_cnpj"] == "99999999000199"
    assert nota["emit_municipio"] == "SAO PAULO"


def test_extrair_nota_06_emit_uf_e_string_nao_enum(nota):
    """enderEmit.UF e TufEmi.SP. str() dele devolveria "TufEmi.SP"."""
    assert nota["emit_uf"] == "SP"
    assert type(nota["emit_uf"]) is str


def test_extrair_nota_07_valor_total_e_804_nao_803(nota):
    """vNF = "8.04". int(float("8.04") * 100) devolve 803."""
    assert nota["valor_total"] == 804
    assert type(nota["valor_total"]) is int


def test_extrair_nota_08_forma_pagamento_vem_do_tpag(nota):
    """inf.pag e objeto, nao lista; detPag e que e lista."""
    assert nota["forma_pagamento"] == "01"


def test_extrair_nota_09_xml_raw_e_o_texto_recebido_intacto(nota, xml_texto):
    assert nota["xml_raw"] == xml_texto


# ---------------------------------------------------------------------------
# Caminho de erro (§6) — item 1 da rubrica de qualidade
# ---------------------------------------------------------------------------


def test_extrair_nota_24_xml_corrompido_levanta_value_error():
    with pytest.raises(ValueError):
        extrair_nota("<nfeProc><naofecha>")


def test_extrair_nota_25_xml_valido_que_nao_e_nfe_levanta_value_error():
    with pytest.raises(ValueError):
        extrair_nota('<?xml version="1.0"?><pedido><item>x</item></pedido>')


def test_extrair_nota_26_string_vazia_levanta_value_error():
    with pytest.raises(ValueError):
        extrair_nota("")

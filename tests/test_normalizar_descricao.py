"""Testes de `normalizar_descricao` — contrato da story 008, tarefa 1.

Escritos ANTES da implementacao (passo 2 do loop) e congelados por commit. O
modelo local recebe este arquivo como LEITURA (`--read`), nunca como editavel.

Criterios e o porque de cada um: `specs/008-identidade-produto/spec.md` §4, C1.

🔴 NENHUM teste fixa a string inteira de uma descricao acentuada — remedio do
risco R4 do recorte. O que se afirma sao PROPRIEDADES da saida e PRESERVACAO do
conteudo, e as duas juntas: so a primeira seria satisfeita por uma funcao que
devolve `""` sempre.

⚠️ Zero barra invertida neste arquivo, de proposito (Achado Q): acentuado entra
como o caractere literal, e a forma NFD sai de `unicodedata.normalize`.
"""

import unicodedata

import pytest

from nfe_parser.produtos import normalizar_descricao

PERMITIDOS_NA_SAIDA = set("abcdefghijklmnopqrstuvwxyz0123456789 ")


# --- C1.1 + C1.2 ------------------------------------------------------------
@pytest.mark.parametrize(
    "descricao",
    [
        "ARROZ TIPO 1 - 5KG",
        "Pão de Açúcar",
        "COCA-COLA 2L",
        "Refrig. 1,5L",
        "1º PRECO",
        "ø10mm",
        "µg VITAMINA",
    ],
)
def test_saida_so_tem_letra_minuscula_digito_e_espaco(descricao):
    """Os tres ultimos casos sao o risco R1: `str.isalnum()` e Unicode-aware e
    aceita `º`, `ø` e `µ`, que tambem nao decompoem em NFD. Com um filtro feito
    de `isalnum()` eles atravessam e a saida deixa de ser ASCII."""
    saida = normalizar_descricao(descricao)

    assert set(saida) <= PERMITIDOS_NA_SAIDA


# --- C1.3 -------------------------------------------------------------------
def test_acento_vira_a_letra_base_e_nao_some():
    """O token acentuado vira o sem acento. ⛔ Nada se afirma sobre o resto."""
    assert "acucar" in normalizar_descricao("Açúcar Mascavo").split()
    assert "pao" in normalizar_descricao("PÃO FRANCÊS").split()


# --- C1.4 -------------------------------------------------------------------
def test_pontuacao_vira_espaco_e_nao_junta_palavras():
    """Apagar a pontuacao faria `COCA-COLA` virar `cocacola`, um token que nao
    existe em descricao nenhuma. Virar espaco no maximo parte o que estava
    junto; apagar inventa palavra nova."""
    tokens = normalizar_descricao("COCA-COLA 2L").split()

    assert "coca" in tokens
    assert "cola" in tokens


# --- C1.5 -------------------------------------------------------------------
def test_espacos_colapsam_e_as_bordas_somem():
    saida = normalizar_descricao("   ARROZ   -   TIPO 1   ")

    assert "  " not in saida
    assert saida == saida.strip()
    assert saida.split() == ["arroz", "tipo", "1"]


# --- C1.6 -------------------------------------------------------------------
def test_numero_e_unidade_atravessam_como_texto():
    """⛔ Nenhuma conversao de unidade: a normalizada e chave de igualdade, nao
    um valor a ser lido."""
    tokens = normalizar_descricao("ARROZ TIPO 1 - 5KG").split()

    assert "1" in tokens
    assert "5kg" in tokens


# --- C1.7 -------------------------------------------------------------------
def test_forma_composta_e_decomposta_convergem():
    """O mesmo texto chega do XML em NFC ou NFD — codepoints diferentes para o
    Python. Sem isto, o emissor da nota decidiria se o produto e um ou dois."""
    composta = "Açúcar"
    decomposta = unicodedata.normalize("NFD", composta)

    assert composta != decomposta
    assert normalizar_descricao(composta) == normalizar_descricao(decomposta)


# --- C1.8 -------------------------------------------------------------------
@pytest.mark.parametrize("descricao", ["", "   ", "!!!", " - . - "])
def test_entrada_sem_conteudo_util_vira_string_vazia(descricao):
    """A funcao e total: nao levanta excecao, nao devolve None. ⚠️ Colapsar tudo
    na chave vazia e limitacao conhecida e aceita — ver spec §5."""
    assert normalizar_descricao(descricao) == ""

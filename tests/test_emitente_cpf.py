"""NF-e de emitente com CPF: o CPF faz o papel de "loja" — spec 01 §2 e §6.3 item 1.

Decisao do Gui de 2026-10-16 (opcao c). Antes, item sem GTIN numa nota dessas
derrubava o lote INTEIRO: a identidade de produto por texto exige o documento da
loja, e o extrator so lia o CNPJ.

🔴 CPF de mentira — repositorio publico. As fixtures ja tem `99999999999` no
DESTINATARIO; um numero diferente no emitente garante que o teste le o lugar
certo, e nao o primeiro CPF que aparecer no XML.
"""

from nfe_parser.extrator import extrair_nota
from nfe_parser.importador import importar
from tests.apoio import CNPJ_FIXTURE, TOMATE, chave, texto, variante, zip_de

CPF_EMITENTE = "88888888888"


def _nota_de_cpf(n):
    """A nota de 1 item (o TOMATE, que e SEM GTIN) emitida por um CPF."""
    xml = variante("nfe_55_1item.xml", chave(n), cpf_emitente=CPF_EMITENTE)
    assert f"<CPF>{CPF_EMITENTE}</CPF>" in xml, "a fixture mudou; o teste depende do emitente dela"
    return xml


def _importar(conexao, tmp_path, membros):
    lote = tmp_path / "lote.zip"
    lote.write_bytes(zip_de(membros))
    return importar(conexao, lote)


def test_extrator_le_o_cpf_do_emitente_no_lugar_do_cnpj():
    nota = extrair_nota(_nota_de_cpf(1))["nota"]

    assert nota["emit_cnpj"] == CPF_EMITENTE


def test_lote_com_nota_de_cpf_e_item_sem_gtin_importa_inteiro(conexao, tmp_path):
    _importar(conexao, tmp_path, {"a.xml": texto("nfe_65_1item.xml"), "b_cpf.xml": _nota_de_cpf(1)})

    resultados = conexao.execute("SELECT resultado FROM importacao_arquivos").fetchall()
    assert sorted(r for (r,) in resultados) == ["nova", "nova"]
    tomate = conexao.execute(
        "SELECT identidade_origem, emit_cnpj FROM produtos WHERE descricao_exemplo = ?", (TOMATE,)
    ).fetchall()
    assert tomate == [("texto", CPF_EMITENTE)]


def test_tomate_do_cpf_e_da_loja_de_cnpj_sao_produtos_diferentes(conexao, tmp_path):
    """Sem GTIN, a identidade vale DENTRO da loja (spec 02 §3): o emitente de CPF
    e outra loja, e o tomate dele nao casa com o da mercearia de CNPJ."""
    _importar(
        conexao,
        tmp_path,
        {"cnpj.xml": texto("nfe_55_1item.xml"), "cpf.xml": _nota_de_cpf(1)},
    )

    lojas = conexao.execute(
        "SELECT emit_cnpj FROM produtos WHERE descricao_exemplo = ? ORDER BY emit_cnpj", (TOMATE,)
    ).fetchall()
    assert lojas == [(CPF_EMITENTE,), (CNPJ_FIXTURE,)]

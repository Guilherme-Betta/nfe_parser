"""Apoio dos testes da camada web (spec 03): XMLs, zips, upload, LLM espiao.

⭐ As notas novas nascem das fixtures anonimizadas por substituicao de texto:
trocar a chave (que aparece no `Id` e no `chNFe`), o CNPJ, o NCM ou a data. Nada
de XML novo inventado do zero, e nada sai de `tmp_path` — repositorio publico.
"""

import io
import zipfile
from pathlib import Path

FIXTURES = Path(__file__).parent.parent / "fixtures"
NS = "http://www.portalfiscal.inf.br/nfe"

# nfe_55_1item: 2026-04, TOMATE (sem GTIN, NCM 07 → vegetais)
CHAVE_1ITEM = "35260499999999000199550010000000011000000017"
# nfe_65_1item: 2026-05, ACHOCOLATADO (GTIN, NCM 18 → mercado-mercearia)
CHAVE_65 = "35260499999999000199650010000000021000000025"
# nfe_55_3itens: 2026-06, ACHOCOLATADO + TOMATE + ARROZ
CHAVE_3ITENS = "35260499999999000199550010000000031000000038"
CNPJ_FIXTURE = "99999999000199"

TOMATE = "TOMATE ITALIANO KG"
ACHOCOLATADO = "ACHOCOLATADO EM PO 400G"

CFE_SAT = f'<CFe xmlns="{NS}"><infCFe><ide><mod>59</mod></ide></infCFe></CFe>'
XML_QUEBRADO = "<nfeProc><quebrado"


def texto(nome):
    return (FIXTURES / nome).read_text(encoding="utf-8")


def chave(n):
    """Uma chave fake de 44 digitos, distinta para cada `n`.

    ⚠️ Serie `002`, e nao a `001` das fixtures: com `001`, `chave(1)` seria
    identica a `CHAVE_1ITEM` e a "nota nova" seria uma duplicada.
    """
    return f"3526049999999900019955002{n:09d}1{n:08d}7"


def variante(nome, chave_nova, *, cnpj=None, ncm=None, dh_emi=None):
    """A fixture `nome` com outra chave e, opcionalmente, outro CNPJ, NCM ou data.

    `ncm` e um par `(antigo, novo)`; `dh_emi` substitui a data inteira.
    """
    xml = texto(nome)
    chave_antiga = xml.split('Id="NFe', 1)[1][:44]
    xml = xml.replace(chave_antiga, chave_nova)
    if cnpj:
        xml = xml.replace(f"<CNPJ>{CNPJ_FIXTURE}</CNPJ>", f"<CNPJ>{cnpj}</CNPJ>")
    if ncm:
        xml = xml.replace(f"<NCM>{ncm[0]}</NCM>", f"<NCM>{ncm[1]}</NCM>")
    if dh_emi:
        antiga = xml.split("<dhEmi>", 1)[1].split("</dhEmi>", 1)[0]
        xml = xml.replace(f"<dhEmi>{antiga}</dhEmi>", f"<dhEmi>{dh_emi}</dhEmi>")
    return xml


def evento(chave_nota):
    return (
        f'<procEventoNFe xmlns="{NS}" versao="1.00"><evento versao="1.00"><infEvento>'
        f"<chNFe>{chave_nota}</chNFe><dhEvento>2026-07-01T10:00:00-03:00</dhEvento>"
        "<tpEvento>110111</tpEvento></infEvento></evento></procEventoNFe>"
    )


def zip_de(membros):
    """Bytes de um `.zip` montado em memoria. `membros` = {nome_interno: texto}."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as arquivo_zip:
        for interno, conteudo in membros.items():
            arquivo_zip.writestr(interno, conteudo)
    return buffer.getvalue()


def enviar(cliente, nome, conteudo):
    """POST do upload na API. `conteudo` pode ser texto (XML) ou bytes (zip)."""
    if isinstance(conteudo, str):
        conteudo = conteudo.encode("utf-8")
    return cliente.post("/api/importacoes", files={"arquivo": (nome, conteudo)})


def produto(conexao, descricao_exemplo):
    """`(id, slug da categoria, origem)` do produto, pela descricao de exemplo."""
    return conexao.execute(
        "SELECT p.id, c.slug, p.origem FROM produtos p"
        " LEFT JOIN categorias c ON c.id = p.categoria_id WHERE p.descricao_exemplo = ?",
        (descricao_exemplo,),
    ).fetchone()


class LlmEspiao:
    """Um `llm(descricao, slugs)` que registra cada chamada e devolve `resposta`."""

    def __init__(self, resposta=None):
        self.resposta = resposta
        self.chamadas = []

    def __call__(self, descricao, slugs):
        self.chamadas.append(descricao)
        return self.resposta

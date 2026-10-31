"""Testes do diagnostico da importacao — story 013, tarefa 3.

🔴 O PORQUE de cada criterio mora em `specs/013-integracao/spec.md` §4 (bloco C3)
e §3 (decisoes D4, D10, D11). ⛔ Nao o repita aqui: aquela spec NAO e enviada ao
modelo local, e este arquivo e.

Congelados por commit ANTES da implementacao; o modelo local le (`--read`).

⭐ A divida `c` e a mais seria do recorte, e o que ela produz nao e um erro: e um
DIAGNOSTICO FALSO. Com a gravacao dentro do `try`, qualquer falha de persistencia
sairia registrada como "XML invalido" — e um lote inteiro apontaria para o lugar
errado. Por isso os oraculos daqui olham o `resultado` gravado, e nao so o
desfecho da chamada.

🔴 OS `.zip` NASCEM EM `tmp_path` E NUNCA SAO COMMITADOS — repositorio publico.
"""

import zipfile
from pathlib import Path

import pytest

from nfe_parser import importador
from nfe_parser.banco import abrir_banco
from nfe_parser.importador import importar
from nfe_parser.tipo_xml import tipo_do_xml

FIXTURES = Path(__file__).parent / "fixtures"

NS = "http://www.portalfiscal.inf.br/nfe"

CHAVE_1ITEM = "35260499999999000199550010000000011000000017"

XML_QUE_NAO_ABRE = "<isto nao e xml"

# ⚠️ Sem namespace de proposito: o `tipo_do_xml` le a tag crua, acha o `mod`
# 55 e responde "nfe" — mas o parser do `nfelib` recusa. E o unico jeito de
# chegar ao `except ValueError` de `_processar_arquivo`, e por isso o C3.8
# existe: sem ele aquele ramo nao e exercitado por teste nenhum da suite.
NFE_QUE_CLASSIFICA_MAS_NAO_ABRE = (
    "<nfeProc><NFe><infNFe><ide><mod>55</mod></ide></infNFe></NFe></nfeProc>"
)


def _evento(chave=CHAVE_1ITEM):
    return (
        f'<procEventoNFe xmlns="{NS}" versao="1.00"><evento versao="1.00"><infEvento>'
        f"<chNFe>{chave}</chNFe><dhEvento>2026-04-10T10:00:00-03:00</dhEvento>"
        "<tpEvento>110111</tpEvento></infEvento></evento></procEventoNFe>"
    )


def _texto(nome):
    return (FIXTURES / nome).read_text(encoding="utf-8")


def _zip(tmp_path, membros, nome="lote.zip"):
    """Monta um `.zip` em `tmp_path`. A ordem de `membros` vira a ordem interna."""
    caminho = tmp_path / nome
    with zipfile.ZipFile(caminho, "w") as arquivo_zip:
        for interno, conteudo in membros.items():
            arquivo_zip.writestr(interno, conteudo)
    return caminho


def _avulso(tmp_path, conteudo, nome="nota.xml"):
    caminho = tmp_path / nome
    caminho.write_text(conteudo, encoding="utf-8")
    return caminho


@pytest.fixture
def caminho_db(tmp_path):
    return tmp_path / "nfe.db"


@pytest.fixture
def conexao(caminho_db):
    con = abrir_banco(caminho_db)
    yield con
    con.close()


def _log(con):
    return con.execute("SELECT resultado, detalhe FROM importacao_arquivos").fetchall()


# --- C3.1 -------------------------------------------------------------------
def test_xml_que_nao_abre_continua_sendo_invalida(conexao, tmp_path):
    """O comportamento que a divida `c` NAO pode levar junto: XML mal formado e
    invalido mesmo, e o `detalhe` e o que diz por que."""
    importar(conexao, _avulso(tmp_path, XML_QUE_NAO_ABRE))

    resultado, detalhe = _log(conexao)[0]
    assert resultado == "invalida"
    assert detalhe


# --- C3.2 -------------------------------------------------------------------
def test_erro_de_persistencia_nao_vira_invalida(conexao, tmp_path, monkeypatch):
    """🔴 O criterio-titulo da divida `c`. Erro ao GRAVAR nao e erro no XML, e
    registra-lo como invalido esconderia o defeito num lote inteiro."""

    def explode(*args, **kwargs):
        raise ValueError("falha ao gravar")

    monkeypatch.setattr(importador, "persistir_nota", explode)

    with pytest.raises(ValueError):
        importar(conexao, _avulso(tmp_path, _texto("nfe_55_1item.xml")))

    assert _log(conexao) == []


# --- C3.3 -------------------------------------------------------------------
def test_importar_commita_o_lote(conexao, caminho_db, tmp_path):
    """🔴 A outra ponta da divida `a`: `persistir_nota` deixou de commitar, entao
    quem fecha a transacao e quem a abriu — `importar`. Outra CONEXAO so enxerga
    o que foi commitado, e e por isso que o oraculo abre uma segunda."""
    importar(conexao, _avulso(tmp_path, _texto("nfe_55_1item.xml")))

    outra = abrir_banco(caminho_db)
    try:
        achou = outra.execute("SELECT 1 FROM notas WHERE chave = ?", (CHAVE_1ITEM,)).fetchone()
    finally:
        outra.close()

    assert achou is not None


# --- C3.4 -------------------------------------------------------------------
def test_cada_arquivo_e_classificado_uma_vez_so(conexao, tmp_path, monkeypatch):
    """A divida `d`. A premissa do literal `2`: o `.zip` tem dois membros, e a
    roteagem entre nota e evento ja precisa classificar cada um — refazer a
    conta dentro do processamento era trabalho jogado fora."""
    chamadas = []

    def contando(texto):
        chamadas.append(texto)
        return tipo_do_xml(texto)

    monkeypatch.setattr(importador, "tipo_do_xml", contando)

    importar(
        conexao,
        _zip(tmp_path, {"1_nota.xml": _texto("nfe_55_1item.xml"), "2_evento.xml": _evento()}),
    )

    assert len(chamadas) == 2


# --- C3.5 -------------------------------------------------------------------
def test_as_duas_passadas_continuam_valendo(conexao, tmp_path):
    """Guarda de regressao: a tarefa reescreve o trecho que monta as duas listas,
    e a invariante-titulo da story 005 mora exatamente ali."""
    importar(
        conexao,
        _zip(tmp_path, {"1_evento.xml": _evento(), "2_nota.xml": _texto("nfe_55_1item.xml")}),
    )

    status = conexao.execute("SELECT status FROM notas WHERE chave = ?", (CHAVE_1ITEM,)).fetchone()[
        0
    ]
    assert status == "cancelada"


# --- C3.7 -------------------------------------------------------------------
def test_erro_ao_aplicar_cancelamento_nao_vira_invalida(conexao, tmp_path, monkeypatch):
    """O mesmo defeito da divida `c`, na funcao ao lado: evento que NAO ABRE e
    invalido, mas falha ao APLICAR o cancelamento e outra coisa."""

    def explode(*args, **kwargs):
        raise ValueError("falha ao aplicar")

    monkeypatch.setattr(importador, "aplicar_cancelamento", explode)

    with pytest.raises(ValueError):
        importar(conexao, _avulso(tmp_path, _evento(), nome="evento.xml"))

    assert _log(conexao) == []


# --- C3.8 (acrescentado no P4) ----------------------------------------------
def test_nota_que_classifica_como_nfe_mas_nao_abre_e_invalida(conexao, tmp_path):
    """🔴 ESTE e o ramo que a divida `c` disputava, e a cobertura mostrou que
    nenhum teste da suite o exercitava.

    O C3.1 manda um arquivo que nem parece XML, e ele para no `elif` de
    `classificacao == "invalida"` — nunca chega ao `try`. So um XML que PASSA
    pelo classificador e TRAVA no extrator entra no `except`, e e ele que tem de
    continuar virando "invalida" depois de `persistir_nota` ter saido de la.
    """
    importar(conexao, _avulso(tmp_path, NFE_QUE_CLASSIFICA_MAS_NAO_ABRE))

    resultado, detalhe = _log(conexao)[0]
    assert resultado == "invalida"
    assert detalhe

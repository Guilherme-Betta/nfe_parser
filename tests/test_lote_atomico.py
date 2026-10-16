"""O lote e uma transacao so, TAMBEM quando falha — achado 1b da revisao de 2026-10-14.

Escrito ANTES da correcao e congelado por commit: quem corrigir nao edita este
arquivo.

🔴 `importar` commita no fim, mas nao desfaz nada quando levanta. A excecao sai
com a transacao ABERTA, carregando a metade do lote que ja tinha sido gravada:
a linha de `importacoes` sem `finalizado_em` e as notas boas que vieram antes
da ruim. Ninguem ve isso na hora. O estrago aparece no PROXIMO `commit()`
daquela conexao — de outro `importar`, de quem for —, que grava a metade orfa
junto com o que ele mesmo fez.

⭐ Quem dispara a falha e uma falha de GRAVACAO simulada no item da segunda nota
— o caso que a spec 01 §6.2 manda desfazer inteiro. Ate 2026-10-16 o gatilho era
uma nota de emitente com CPF e item sem GTIN; desde a decisao do Gui daquele dia
(spec 01 §6.3 item 1) essa nota importa normalmente, e o gatilho virou este. O
contrato testado nao mudou.

🔴 OS `.zip` NASCEM EM `tmp_path` E NUNCA SAO COMMITADOS — repositorio publico.
"""

import sqlite3
import zipfile
from contextlib import closing
from pathlib import Path

import pytest

from nfe_parser import persistencia
from nfe_parser.banco import abrir_banco
from nfe_parser.importador import importar

FIXTURES = Path(__file__).parent / "fixtures"

NS = "http://www.portalfiscal.inf.br/nfe"
CHAVE_1ITEM = "35260499999999000199550010000000011000000017"
TOMATE = "TOMATE ITALIANO KG"


@pytest.fixture
def caminho_banco(tmp_path):
    return tmp_path / "nfe.db"


@pytest.fixture
def conexao(caminho_banco):
    con = abrir_banco(caminho_banco)
    yield con
    con.close()


def _zip(tmp_path, nome, membros):
    """Monta um `.zip` em `tmp_path`. A ordem de `membros` vira a ordem interna."""
    caminho = tmp_path / nome
    with zipfile.ZipFile(caminho, "w") as arquivo_zip:
        for interno, conteudo in membros.items():
            arquivo_zip.writestr(interno, conteudo)
    return caminho


def _fixture(nome):
    return (FIXTURES / nome).read_text(encoding="utf-8")


def _gravacao_do_tomate_falha(monkeypatch):
    """Faz a gravacao do item TOMATE (so ele) levantar como um disco cheio levantaria."""
    original = persistencia.resolver_produto_do_item

    def resolver(conexao, item, emit_cnpj):
        if item["descricao"] == TOMATE:
            raise sqlite3.OperationalError("database or disk is full (simulado)")
        return original(conexao, item, emit_cnpj)

    monkeypatch.setattr(persistencia, "resolver_produto_do_item", resolver)


def _evento(chave):
    return (
        f'<procEventoNFe xmlns="{NS}" versao="1.00"><evento versao="1.00"><infEvento>'
        f"<chNFe>{chave}</chNFe><dhEvento>2026-04-10T10:00:00-03:00</dhEvento>"
        "<tpEvento>110111</tpEvento></infEvento></evento></procEventoNFe>"
    )


def _conta(conexao, tabela):
    return conexao.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]


def test_lote_que_falha_nao_vaza_no_proximo_commit(conexao, tmp_path, monkeypatch):
    """⚠️ O `commit()` depois da excecao e o ponto do teste, e nao descuido: e
    ele que transforma "transacao aberta" em "lixo no disco". Com o lote
    desfeito na saida de `importar`, nao sobra nada para ele gravar.

    ⭐ A nota boa vem PRIMEIRO no `.zip` de proposito: quando a ruim levanta, a
    boa ja esta gravada na transacao — e e ela que nao pode sobreviver.
    """
    lote = _zip(
        tmp_path,
        "lote.zip",
        {"a_boa.xml": _fixture("nfe_65_1item.xml"), "b_tomate.xml": _fixture("nfe_55_1item.xml")},
    )
    _gravacao_do_tomate_falha(monkeypatch)

    with pytest.raises(sqlite3.OperationalError):
        importar(conexao, lote)
    conexao.commit()

    assert _conta(conexao, "importacoes") == 0
    assert _conta(conexao, "importacao_arquivos") == 0
    assert _conta(conexao, "notas") == 0
    assert _conta(conexao, "itens") == 0
    assert _conta(conexao, "produtos") == 0


def test_lote_que_da_certo_fica_inteiro_no_disco(conexao, caminho_banco, tmp_path):
    """Guarda da correcao: ja passa hoje, e TEM de continuar passando.

    🔴 Tirar o `commit()` de `aplicar_cancelamento` so e seguro se `importar`
    confirmar o lote DEPOIS da segunda passada. Se nao confirmar, o
    cancelamento some em silencio — e nenhum outro teste veria, porque todos
    leem pela mesma conexao, que enxerga o que ainda nao foi confirmado.

    ⭐ Por isso a leitura aqui e por OUTRA conexao: ela so ve o que foi
    commitado. O `closing` e o que a fecha no fim — `with sqlite3.connect(...)`
    sozinho NAO fecha a conexao, so encerra a transacao.
    """
    lote = _zip(
        tmp_path,
        "lote.zip",
        {"nota.xml": _fixture("nfe_55_1item.xml"), "evento.xml": _evento(CHAVE_1ITEM)},
    )

    importar(conexao, lote)

    with closing(sqlite3.connect(caminho_banco)) as outra:
        status = outra.execute("SELECT status FROM notas WHERE chave = ?", (CHAVE_1ITEM,))
        assert status.fetchone() == ("cancelada",)
        finalizado = outra.execute("SELECT finalizado_em IS NOT NULL FROM importacoes")
        assert finalizado.fetchall() == [(1,)]

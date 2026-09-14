"""Testes do `.xml` avulso — tarefa 5 da story 004-lote-zip-dedup.

Escritos ANTES da implementacao (passo 2 do loop) e congelados por commit. O
modelo local recebe este arquivo como LEITURA (`--read`), nunca como editavel.

⭐ POR QUE ISTO E UMA TAREFA SEPARADA DO `.zip`

Duas razoes, e a segunda foi MEDIDA no passo 2, nao estimada:

1. "Ler um zip" e "ler um arquivo solto pelo mesmo caminho" sao dois defeitos —
   regra 2 do fatiamento. O segundo e, na verdade, um criterio de *desenho*: o
   C5.3 proibe duas copias da logica de roteamento, e o C5.4 e o teste que
   detecta a copia.
2. Os dois blocos juntos davam ~3,4k de `--read`, o que punha o turno 1 em
   ~6,0k contra o teto empirico de 6k da regra 5. Separados, cada tarefa volta
   para a faixa de ~5k.

⚠️ POR QUE `write_bytes` E NAO `write_text`: no Windows, o modo texto traduz
"\\n" para "\\r\\n" na escrita. Isso mudaria os BYTES do arquivo solto em
relacao aos do mesmo XML dentro do zip, e o C5.4 — que compara os dois
`arquivo_hash` — falharia por um motivo que nao tem nada a ver com o codigo
sendo testado. Foi o modo de falha mais facil de introduzir neste modulo.

Criterios em `specs/004-lote-zip-dedup/spec.md` §3, bloco C5.
"""

import hashlib
import zipfile
from pathlib import Path

import pytest

from nfe_parser.banco import abrir_banco
from nfe_parser.importador import importar

FIXTURES = Path(__file__).parent / "fixtures"

XML_QUEBRADO = "<nfeProc><quebrado"
CHAVE_1ITEM = "35260499999999000199550010000000011000000017"


@pytest.fixture
def conexao(tmp_path):
    con = abrir_banco(tmp_path / "nfe.db")
    yield con
    con.close()


def _texto(nome):
    return (FIXTURES / nome).read_text(encoding="utf-8")


def _avulso(tmp_path, nome, texto):
    caminho = tmp_path / nome
    caminho.write_bytes(texto.encode("utf-8"))  # ver o aviso do cabecalho
    return caminho


def _zip(tmp_path, nome, membros):
    caminho = tmp_path / nome
    with zipfile.ZipFile(caminho, "w") as arquivo_zip:
        for interno, conteudo in membros.items():
            arquivo_zip.writestr(interno, conteudo)
    return caminho


def _sha256(texto):
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _conta(con, tabela):
    return con.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]


def _log(con, importacao_id):
    return con.execute(
        "SELECT arquivo, resultado FROM importacao_arquivos"
        " WHERE importacao_id = ? ORDER BY arquivo",
        (importacao_id,),
    ).fetchall()


# --- C5.1 -------------------------------------------------------------------
def test_um_xml_avulso_entra_pelo_mesmo_importar(conexao, tmp_path):
    caminho = _avulso(tmp_path, "nota.xml", _texto("nfe_55_1item.xml"))

    importacao_id = importar(conexao, caminho)

    assert _conta(conexao, "notas") == 1
    assert _log(conexao, importacao_id) == [("nota.xml", "nova")]


def test_o_avulso_tambem_abre_e_fecha_a_linha_de_importacao(conexao, tmp_path):
    caminho = _avulso(tmp_path, "nota.xml", _texto("nfe_55_1item.xml"))

    importacao_id = importar(conexao, caminho)

    iniciado_em, finalizado_em = conexao.execute(
        "SELECT iniciado_em, finalizado_em FROM importacoes WHERE id = ?", (importacao_id,)
    ).fetchone()

    assert iniciado_em is not None
    assert finalizado_em is not None


def test_um_xml_avulso_corrompido_tambem_nao_levanta(conexao, tmp_path):
    """O criterio 4 nao vale so dentro do zip: um arquivo so tambem nao derruba."""
    caminho = _avulso(tmp_path, "quebrada.xml", XML_QUEBRADO)

    importacao_id = importar(conexao, caminho)

    assert _conta(conexao, "notas") == 0
    assert _log(conexao, importacao_id) == [("quebrada.xml", "invalida")]


def test_o_avulso_tambem_deduplica(conexao, tmp_path):
    caminho = _avulso(tmp_path, "nota.xml", _texto("nfe_55_1item.xml"))

    primeira = importar(conexao, caminho)
    segunda = importar(conexao, caminho)

    assert _conta(conexao, "notas") == 1
    assert _log(conexao, primeira) == [("nota.xml", "nova")]
    assert _log(conexao, segunda) == [("nota.xml", "duplicada")]


# --- C5.2 -------------------------------------------------------------------
def test_o_sufixo_decide_e_nao_o_conteudo(conexao, tmp_path):
    """Um XML com nome `.txt` ainda e tratado como XML unico.

    A regra e: `.zip` abre com `zipfile`; QUALQUER outro sufixo vira arquivo
    unico. Nao ha adivinhacao de conteudo, e este teste trava isso — sem ele, a
    implementacao poderia espiar os bytes e mudar de ideia.
    """
    caminho = _avulso(tmp_path, "nota.txt", _texto("nfe_55_1item.xml"))

    importacao_id = importar(conexao, caminho)

    assert _conta(conexao, "notas") == 1
    assert _log(conexao, importacao_id) == [("nota.txt", "nova")]


# --- C5.4 -------------------------------------------------------------------
def test_o_mesmo_xml_avulso_e_dentro_do_zip_da_o_mesmo_resultado(tmp_path):
    """⭐ O teste que prova que os dois caminhos convergem numa funcao so.

    Duas copias da logica de roteamento — uma no ramo do zip, outra no ramo do
    arquivo solto — passariam em todos os outros testes e divergiriam aqui, que
    e o unico lugar onde as duas sao comparadas lado a lado. E o C5.3, que e um
    criterio de desenho, virado em assercao.
    """
    texto = _texto("nfe_55_1item.xml")
    colunas = "SELECT resultado, arquivo_hash, chave FROM importacao_arquivos WHERE importacao_id = ?"

    con_zip = abrir_banco(tmp_path / "a.db")
    id_zip = importar(con_zip, _zip(tmp_path, "lote.zip", {"nota.xml": texto}))
    linha_zip = con_zip.execute(colunas, (id_zip,)).fetchone()
    con_zip.close()

    con_solto = abrir_banco(tmp_path / "b.db")
    id_solto = importar(con_solto, _avulso(tmp_path, "nota.xml", texto))
    linha_solto = con_solto.execute(colunas, (id_solto,)).fetchone()
    con_solto.close()

    assert linha_zip == linha_solto
    assert linha_zip == ("nova", _sha256(texto), CHAVE_1ITEM)


def test_o_hash_do_avulso_e_dos_bytes_do_arquivo(conexao, tmp_path):
    texto = _texto("nfe_65_1item.xml")
    caminho = _avulso(tmp_path, "nfce.xml", texto)

    importacao_id = importar(conexao, caminho)

    assert conexao.execute(
        "SELECT arquivo_hash FROM importacao_arquivos WHERE importacao_id = ?", (importacao_id,)
    ).fetchone()[0] == _sha256(texto)


# --- C5.5 -------------------------------------------------------------------
def test_o_caminho_aceita_str_e_path(conexao, tmp_path):
    """Os dois tipos, e nos dois ramos — zip e avulso."""
    como_path = _avulso(tmp_path, "a.xml", _texto("nfe_55_1item.xml"))
    como_str = str(_zip(tmp_path, "b.zip", {"outra.xml": _texto("nfe_65_1item.xml")}))

    primeira = importar(conexao, como_path)
    segunda = importar(conexao, como_str)

    assert _log(conexao, primeira) == [("a.xml", "nova")]
    assert _log(conexao, segunda) == [("outra.xml", "nova")]
    assert _conta(conexao, "notas") == 2

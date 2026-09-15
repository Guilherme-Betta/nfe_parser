"""Testes do arquivo de seed REAL — story 010, criterio C4, escrito no P4.

⚠️ Este modulo nao testa codigo: testa o DADO. E por isso ele existe separado
dos oraculos do loop, que semeiam categorias inventadas e minimas de proposito
(spec §5) — um oraculo que dependesse do arquivo real ficaria vermelho toda vez
que o Gui renomeasse uma categoria, e passaria a medir o dado, nao o codigo.

🔴 A D1 decidiu que o `slug` e digitado a mao, e reconheceu a divida: nada no
codigo impede um slug errado. Este arquivo e quem paga essa conta.
"""

import json

import pytest

from nfe_parser.banco import abrir_banco
from nfe_parser.categorizacao import classificar_produto
from nfe_parser.seed import _CAMINHO_PADRAO, carregar_ncm_ancora, carregar_seed_padrao

DADOS = json.loads(_CAMINHO_PADRAO.read_text(encoding="utf-8"))
CATEGORIAS = DADOS["categorias"]
ANCORAS = DADOS["ncm_ancora"]
SLUGS = {cat["slug"] for cat in CATEGORIAS}

# Um NCM que o mapa NAO alcanca: moveis de madeira. Nem `94`, nem `9403`,
# nem `94036000` estao no arquivo — e e disso que o resgate precisa.
NCM_FORA_DO_MAPA = "94036000"


@pytest.fixture
def conexao(tmp_path):
    con = abrir_banco(tmp_path / "nfe.db")
    yield con
    con.close()


def test_a_forma_do_seed_bate_com_o_report(conexao):
    """§5 do report: 10 categorias-pai, 32 subcategorias, e o bucket."""
    pais = [c for c in CATEGORIAS if not c.get("parent") and not c.get("is_bucket")]
    subs = [c for c in CATEGORIAS if c.get("parent")]
    assert (len(pais), len(subs)) == (10, 32)
    assert len(CATEGORIAS) == 43


def test_os_slugs_sao_unicos():
    """🔴 Slug repetido viraria UPDATE silencioso da linha anterior."""
    assert len(SLUGS) == len(CATEGORIAS)


def test_todo_parent_citado_existe_e_o_filho_leva_o_prefixo_do_pai():
    """D2: o slug do filho comeca pelo slug do pai, sem excecao."""
    for cat in CATEGORIAS:
        pai = cat.get("parent")
        if pai:
            assert pai in SLUGS, cat["slug"]
            assert cat["slug"].startswith(f"{pai}-"), cat["slug"]


def test_ha_exatamente_um_bucket_e_o_slug_dele_e_uncategorized():
    buckets = [c["slug"] for c in CATEGORIAS if c.get("is_bucket")]
    assert buckets == ["uncategorized"]


def test_todo_prefixo_tem_largura_valida_e_so_digitos():
    """⚠️ A largura o carregador recusa; "so digitos" mora AQUI (spec §8)."""
    for ancora in ANCORAS:
        prefixo = ancora["prefixo"]
        assert len(prefixo) in (2, 4, 8), prefixo
        assert prefixo.isdigit(), prefixo
    assert len({a["prefixo"] for a in ANCORAS}) == len(ANCORAS)


def test_toda_ancora_aponta_para_uma_categoria_que_existe():
    for ancora in ANCORAS:
        assert ancora["categoria"] in SLUGS, ancora["prefixo"]


def test_o_arquivo_real_carrega_e_recarrega_sem_duplicar(conexao):
    carregar_seed_padrao(conexao)
    primeira = dict(conexao.execute("SELECT slug, id FROM categorias").fetchall())
    carregar_seed_padrao(conexao)
    assert dict(conexao.execute("SELECT slug, id FROM categorias").fetchall()) == primeira
    assert len(primeira) == 43
    assert conexao.execute("SELECT COUNT(*) FROM ncm_ancora").fetchone()[0] == len(ANCORAS)


def test_crescer_o_mapa_ncm_RESGATA_o_produto_que_caiu_no_bucket(conexao):
    """🔴 A D3 da 009 ganhando sentido — e a razao de o seed ser idempotente.

    O produto cai no bucket com `origem` NULL, que e o que o marca como
    reprocessavel. Acrescentar a ancora que o alcanca e rodar a cascata de novo
    TEM de o tirar de la. Se `classificar_produto` parasse em "ja tem
    categoria", este teste ficaria vermelho — e ele e o unico lugar do projeto
    onde as duas stories se provam juntas.
    """
    carregar_seed_padrao(conexao)
    conexao.execute(
        "INSERT INTO produtos (id, identidade_origem, gtin, descricao_exemplo,"
        " criado_em, atualizado_em) VALUES (1, 'gtin', '789', 'Mesa', 'ontem', 'ontem')"
    )

    bucket = conexao.execute("SELECT id FROM categorias WHERE is_bucket = 1").fetchone()[0]
    assert classificar_produto(conexao, 1, NCM_FORA_DO_MAPA) == bucket
    assert conexao.execute("SELECT origem FROM produtos WHERE id = 1").fetchone()[0] is None

    carregar_ncm_ancora(conexao, [{"prefixo": "9403", "categoria": "outros"}])
    outros = conexao.execute("SELECT id FROM categorias WHERE slug = 'outros'").fetchone()[0]

    assert classificar_produto(conexao, 1, NCM_FORA_DO_MAPA) == outros
    assert conexao.execute("SELECT origem FROM produtos WHERE id = 1").fetchone()[0] == "ncm"

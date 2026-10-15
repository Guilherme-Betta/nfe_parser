"""As operacoes que a camada web dispara — e quem abre e fecha cada transacao.

🔴 Os nucleos (`taxonomia`, `categorizacao`, `seed`, `varredura`) nao commitam: quem
abre a transacao e quem a fecha. Este modulo e esse "quem" para o app web — uma
transacao por operacao, com `with conexao:` (COMMIT no fim, ROLLBACK se algo
levantar). A API e as paginas chamam daqui, e por isso as duas gravam igual.

⚠️ A excecao e `importar`, que ja e dono do seu lote (spec 01 §6.2): ele commita
sozinho, e a classificacao roda DEPOIS, numa segunda transacao (spec 03 §3).
"""

from pathlib import Path

from nfe_parser import taxonomia
from nfe_parser.banco import abrir_banco
from nfe_parser.categorizacao import definir_categoria_manual
from nfe_parser.consultas import id_da_categoria
from nfe_parser.importador import importar
from nfe_parser.seed import carregar_seed_padrao
from nfe_parser.varredura import classificar_produtos_pendentes

NAO_MUDA = object()
"""Marca o campo que `editar_categoria` deve deixar como esta.

⭐ `None` nao serve para isso: em `parent_slug`, `None` QUER dizer "subir para o
nivel 1". Sem uma marca propria, "nao mover" e "mover para o topo" seriam o mesmo
valor.
"""


def preparar_banco(caminho):
    """Garante pasta, esquema, migracoes e seed. Roda no startup do app.

    ⭐ Tudo aqui e idempotente — `criar_esquema` tem `IF NOT EXISTS`, as migracoes
    pulam o que ja rodou, o seed so insere o que falta —, entao subir o app de novo
    sobre o mesmo arquivo nao muda nada.
    """
    Path(caminho).parent.mkdir(parents=True, exist_ok=True)
    conexao = abrir_banco(caminho)
    try:
        with conexao:
            carregar_seed_padrao(conexao)
    finally:
        conexao.close()


def importar_e_classificar(conexao, caminho, origem):
    """Importa o lote e roda a classificacao base sobre os pendentes. Devolve o id.

    🔴 Duas transacoes, de proposito. Se a classificacao falhar, a excecao sobe,
    mas o lote JA ESTA gravado — e nada se perde: os produtos continuam com
    `origem IS NULL`, e a proxima varredura os pega. Juntar as duas faria um erro
    de classificacao desfazer uma importacao que estava certa.

    ⛔ Sem LLM: ele e opt-in e roda a parte (`classificar_com_llm`).
    """
    importacao_id = importar(conexao, caminho, origem)
    with conexao:
        classificar_produtos_pendentes(conexao)
    return importacao_id


def classificar_com_llm(conexao, llm):
    """Roda a varredura COM o LLM. Devolve quantos produtos sairam do pendente."""
    with conexao:
        return classificar_produtos_pendentes(conexao, llm)


def classificar_manual(conexao, produto_id, categoria_slug):
    """A decisao de um humano: o produto vai para `categoria_slug`, com `origem='manual'`."""
    with conexao:
        definir_categoria_manual(conexao, produto_id, id_da_categoria(conexao, categoria_slug))


def criar_categoria(conexao, nome, parent_slug=None):
    with conexao:
        return taxonomia.criar_categoria(conexao, nome, parent_slug)


def editar_categoria(conexao, slug, nome=NAO_MUDA, parent_slug=NAO_MUDA):
    """Renomeia e/ou move, numa transacao so: ou as duas mudancas entram, ou nenhuma."""
    with conexao:
        if nome is not NAO_MUDA:
            taxonomia.renomear_categoria(conexao, slug, nome)
        if parent_slug is not NAO_MUDA:
            taxonomia.mover_categoria(conexao, slug, parent_slug)


def apagar_categoria(conexao, slug):
    with conexao:
        taxonomia.apagar_categoria(conexao, slug)

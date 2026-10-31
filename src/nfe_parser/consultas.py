"""Leituras que a camada web serve (spec 03 §4): importacoes, notas, produtos, arvore.

⭐ SQL puro, sem FastAPI: as mesmas funcoes atendem a API JSON e as paginas, e sao
testaveis sem HTTP. ⛔ Nada aqui escreve no banco.

⭐ Os filtros montam o `WHERE` a partir de pedacos FIXOS deste arquivo; o valor
que vem de fora entra sempre como parametro nomeado (`:mes`), nunca colado no
texto do SQL. E isso que fecha a porta para injecao de SQL.

📋 Dinheiro sai como na spec 01 §6.2: `*_centavos` (int, a fonte de verdade) e a
string derivada ao lado.
"""

from nfe_parser.serializacao import de_centavos
from nfe_parser.vocabulario import IdentidadeProduto, OrigemClassificacao

_CONTADORES = (
    "total_arquivos",
    "notas_novas",
    "duplicadas",
    "invalidas",
    "cancelamentos_aplicados",
    "nao_suportadas",
)


def _dicts(cursor):
    """Cada linha do cursor como dicionario `{coluna: valor}`."""
    colunas = [d[0] for d in cursor.description]
    return [dict(zip(colunas, linha)) for linha in cursor.fetchall()]


def _where(filtros):
    return ("WHERE " + " AND ".join(filtros)) if filtros else ""


def _pagina(pagina, por_pagina):
    return {"limite": por_pagina, "deslocamento": (pagina - 1) * por_pagina}


def _importacao_de(linha):
    return {
        "importacao_id": linha["id"],
        "origem": linha["origem"],
        "iniciado_em": linha["iniciado_em"],
        "finalizado_em": linha["finalizado_em"],
        "contadores": {nome: linha[nome] for nome in _CONTADORES},
    }


def listar_importacoes(conexao, limite=20):
    """As `limite` importacoes mais recentes, da ultima para a primeira."""
    cursor = conexao.execute("SELECT * FROM importacoes ORDER BY id DESC LIMIT ?", (limite,))
    return [_importacao_de(linha) for linha in _dicts(cursor)]


def resumo_classificacao(conexao, importacao_id):
    """Os produtos distintos das notas NOVAS do lote, contados pelo estado atual.

    ⭐ "Notas novas" porque e so delas que o lote e dono: `notas.importacao_id`
    fica com o primeiro lote que gravou a nota, e uma duplicada nao muda isso.

    ⚠️ `memoria` soma `manual` e `memoria`: as duas sao o degrau 1 da cascata,
    "ja estava decidido". `bucket` e `origem IS NULL` — pendente.
    """
    por_origem = dict(
        conexao.execute(
            "SELECT p.origem, COUNT(DISTINCT p.id) FROM itens i"
            " JOIN notas n ON n.chave = i.nota_chave"
            " JOIN produtos p ON p.id = i.produto_id"
            " WHERE n.importacao_id = ? GROUP BY p.origem",
            (importacao_id,),
        ).fetchall()
    )
    return {
        "produtos": sum(por_origem.values()),
        "memoria": por_origem.get(OrigemClassificacao.MANUAL, 0)
        + por_origem.get(OrigemClassificacao.MEMORIA, 0),
        "ncm": por_origem.get(OrigemClassificacao.NCM, 0),
        "llm": por_origem.get(OrigemClassificacao.LLM, 0),
        "bucket": por_origem.get(None, 0),
    }


def importacao(conexao, importacao_id):
    """O lote com contadores, resumo da classificacao e log por arquivo. None se nao existe."""
    linhas = _dicts(conexao.execute("SELECT * FROM importacoes WHERE id = ?", (importacao_id,)))
    if not linhas:
        return None

    resultado = _importacao_de(linhas[0])
    resultado["classificacao"] = resumo_classificacao(conexao, importacao_id)
    resultado["arquivos"] = _dicts(
        conexao.execute(
            "SELECT arquivo, resultado, chave, detalhe FROM importacao_arquivos"
            " WHERE importacao_id = ? ORDER BY id",
            (importacao_id,),
        )
    )
    return resultado


def listar_notas(conexao, mes=None, loja_cnpj=None, status=None, pagina=1, por_pagina=50):
    """Cabecalhos de nota, filtrados e paginados. Da mais recente para a mais antiga.

    ⚠️ `mes` compara os 7 primeiros caracteres de `dh_emi` (`'YYYY-MM'`): a data e
    a do XML, com o fuso do emitente, e a competencia e a do documento.
    """
    filtros, parametros = [], _pagina(pagina, por_pagina)
    if mes:
        filtros.append("substr(n.dh_emi, 1, 7) = :mes")
        parametros["mes"] = mes
    if loja_cnpj:
        filtros.append("n.emit_cnpj = :loja_cnpj")
        parametros["loja_cnpj"] = loja_cnpj
    if status:
        filtros.append("n.status = :status")
        parametros["status"] = status
    where = _where(filtros)

    total = conexao.execute(f"SELECT COUNT(*) FROM notas n {where}", parametros).fetchone()[0]
    linhas = _dicts(
        conexao.execute(
            "SELECT n.chave, n.modelo, n.dh_emi, n.emit_nome, n.emit_cnpj, n.valor_total,"
            " n.status, (SELECT COUNT(*) FROM itens i WHERE i.nota_chave = n.chave) AS n_itens"
            f" FROM notas n {where}"
            " ORDER BY n.dh_emi DESC, n.chave LIMIT :limite OFFSET :deslocamento",
            parametros,
        )
    )
    notas = [
        {
            "chave": linha["chave"],
            "modelo": linha["modelo"],
            "dh_emi": linha["dh_emi"],
            "emit_nome": linha["emit_nome"],
            "emit_cnpj": linha["emit_cnpj"],
            "valor_total_centavos": linha["valor_total"],
            "valor_total": de_centavos(linha["valor_total"]),
            "status": linha["status"],
            "n_itens": linha["n_itens"],
        }
        for linha in linhas
    ]
    return {"notas": notas, "total": total, "pagina": pagina, "por_pagina": por_pagina}


_SELECT_PRODUTO = (
    "SELECT p.id, p.descricao_exemplo, p.identidade_origem, p.gtin,"
    " c.slug AS categoria_slug, c.nome AS categoria, p.origem,"
    " (SELECT COUNT(*) FROM itens i WHERE i.produto_id = p.id) AS n_itens"
    " FROM produtos p LEFT JOIN categorias c ON c.id = p.categoria_id"
)


_NA_FILA = "(p.origem IS NULL OR p.categoria_id IN (SELECT id FROM categorias WHERE is_bucket = 1))"
"""Produto que a revisao mostra. 🔴 So `origem IS NULL` deixaria de fora o devolvido
a fila, que e `manual` no bucket — e o humano o perderia de vista."""


def _produto_de(linha):
    """⭐ `aproximado` e a honestidade da spec 02 §3: identidade por texto so vale
    dentro da loja, e a UI tem de dizer isso em vez de fingir precisao."""
    return {**linha, "aproximado": linha["identidade_origem"] == IdentidadeProduto.TEXTO}


def listar_produtos(conexao, classificado=None, origem=None, pagina=1, por_pagina=50):
    """A fila de revisao: produtos filtrados e paginados, os mais frequentes primeiro.

    "Nao classificado" e quem esta NA FILA: `origem` NULL (a cascata ainda nao
    resolveu) ou no bucket (inclui o que o humano devolveu, com `origem='manual'`
    — spec 02 §4). ⛔ Nunca `categoria_id IS NULL`: o produto no bucket TEM
    categoria e e justamente ele que precisa de revisao.
    """
    filtros, parametros = [], _pagina(pagina, por_pagina)
    if classificado is not None:
        filtros.append(f"NOT {_NA_FILA}" if classificado else _NA_FILA)
    if origem:
        filtros.append("p.origem = :origem")
        parametros["origem"] = origem
    where = _where(filtros)

    total = conexao.execute(f"SELECT COUNT(*) FROM produtos p {where}", parametros).fetchone()[0]
    linhas = _dicts(
        conexao.execute(
            f"{_SELECT_PRODUTO} {where} ORDER BY n_itens DESC, p.id"
            " LIMIT :limite OFFSET :deslocamento",
            parametros,
        )
    )
    return {
        "produtos": [_produto_de(linha) for linha in linhas],
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina,
    }


def itens_aproximados(conexao, chave):
    """Os `n_item` da nota cujo produto tem identidade por texto — para a UI marcar."""
    return {
        linha[0]
        for linha in conexao.execute(
            "SELECT i.n_item FROM itens i JOIN produtos p ON p.id = i.produto_id"
            " WHERE i.nota_chave = ? AND p.identidade_origem = 'texto'",
            (chave,),
        )
    }


def produto(conexao, produto_id):
    """Um produto, no mesmo formato da fila. None se nao existe."""
    linhas = _dicts(conexao.execute(f"{_SELECT_PRODUTO} WHERE p.id = ?", (produto_id,)))
    return _produto_de(linhas[0]) if linhas else None


def arvore_categorias(conexao):
    """A taxonomia em 2 niveis, com quantos produtos cada categoria tem DIRETAMENTE.

    ⭐ `n_produtos` existe para a UI avisar, antes de apagar, quantos produtos vao
    para o bucket. Ordem por slug: e ASCII, entao acento nao embaralha a lista.
    """
    linhas = _dicts(
        conexao.execute(
            "SELECT c.id, c.slug, c.nome, c.parent_id, c.is_bucket,"
            " (SELECT COUNT(*) FROM produtos p WHERE p.categoria_id = c.id) AS n_produtos"
            " FROM categorias c ORDER BY c.is_bucket, c.slug"
        )
    )
    filhas = {}
    for linha in linhas:
        if linha["parent_id"] is not None:
            filhas.setdefault(linha["parent_id"], []).append(
                {"slug": linha["slug"], "nome": linha["nome"], "n_produtos": linha["n_produtos"]}
            )
    return [
        {
            "slug": linha["slug"],
            "nome": linha["nome"],
            "is_bucket": bool(linha["is_bucket"]),
            "n_produtos": linha["n_produtos"],
            "filhas": filhas.get(linha["id"], []),
        }
        for linha in linhas
        if linha["parent_id"] is None
    ]


def categoria(conexao, slug):
    """`{slug, nome, parent_slug}` da categoria. None se nao existe."""
    linhas = _dicts(
        conexao.execute(
            "SELECT c.slug, c.nome, pai.slug AS parent_slug FROM categorias c"
            " LEFT JOIN categorias pai ON pai.id = c.parent_id WHERE c.slug = ?",
            (slug,),
        )
    )
    return linhas[0] if linhas else None


def id_da_categoria(conexao, slug):
    """O `id` interno da categoria `slug`. Levanta `LookupError` se nao existe."""
    linha = conexao.execute("SELECT id FROM categorias WHERE slug = ?", (slug,)).fetchone()
    if linha is None:
        raise LookupError(f"nao existe categoria com slug {slug!r}")
    return linha[0]


def bucket(conexao):
    """`{slug, nome}` do bucket — o "Nao Classificado". Levanta `LookupError` se nao ha."""
    linha = conexao.execute("SELECT slug, nome FROM categorias WHERE is_bucket = 1").fetchone()
    if linha is None:
        raise LookupError("nao ha bucket no banco: o seed nao foi carregado")
    return {"slug": linha[0], "nome": linha[1]}


def lojas(conexao):
    """`[(cnpj, nome)]` de toda loja com nota, por nome — para o filtro da tela."""
    return conexao.execute(
        "SELECT emit_cnpj, MAX(emit_nome) FROM notas WHERE emit_cnpj IS NOT NULL"
        " GROUP BY emit_cnpj ORDER BY 2, 1"
    ).fetchall()


def contagens(conexao):
    """Quantas linhas ha nas tabelas principais — para o `/api/health`."""
    return {
        tabela: conexao.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]
        for tabela in ("notas", "itens", "produtos", "categorias")
    }

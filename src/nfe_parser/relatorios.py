"""As analises da visualizacao — spec 05 §3. So leitura.

⭐ Todas passam por `gastos.consultar`, com as regras comuns (so nota valida,
competencia pelo `dh_emi`, rollup de categoria) e os mesmos filtros: `de`, `ate`,
`categoria_slug`, `loja_cnpj`, `produto_id`. E o mesmo motor do orcamento, entao
o relatorio e o orcamento nunca discordam sobre quanto se gastou.

⛔ Nada aqui escreve no banco.
"""

from decimal import Decimal

from nfe_parser import gastos

ORDENS = ("valor", "quantidade")


def meses_entre(inicio, fim):
    """`'2026-11'..'2027-02'` → os quatro meses, inclusive. Vazio se `inicio > fim`."""
    atual = int(inicio[:4]) * 12 + int(inicio[5:7]) - 1
    ultimo = int(fim[:4]) * 12 + int(fim[5:7]) - 1
    return [f"{indice // 12:04d}-{indice % 12 + 1:02d}" for indice in range(atual, ultimo + 1)]


def gasto_mensal(conexao, **filtros):
    """A serie `[{mes, gasto}]`, em ordem, com 0 nos meses sem gasto.

    🔴 O zero e informacao: um mes sem compra que SUMISSE da serie faria o
    grafico de linha ligar junho a agosto por cima de julho, como se julho
    tivesse gasto a media dos dois. A serie vai do primeiro ao ultimo mes com
    gasto — ou de `de` a `ate`, quando o pedido diz.
    """
    por_mes = dict(
        gastos.consultar(
            conexao, "substr(n.dh_emi, 1, 7), SUM(i.valor_linha)", "GROUP BY 1", **filtros
        )
    )
    inicio = filtros.get("de") or (min(por_mes) if por_mes else None)
    fim = filtros.get("ate") or (max(por_mes) if por_mes else None)
    if not (por_mes or (filtros.get("de") and filtros.get("ate"))):
        return []
    return [{"mes": mes, "gasto": por_mes.get(mes, 0)} for mes in meses_entre(inicio, fim)]


def gasto_categoria(conexao, **filtros):
    """Por categoria de nivel 1, com rollup; o nao classificado a parte."""
    return gastos.gasto_por_categoria(conexao, **filtros)


def gasto_loja(conexao, **filtros):
    """`[{emit_cnpj, emit_nome, gasto}]`, maior primeiro; empate pelo CNPJ.

    ⚠️ O nome sai de UMA das notas da loja (`MAX`): a mesma loja pode ter grafado
    o nome de jeitos diferentes ao longo do tempo, e a identidade e o CNPJ.
    """
    linhas = gastos.consultar(
        conexao,
        "n.emit_cnpj, MAX(n.emit_nome), SUM(i.valor_linha)",
        "GROUP BY n.emit_cnpj ORDER BY 3 DESC, 1",
        **filtros,
    )
    return [{"emit_cnpj": cnpj, "emit_nome": nome, "gasto": gasto} for cnpj, nome, gasto in linhas]


def top_produtos(conexao, limite=20, ordenar="valor", **filtros):
    """Os produtos que mais pesaram, por valor ou por quantidade.

    🔴 A quantidade e somada em `Decimal`, a partir da string exata do XML, e sai
    como string: `SUM()` no SQLite converteria o TEXT para REAL (float binario),
    e `0.1 + 0.2` deixaria de ser `0.3`. Por isso a soma e feita aqui, item a item.

    ⚠️ Produto vendido em unidades diferentes (KG numa loja, UN noutra) somaria
    coisas diferentes; na pratica a identidade de produto quase sempre fixa a
    unidade, e o numero e para ordenar, nao para conta.
    """
    if ordenar not in ORDENS:
        raise ValueError(f"ordenar tem de ser um de {ORDENS}; recebi {ordenar!r}")

    gasto, quantidade = {}, {}
    for produto_id, valor, qtd in gastos.consultar(
        conexao,
        "i.produto_id, i.valor_linha, i.quantidade",
        "AND i.produto_id IS NOT NULL",
        **filtros,
    ):
        gasto[produto_id] = gasto.get(produto_id, 0) + valor
        quantidade[produto_id] = quantidade.get(produto_id, Decimal(0)) + Decimal(qtd)

    medida = gasto if ordenar == "valor" else quantidade
    escolhidos = sorted(medida, key=lambda produto_id: (-medida[produto_id], produto_id))[:limite]
    if not escolhidos:
        return []

    marcadores = ", ".join("?" for _ in escolhidos)
    info = {
        produto_id: (descricao, identidade, cnpj)
        for produto_id, descricao, identidade, cnpj in conexao.execute(
            "SELECT id, descricao_exemplo, identidade_origem, emit_cnpj FROM produtos"
            f" WHERE id IN ({marcadores})",
            escolhidos,
        )
    }
    return [_item_do_top(produto_id, info, gasto, quantidade) for produto_id in escolhidos]


def _item_do_top(produto_id, info, gasto, quantidade):
    """⭐ `emit_cnpj` so para o produto por TEXTO: a identidade dele E a loja, e tres
    "TOMATE KG" de tres lojas sao tres produtos — sem a loja, tres linhas iguais. O
    produto por GTIN nao pertence a loja nenhuma."""
    descricao, identidade, cnpj = info[produto_id]
    return {
        "produto_id": produto_id,
        "descricao_exemplo": descricao,
        "gasto": gasto[produto_id],
        "quantidade": str(quantidade[produto_id]),
        "identidade_origem": identidade,
        "aproximado": identidade == "texto",
        "emit_cnpj": cnpj if identidade == "texto" else None,
    }


def preco_no_tempo(conexao, produto_id, **filtros):
    """Os precos unitarios pagos num produto, por data, com a loja de cada um.

    ⭐ `aproximado` e a honestidade da spec 02 §3: produto por texto so casa
    dentro da loja; por GTIN, a serie e confiavel entre lojas.
    """
    produto = conexao.execute(
        "SELECT descricao_exemplo, identidade_origem FROM produtos WHERE id = ?", (produto_id,)
    ).fetchone()
    if produto is None:
        raise LookupError(f"nao existe produto {produto_id}")

    pontos = gastos.consultar(
        conexao,
        "n.dh_emi, i.valor_unitario, n.emit_nome, n.emit_cnpj",
        "ORDER BY n.dh_emi, n.chave, i.n_item",
        produto_id=produto_id,
        **filtros,
    )
    return {
        "produto_id": produto_id,
        "descricao_exemplo": produto[0],
        "identidade_origem": produto[1],
        "aproximado": produto[1] == "texto",
        "pontos": [
            {"data": data, "valor_unitario": valor, "emit_nome": nome, "emit_cnpj": cnpj}
            for data, valor, nome, cnpj in pontos
        ],
    }

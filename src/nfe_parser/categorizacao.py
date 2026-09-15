def buscar_categoria_por_ncm(conexao, ncm):
    if not ncm:
        return None

    cursor = conexao.execute(
        """
        SELECT categoria_id FROM ncm_ancora
        WHERE prefixo IN (?, ?, ?)
        ORDER BY LENGTH(prefixo) DESC
        LIMIT 1
        """,
        (ncm[:8], ncm[:4], ncm[:2]),
    )

    resultado = cursor.fetchone()
    if resultado:
        return resultado[0]

    return None


def _categoria_do_bucket(conexao):
    linha = conexao.execute("SELECT id FROM categorias WHERE is_bucket = 1").fetchone()
    if linha is None:
        raise LookupError("nenhuma categoria com is_bucket = 1; o seed da taxonomia nao foi carregado")
    return linha[0]


def classificar_produto(conexao, produto_id, ncm):
    from datetime import UTC, datetime

    linha = conexao.execute(
        "SELECT categoria_id, origem FROM produtos WHERE id = ?", (produto_id,)
    ).fetchone()
    if linha is None:
        raise LookupError(f"produto {produto_id} nao existe")
    categoria_atual, origem_atual = linha[0], linha[1]

    if origem_atual in ("manual", "memoria"):
        return categoria_atual

    categoria = buscar_categoria_por_ncm(conexao, ncm)
    if categoria is None:
        categoria = _categoria_do_bucket(conexao)
        origem = None
    else:
        origem = "ncm"

    conexao.execute(
        "UPDATE produtos SET categoria_id = ?, origem = ?, atualizado_em = ? WHERE id = ?",
        (categoria, origem, datetime.now(UTC).isoformat(), produto_id),
    )

    return categoria


def definir_categoria_manual(conexao, produto_id, categoria_id):
    from datetime import UTC, datetime

    linha = conexao.execute("SELECT id FROM produtos WHERE id = ?", (produto_id,)).fetchone()
    if linha is None:
        raise LookupError(f"produto {produto_id} nao existe")

    conexao.execute(
        "UPDATE produtos SET categoria_id = ?, origem = 'manual', atualizado_em = ? WHERE id = ?",
        (categoria_id, datetime.now(UTC).isoformat(), produto_id),
    )

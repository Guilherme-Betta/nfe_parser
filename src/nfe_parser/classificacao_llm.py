from datetime import UTC, datetime

from nfe_parser.categorizacao import classificar_produto


def classificar_produto_com_llm(conexao, produto_id, ncm, llm=None):
    # PASSO 1
    categoria = classificar_produto(conexao, produto_id, ncm)
    if llm is None:
        return categoria

    # PASSO 2
    origem, descricao = conexao.execute(
        "SELECT origem, descricao_exemplo FROM produtos WHERE id = ?", (produto_id,)
    ).fetchone()
    if origem is not None or not descricao:
        return categoria

    # PASSO 3
    slugs = [
        linha[0]
        for linha in conexao.execute(
            "SELECT slug FROM categorias WHERE is_bucket = 0 ORDER BY slug"
        ).fetchall()
    ]

    # PASSO 4
    resposta = llm(descricao, slugs)
    if resposta is None:
        return categoria
    slug, confianca = resposta

    # PASSO 5
    linha = conexao.execute(
        "SELECT id FROM categorias WHERE slug = ? AND is_bucket = 0", (slug,)
    ).fetchone()
    if linha is None:
        return categoria

    # PASSO 6
    conexao.execute(
        "UPDATE produtos SET categoria_id = ?, origem = 'llm', confianca = ?, atualizado_em = ?"
        " WHERE id = ?",
        (linha[0], confianca, datetime.now(UTC).isoformat(), produto_id),
    )
    return linha[0]

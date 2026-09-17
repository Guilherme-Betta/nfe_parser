from nfe_parser.categorizacao import classificar_produto

def classificar_produtos_pendentes(conexao) -> int:
    pendentes = conexao.execute("SELECT id FROM produtos WHERE origem IS NULL").fetchall()
    resgatados = 0

    for (produto_id,) in pendentes:
        linha = conexao.execute(
            "SELECT ncm FROM itens WHERE produto_id = ? ORDER BY id DESC LIMIT 1",
            (produto_id,),
        ).fetchone()
        ncm = linha[0] if linha else None

        classificar_produto(conexao, produto_id, ncm)
        origem = conexao.execute(
            "SELECT origem FROM produtos WHERE id = ?", (produto_id,)
        ).fetchone()[0]
        if origem is not None:
            resgatados += 1

    return resgatados

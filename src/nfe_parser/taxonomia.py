from datetime import UTC, datetime

from nfe_parser.categorizacao import categoria_do_bucket


def apagar_categoria(conexao, slug):
    # PASSO 1
    linha = conexao.execute("SELECT id, is_bucket FROM categorias WHERE slug = ?", (slug,)).fetchone()
    if linha is None:
        raise LookupError(f"nao existe categoria com slug {slug!r}")
    categoria_id, is_bucket = linha[0], linha[1]

    # PASSO 2
    if is_bucket:
        raise ValueError(f"a categoria {slug!r} e o bucket; apaga-la quebraria a classificacao")

    # PASSO 3
    filhas = conexao.execute(
        "SELECT COUNT(*) FROM categorias WHERE parent_id = ?", (categoria_id,)
    ).fetchone()[0]
    if filhas:
        raise ValueError(
            f"a categoria {slug!r} tem {filhas} subcategoria(s);"
            " mova ou apague as subcategorias antes de apagar esta"
        )

    # PASSO 4
    conexao.execute(
        "UPDATE produtos SET categoria_id = ?, origem = NULL, atualizado_em = ? WHERE categoria_id = ?",
        (categoria_do_bucket(conexao), datetime.now(UTC).isoformat(), categoria_id),
    )

    # PASSO 5
    conexao.execute("DELETE FROM ncm_ancora WHERE categoria_id = ?", (categoria_id,))

    # PASSO 6
    conexao.execute(
        "INSERT INTO categorias_apagadas (slug, apagada_em) VALUES (?, ?) ON CONFLICT(slug) DO NOTHING",
        (slug, datetime.now(UTC).isoformat()),
    )

    # PASSO 7
    conexao.execute("DELETE FROM categorias WHERE id = ?", (categoria_id,))


def mover_categoria(conexao, slug, novo_parent_slug):
    # PASSO 1
    linha = conexao.execute("SELECT id FROM categorias WHERE slug = ?", (slug,)).fetchone()
    if linha is None:
        raise LookupError(f"nao existe categoria com slug {slug!r}")
    categoria_id = linha[0]

    # PASSO 2
    if novo_parent_slug is None:
        conexao.execute("UPDATE categorias SET parent_id = NULL WHERE id = ?", (categoria_id,))
        return

    # PASSO 3
    pai = conexao.execute("SELECT id FROM categorias WHERE slug = ?", (novo_parent_slug,)).fetchone()
    if pai is None:
        raise LookupError(f"nao existe categoria com slug {novo_parent_slug!r} para ser o novo pai")

    # PASSO 4
    atual = pai[0]
    while atual is not None:
        if atual == categoria_id:
            raise ValueError(
                f"mover {slug!r} para dentro de {novo_parent_slug!r} criaria um ciclo na arvore"
            )
        atual = conexao.execute(
            "SELECT parent_id FROM categorias WHERE id = ?", (atual,)
        ).fetchone()[0]

    # PASSO 5
    conexao.execute("UPDATE categorias SET parent_id = ? WHERE id = ?", (pai[0], categoria_id))


def renomear_categoria(conexao, slug, nome):
    # PASSO 1
    if not nome:
        raise ValueError(f"renomear_categoria exige um nome nao vazio; recebeu {nome!r}")

    # PASSO 2
    linha = conexao.execute("SELECT id FROM categorias WHERE slug = ?", (slug,)).fetchone()
    if linha is None:
        raise LookupError(f"nao existe categoria com slug {slug!r}")

    # PASSO 3
    conexao.execute("UPDATE categorias SET nome = ? WHERE slug = ?", (nome, slug))

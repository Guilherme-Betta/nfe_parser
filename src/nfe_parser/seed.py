def carregar_categorias(conexao, categorias):
    # PASSO 1: inserir cada categoria
    for cat in categorias:
        conexao.execute(
            """
            INSERT INTO categorias (slug, nome, is_bucket) VALUES (?, ?, ?)
            ON CONFLICT(slug) DO UPDATE SET nome = excluded.nome, is_bucket = excluded.is_bucket
            """,
            (cat["slug"], cat["nome"], 1 if cat.get("is_bucket") else 0),
        )

    # PASSO 2: ligar os pais
    for cat in categorias:
        pai_slug = cat.get("parent")
        if pai_slug:
            pai = conexao.execute("SELECT id FROM categorias WHERE slug = ?", (pai_slug,)).fetchone()
            if pai is None:
                raise LookupError(
                    f"a categoria {cat['slug']} aponta para o pai {pai_slug}, que nao esta no seed"
                )
            conexao.execute("UPDATE categorias SET parent_id = ? WHERE slug = ?", (pai[0], cat["slug"]))

    # PASSO 3: conferir o bucket
    quantos = conexao.execute("SELECT COUNT(*) FROM categorias WHERE is_bucket = 1").fetchone()[0]
    if quantos != 1:
        raise ValueError(
            f"o banco ficou com {quantos} categorias is_bucket = 1; tem de haver exatamente uma"
        )


def carregar_ncm_ancora(conexao, ancoras):
    for ancora in ancoras:
        prefixo = ancora["prefixo"]
        slug = ancora["categoria"]

        # PASSO 1: confira a largura do prefixo ANTES de qualquer consulta
        if len(prefixo) not in (2, 4, 8):
            raise ValueError(
                f"o prefixo NCM {prefixo} tem {len(prefixo)} digitos; so 2, 4 ou 8 casam com a busca"
            )

        # PASSO 2: resolva o slug
        linha = conexao.execute("SELECT id FROM categorias WHERE slug = ?", (slug,)).fetchone()
        if linha is None:
            raise LookupError(
                f"o prefixo {prefixo} aponta para a categoria {slug}, que nao esta no seed"
            )

        # PASSO 3: grave
        conexao.execute(
            """
            INSERT INTO ncm_ancora (prefixo, categoria_id) VALUES (?, ?)
            ON CONFLICT(prefixo) DO UPDATE SET categoria_id = excluded.categoria_id
            """,
            (prefixo, linha[0]),
        )

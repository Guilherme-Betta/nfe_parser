"""O gasto REALIZADO: quanto saiu, por categoria, num periodo. Motor das specs 04 e 05.

As regras comuns (spec 04 §3, spec 05 §3) moram aqui, num lugar so:
- soma `itens.valor_linha` (centavos, inteiro — nunca float);
- so `notas.status = 'ok'`: cancelada NUNCA conta;
- o mes e `substr(notas.dh_emi, 1, 7)` — a competencia e a data de emissao;
- ROLLUP: o gasto de uma subcategoria sobe para a categoria de nivel 1.

⛔ Nada aqui escreve no banco.
"""

# 🔴 A CTE recursiva leva cada categoria a sua RAIZ (nivel 1). A arvore tem 2
# niveis hoje (spec 02), e `COALESCE(parent_id, id)` bastaria — mas so enquanto
# ninguem criar um terceiro nivel por fora das funcoes da taxonomia. Subir ate o
# `parent_id IS NULL` vale para qualquer profundidade, e o custo e o mesmo.
CTE_RAIZ = """
    raiz(id, raiz_id) AS (
      SELECT id, id FROM categorias WHERE parent_id IS NULL
      UNION ALL
      SELECT c.id, r.raiz_id FROM categorias c JOIN raiz r ON c.parent_id = r.id
    )
"""

# ⭐ Os dois LEFT JOIN nao sao enfeite: item sem produto e produto sem categoria
# existem (spec 02 §7.2), e com INNER JOIN o gasto deles SUMIRIA do total em vez
# de aparecer como "nao classificado".
FROM_ITENS = """
    FROM itens i
    JOIN notas n ON n.chave = i.nota_chave
    LEFT JOIN produtos p ON p.id = i.produto_id
    LEFT JOIN categorias c ON c.id = p.categoria_id
    LEFT JOIN raiz r ON r.id = c.id
"""


# A categoria pedida e TODA a descendencia dela: filtrar por `mercado` tem de pegar
# o que esta em `mercado-mercearia` (rollup, spec 05 §3).
CTE_DESCENDENTES = """
    descendentes(id) AS (
      SELECT id FROM categorias WHERE slug = :categoria_slug
      UNION ALL
      SELECT c.id FROM categorias c JOIN descendentes d ON c.parent_id = d.id
    )
"""


def conferir_filtros(conexao, categoria_slug=None, produto_id=None):
    """Levanta `LookupError` se a categoria ou o produto do filtro nao existem.

    ⭐ Sem isto, um slug com erro de digitacao devolveria "gasto zero" — uma
    resposta valida que mente. Melhor dizer que o filtro nao casa com nada.
    """
    if (
        categoria_slug
        and not conexao.execute(
            "SELECT 1 FROM categorias WHERE slug = ?", (categoria_slug,)
        ).fetchone()
    ):
        raise LookupError(f"nao existe categoria com slug {categoria_slug!r}")
    if (
        produto_id is not None
        and not conexao.execute("SELECT 1 FROM produtos WHERE id = ?", (produto_id,)).fetchone()
    ):
        raise LookupError(f"nao existe produto {produto_id}")


def filtros_de_gasto(de=None, ate=None, categoria_slug=None, loja_cnpj=None, produto_id=None):
    """`(WITH, WHERE, parametros)` comuns a todo gasto filtrado.

    O WHERE base e so nota valida; cada filtro acrescenta um pedaco FIXO, com o
    valor como parametro nomeado — nunca colado no SQL.

    ⭐ `de` e `ate` sao `'YYYY-MM'`, e a comparacao de TEXTO funciona porque o
    formato tem largura fixa: `'2026-06' <= '2026-10'` como string e como data.
    """
    ctes, filtros, parametros = [CTE_RAIZ], ["n.status = 'ok'"], {}
    if de:
        filtros.append("substr(n.dh_emi, 1, 7) >= :de")
        parametros["de"] = de
    if ate:
        filtros.append("substr(n.dh_emi, 1, 7) <= :ate")
        parametros["ate"] = ate
    if categoria_slug:
        ctes.append(CTE_DESCENDENTES)
        filtros.append("c.id IN (SELECT id FROM descendentes)")
        parametros["categoria_slug"] = categoria_slug
    if loja_cnpj:
        filtros.append("n.emit_cnpj = :loja_cnpj")
        parametros["loja_cnpj"] = loja_cnpj
    if produto_id is not None:
        filtros.append("i.produto_id = :produto_id")
        parametros["produto_id"] = produto_id
    return "WITH RECURSIVE " + ", ".join(ctes), " AND ".join(filtros), parametros


def consultar(conexao, select, sufixo="", **filtros):
    """Roda `SELECT <select>` sobre os itens filtrados. `sufixo` vem depois do WHERE."""
    conferir_filtros(conexao, filtros.get("categoria_slug"), filtros.get("produto_id"))
    com, onde, parametros = filtros_de_gasto(**filtros)
    return conexao.execute(
        f"{com} SELECT {select} {FROM_ITENS} WHERE {onde} {sufixo}", parametros
    ).fetchall()


def gasto_por_categoria(conexao, **filtros):
    """O gasto por categoria de NIVEL 1, com rollup, e o nao classificado a parte.

    Devolve `{"linhas": [{categoria_slug, nome, gasto}], "nao_classificado": {"gasto"}}`,
    linhas por slug. So entram categorias com gasto. `filtros`: os de `filtros_de_gasto`.

    🔴 "Nao classificado" e: item sem produto, produto sem categoria, e produto no
    BUCKET. O bucket e uma categoria de nivel 1 como outra qualquer para a CTE, e
    sem o `is_bucket` no CASE ele viraria uma linha "Nao Classificado" somada as
    categorias — fingindo que o dinheiro sem categoria cabe num teto.
    """
    linhas = consultar(
        conexao,
        "CASE WHEN c.id IS NULL OR c.is_bucket = 1 THEN NULL ELSE r.raiz_id END,"
        " SUM(i.valor_linha)",
        "GROUP BY 1",
        **filtros,
    )

    por_raiz = {raiz_id: gasto for raiz_id, gasto in linhas}
    nao_classificado = por_raiz.pop(None, 0)
    categorias = conexao.execute(
        "SELECT id, slug, nome FROM categorias WHERE parent_id IS NULL ORDER BY slug"
    ).fetchall()
    return {
        "linhas": [
            {"categoria_slug": slug, "nome": nome, "gasto": por_raiz[categoria_id]}
            for categoria_id, slug, nome in categorias
            if categoria_id in por_raiz
        ],
        "nao_classificado": {"gasto": nao_classificado},
    }

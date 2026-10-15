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


def filtro_periodo(de=None, ate=None):
    """O `WHERE` comum a todo gasto: so nota valida, e o intervalo de meses pedido.

    ⭐ `de` e `ate` sao `'YYYY-MM'`, e a comparacao de TEXTO funciona porque o
    formato tem largura fixa: `'2026-06' <= '2026-10'` como string e como data.
    """
    filtros, parametros = ["n.status = 'ok'"], {}
    if de:
        filtros.append("substr(n.dh_emi, 1, 7) >= :de")
        parametros["de"] = de
    if ate:
        filtros.append("substr(n.dh_emi, 1, 7) <= :ate")
        parametros["ate"] = ate
    return filtros, parametros


def gasto_por_categoria(conexao, de=None, ate=None):
    """O gasto por categoria de NIVEL 1, com rollup, e o nao classificado a parte.

    Devolve `{"linhas": [{categoria_slug, nome, gasto}], "nao_classificado": {"gasto"}}`,
    linhas por slug. So entram categorias com gasto.

    🔴 "Nao classificado" e: item sem produto, produto sem categoria, e produto no
    BUCKET. O bucket e uma categoria de nivel 1 como outra qualquer para a CTE, e
    sem o `is_bucket` no CASE ele viraria uma linha "Nao Classificado" somada as
    categorias — fingindo que o dinheiro sem categoria cabe num teto.
    """
    filtros, parametros = filtro_periodo(de, ate)
    linhas = conexao.execute(
        f"WITH RECURSIVE {CTE_RAIZ}"
        " SELECT CASE WHEN c.id IS NULL OR c.is_bucket = 1 THEN NULL ELSE r.raiz_id END,"
        " SUM(i.valor_linha)"
        f" {FROM_ITENS} WHERE {' AND '.join(filtros)} GROUP BY 1",
        parametros,
    ).fetchall()

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

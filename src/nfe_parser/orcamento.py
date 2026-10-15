"""Orcamento: teto de gasto por categoria de nivel 1 e mes — spec 04.

⭐ O orcamento so GUARDA o teto; o realizado vem de `gastos.py`, o mesmo motor dos
relatorios (spec 05). Assim "quanto gastei em Mercado em junho" tem uma resposta
so, e o orcamento nunca diverge do relatorio.

⚠️ Nenhuma funcao daqui commita: quem abre a transacao e `operacoes.py`.
"""

import re
from datetime import UTC, datetime

from nfe_parser.gastos import gasto_por_categoria

_MES = re.compile(r"\d{4}-(0[1-9]|1[0-2])")


def _validar_mes(mes):
    if not isinstance(mes, str) or not _MES.fullmatch(mes):
        raise ValueError(f"mes tem de ser 'AAAA-MM', com mes de 01 a 12; recebi {mes!r}")


def _validar_limite(limite):
    """Inteiro positivo, em centavos.

    ⚠️ `bool` e subclasse de `int` em Python (`True == 1`), entao `isinstance`
    sozinho aceitaria `True` como um centavo. Por isso a exclusao explicita.
    """
    if isinstance(limite, bool) or not isinstance(limite, int) or limite <= 0:
        raise ValueError(f"o limite e um inteiro de centavos maior que zero; recebi {limite!r}")


def definir_orcamento(conexao, categoria_slug, mes, limite):
    """Cria o teto de `categoria_slug` em `mes`. Devolve o id.

    🔴 So categoria de NIVEL 1 e nunca o bucket (spec 04 §2). Teto em subcategoria
    e roadmap; teto no bucket seria orcar o dinheiro que nao se sabe onde foi.
    """
    _validar_mes(mes)
    _validar_limite(limite)

    linha = conexao.execute(
        "SELECT id, parent_id, is_bucket FROM categorias WHERE slug = ?", (categoria_slug,)
    ).fetchone()
    if linha is None:
        raise LookupError(f"nao existe categoria com slug {categoria_slug!r}")
    categoria_id, parent_id, is_bucket = linha
    if is_bucket:
        raise ValueError(f"{categoria_slug!r} e o bucket; o gasto sem categoria nao tem teto")
    if parent_id is not None:
        raise ValueError(
            f"{categoria_slug!r} e subcategoria; no MVP o teto e por categoria de nivel 1"
        )

    if conexao.execute(
        "SELECT 1 FROM orcamentos WHERE categoria_id = ? AND mes = ?", (categoria_id, mes)
    ).fetchone():
        raise ValueError(f"ja existe orcamento de {categoria_slug!r} em {mes}; altere o limite")

    agora = datetime.now(UTC).isoformat()
    return conexao.execute(
        "INSERT INTO orcamentos (categoria_id, mes, limite, criado_em, atualizado_em)"
        " VALUES (?, ?, ?, ?, ?)",
        (categoria_id, mes, limite, agora, agora),
    ).lastrowid


def alterar_limite(conexao, orcamento_id, limite):
    _validar_limite(limite)
    cursor = conexao.execute(
        "UPDATE orcamentos SET limite = ?, atualizado_em = ? WHERE id = ?",
        (limite, datetime.now(UTC).isoformat(), orcamento_id),
    )
    if cursor.rowcount == 0:
        raise LookupError(f"nao existe orcamento {orcamento_id}")


def apagar_orcamento(conexao, orcamento_id):
    cursor = conexao.execute("DELETE FROM orcamentos WHERE id = ?", (orcamento_id,))
    if cursor.rowcount == 0:
        raise LookupError(f"nao existe orcamento {orcamento_id}")


def orcamento(conexao, orcamento_id):
    """`{id, categoria_slug, mes, limite}`, ou None se nao existe."""
    linha = conexao.execute(
        "SELECT o.id, c.slug, o.mes, o.limite FROM orcamentos o"
        " JOIN categorias c ON c.id = o.categoria_id WHERE o.id = ?",
        (orcamento_id,),
    ).fetchone()
    if linha is None:
        return None
    return dict(zip(("id", "categoria_slug", "mes", "limite"), linha))


def _linha(slug, nome, teto, gasto):
    limite = teto["limite"] if teto else None
    saldo = limite - gasto if limite is not None else None
    return {
        "orcamento_id": teto["id"] if teto else None,
        "categoria_slug": slug,
        "nome": nome,
        "limite": limite,
        "gasto": gasto,
        "saldo": saldo,
        "pct": round(gasto / limite, 4) if limite else None,
        "estouro": saldo is not None and saldo < 0,
    }


def orcamentos_do_mes(conexao, mes):
    """O readout do mes: limite · gasto · saldo por categoria de nivel 1.

    ⭐ Entra toda categoria com TETO no mes ou com GASTO no mes. A categoria com
    gasto e sem teto aparece com `limite` None — e o jeito de ver onde o dinheiro
    foi e decidir criar o teto, em vez de o gasto sumir da tela.

    ⚠️ `totais.gasto` e TODO o gasto do mes, inclusive o nao classificado: e o
    numero honesto de "quanto saiu". Comparar com `totais.limite` mostra quanto do
    gasto esta fora de qualquer teto.
    """
    _validar_mes(mes)
    realizado = gasto_por_categoria(conexao, de=mes, ate=mes)
    gastos = {linha["categoria_slug"]: linha for linha in realizado["linhas"]}
    tetos = {
        slug: {"id": orcamento_id, "nome": nome, "limite": limite}
        for orcamento_id, slug, nome, limite in conexao.execute(
            "SELECT o.id, c.slug, c.nome, o.limite FROM orcamentos o"
            " JOIN categorias c ON c.id = o.categoria_id WHERE o.mes = ?",
            (mes,),
        )
    }

    linhas = []
    for slug in sorted(gastos.keys() | tetos.keys()):
        gasto = gastos.get(slug, {}).get("gasto", 0)
        nome = (tetos.get(slug) or gastos[slug])["nome"]
        linhas.append(_linha(slug, nome, tetos.get(slug), gasto))

    nao_classificado = realizado["nao_classificado"]
    return {
        "mes": mes,
        "linhas": linhas,
        "nao_classificado": nao_classificado,
        "totais": {
            "limite": sum(teto["limite"] for teto in tetos.values()),
            "gasto": sum(linha["gasto"] for linha in linhas) + nao_classificado["gasto"],
        },
    }

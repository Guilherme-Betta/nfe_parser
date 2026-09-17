import sqlite3
from datetime import UTC, datetime
from nfe_parser.produtos import resolver_produto_por_gtin, resolver_produto_por_texto


def resolver_produto_do_item(conexao, item, emit_cnpj):
    if item["gtin"]:
        return resolver_produto_por_gtin(conexao, item["gtin"], item["descricao"])
    return resolver_produto_por_texto(conexao, item["descricao"], emit_cnpj)


def persistir_nota(
    conexao: sqlite3.Connection, extraido: dict, importacao_id: int | None = None
) -> str:
    """Persiste uma nota e seus itens no banco de dados."""

    # Verificando se a nota já existe
    chave = extraido["nota"]["chave"]
    query_check = "SELECT 1 FROM notas WHERE chave = ?"
    if conexao.execute(query_check, (chave,)).fetchone():
        return "duplicada"

    # Inserindo a nota
    nota = extraido["nota"]
    campos_nota = [
        "chave",
        "modelo",
        "serie",
        "numero",
        "dh_emi",
        "emit_nome",
        "emit_cnpj",
        "emit_municipio",
        "emit_uf",
        "valor_total",
        "forma_pagamento",
        "xml_raw",
        "importacao_id",
        "criado_em",
    ]
    valores_nota = [
        nota["chave"],
        nota["modelo"],
        nota["serie"],
        nota["numero"],
        nota["dh_emi"],
        nota["emit_nome"],
        nota["emit_cnpj"],
        nota["emit_municipio"],
        nota["emit_uf"],
        nota["valor_total"],
        nota["forma_pagamento"],
        nota["xml_raw"],
        importacao_id,
        datetime.now(UTC).isoformat(),
    ]

    placeholders = ", ".join("?" for _ in campos_nota)
    query_nota = f"INSERT INTO notas ({', '.join(campos_nota)}) VALUES ({placeholders})"
    conexao.execute(query_nota, valores_nota)

    # Inserindo os itens
    itens = extraido["itens"]
    campos_itens = [
        "nota_chave",
        "n_item",
        "descricao",
        "cprod",
        "ncm",
        "gtin",
        "quantidade",
        "unidade",
        "valor_unitario",
        "valor_linha",
        "criado_em",
        "produto_id",
    ]
    for item in itens:
        produto_id = resolver_produto_do_item(conexao, item, nota["emit_cnpj"])
        valores_itens = [
            nota["chave"],
            item["n_item"],
            item["descricao"],
            item["cprod"],
            item["ncm"],
            item["gtin"],
            item["quantidade"],
            item["unidade"],
            item["valor_unitario"],
            item["valor_linha"],
            datetime.now(UTC).isoformat(),
            produto_id,
        ]
        placeholders = ", ".join("?" for _ in campos_itens)
        query_itens = f"INSERT INTO itens ({', '.join(campos_itens)}) VALUES ({placeholders})"
        conexao.execute(query_itens, valores_itens)

    return "nova"

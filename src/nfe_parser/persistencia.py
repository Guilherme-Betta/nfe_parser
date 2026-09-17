"""Uma nota extraida do XML vira linhas no banco: `notas`, `itens`, `produtos`.

A story 013 acrescentou a terceira tabela a essa lista. Ate ela, um item entrava
como evento de compra solto; agora cada item resolve QUAL produto ele e, e grava
esse `produto_id` junto.

🔴 NENHUMA FUNCAO DAQUI CHAMA `conexao.commit()`, e isso mudou na 013. Antes
`persistir_nota` commitava por conta propria, e era a divida `a`: resolver o
produto e inserir o item TEM de ser a mesma transacao. Com o commit la dentro, a
nota e os itens ja estariam gravados quando a resolucao de um item POSTERIOR
falhasse, e o banco ficaria com item sem produto, sem sintoma nenhum.

⭐ A regra agora e a mesma que `produtos.py`, `categorizacao.py`, `seed.py` e
`taxonomia.py` ja anunciam: quem abriu a transacao e que a fecha. Quem abre o
lote e `importar`.

⛔ Este modulo NAO classifica. O produto nasce com `categoria_id` e `origem`
NULL, que e o estado "pendente" que `varredura.py` procura depois.
"""

import sqlite3
from datetime import UTC, datetime

from nfe_parser.produtos import resolver_produto_por_gtin, resolver_produto_por_texto


def resolver_produto_do_item(conexao, item, emit_cnpj):
    """Despacha um item de nota para a resolucao de identidade que serve a ele.

    ⭐ E o despachante que faltava entre as duas funcoes de `produtos.py` — a
    divida `g`. A regra e curta: quem tem codigo de barras se identifica por ele;
    quem nao tem cai na chave de texto, que so vale DENTRO da loja que emitiu.

    🔴 E ele mora AQUI, e nao em `produtos.py`, de proposito. A regra de despacho
    e uma politica sobre ITEM DE NOTA, e aquele modulo declara no cabecalho que
    nao sabe o que e um item: ele fala de GTIN e de texto+CNPJ, nunca de `itens`.
    Este modulo existe justamente para transformar item de nota em linha de
    banco, e e aqui que a politica pertence.

    ⚠️ Item sem GTIN em nota sem CNPJ levanta `ValueError`, vindo de
    `resolver_produto_por_texto`. ⛔ O erro SOBE: engoli-lo deixaria `produto_id`
    NULL em silencio, e uma chave de texto sem loja nao identificaria nada.
    """

    if item["gtin"]:
        return resolver_produto_por_gtin(conexao, item["gtin"], item["descricao"])
    return resolver_produto_por_texto(conexao, item["descricao"], emit_cnpj)


def persistir_nota(
    conexao: sqlite3.Connection, extraido: dict, importacao_id: int | None = None
) -> str:
    """Persiste uma nota e seus itens, resolvendo a identidade de cada item.

    Devolve `"duplicada"` se a chave ja existe, e `"nova"` se gravou.

    ⭐ A checagem de duplicada e a PRIMEIRA coisa, e continua sendo: nota repetida
    sai pela porta de cima sem criar produto nenhum.

    ⚠️ Dentro do laco, a ordem importa — resolver ANTES de inserir. Nao porque o
    SQL exija, mas porque as duas coisas tem de estar na mesma transacao, e e
    essa transacao que o `commit` de quem chamou vai fechar.
    """

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

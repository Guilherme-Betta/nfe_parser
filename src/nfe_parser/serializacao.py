import json

def de_centavos(centavos: int) -> str:
    sinal = "-" if centavos < 0 else ""
    valor = abs(centavos)
    reais = valor // 100
    centavos = valor % 100
    return f"{sinal}{reais}.{centavos:02d}"

def nota_para_json(conexao, chave: str) -> str | None:
    cursor = conexao.execute(
        "SELECT chave, modelo, serie, numero, dh_emi, emit_nome, emit_cnpj,"
        " emit_municipio, emit_uf, valor_total, forma_pagamento, status, cancelado_em"
        " FROM notas WHERE chave = ?",
        (chave,),
    )
    linha = cursor.fetchone()
    if linha is None:
        return None
    colunas = [d[0] for d in cursor.description]
    dados = dict(zip(colunas, linha))
    
    saida = {
        "chave": dados["chave"],
        "modelo": dados["modelo"],
        "serie": dados["serie"],
        "numero": dados["numero"],
        "dh_emi": dados["dh_emi"],
        "emit_nome": dados["emit_nome"],
        "emit_cnpj": dados["emit_cnpj"],
        "emit_municipio": dados["emit_municipio"],
        "emit_uf": dados["emit_uf"],
        "valor_total_centavos": dados["valor_total"],
        "valor_total": de_centavos(dados["valor_total"]),
        "forma_pagamento": dados["forma_pagamento"],
        "status": dados["status"],
        "cancelado_em": dados["cancelado_em"],
    }
    
    cursor_itens = conexao.execute(
        "SELECT n_item, descricao, cprod, ncm, gtin, quantidade, unidade,"
        " valor_unitario, valor_linha"
        " FROM itens WHERE nota_chave = ? ORDER BY n_item",
        (chave,),
    )
    
    itens = []
    for linha in cursor_itens.fetchall():
        colunas = [d[0] for d in cursor_itens.description]
        item = dict(zip(colunas, linha))
        item["valor_linha_centavos"] = item["valor_linha"]
        item["valor_linha"] = de_centavos(item["valor_linha"])
        # Reorganizar as chaves para garantir a ordem correta
        item = {
            "n_item": item["n_item"],
            "descricao": item["descricao"],
            "cprod": item["cprod"],
            "ncm": item["ncm"],
            "gtin": item["gtin"],
            "quantidade": item["quantidade"],
            "unidade": item["unidade"],
            "valor_unitario": item["valor_unitario"],
            "valor_linha_centavos": item["valor_linha_centavos"],
            "valor_linha": item["valor_linha"],
        }
        itens.append(item)
    
    saida["itens"] = itens
    
    return json.dumps(saida, ensure_ascii=False)

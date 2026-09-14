from datetime import datetime, timezone
import sqlite3

def persistir_nota(conexao: sqlite3.Connection, extraido: dict, importacao_id: int | None = None) -> str:
    """Persiste uma nota e seus itens no banco de dados."""
    
    # Inserindo a nota
    nota = extraido["nota"]
    campos_nota = [
        "chave", "modelo", "serie", "numero", "dh_emi", "emit_nome", "emit_cnpj",
        "emit_municipio", "emit_uf", "valor_total", "forma_pagamento", "xml_raw",
        "importacao_id", "criado_em"
    ]
    valores_nota = [
        nota["chave"], nota["modelo"], nota["serie"], nota["numero"], nota["dh_emi"],
        nota["emit_nome"], nota["emit_cnpj"], nota["emit_municipio"], nota["emit_uf"],
        nota["valor_total"], nota["forma_pagamento"], nota["xml_raw"],
        importacao_id, datetime.now(timezone.utc).isoformat()
    ]
    
    placeholders = ", ".join("?" for _ in campos_nota)
    query_nota = f"INSERT INTO notas ({', '.join(campos_nota)}) VALUES ({placeholders})"
    conexao.execute(query_nota, valores_nota)
    
    # Inserindo os itens
    itens = extraido["itens"]
    campos_itens = [
        "nota_chave", "n_item", "descricao", "cprod", "ncm", "gtin", "quantidade",
        "unidade", "valor_unitario", "valor_linha", "criado_em"
    ]
    for item in itens:
        valores_itens = [
            nota["chave"], item["n_item"], item["descricao"], item["cprod"], item["ncm"],
            item["gtin"], item["quantidade"], item["unidade"], item["valor_unitario"],
            item["valor_linha"], datetime.now(timezone.utc).isoformat()
        ]
        placeholders = ", ".join("?" for _ in campos_itens)
        query_itens = f"INSERT INTO itens ({', '.join(campos_itens)}) VALUES ({placeholders})"
        conexao.execute(query_itens, valores_itens)
    
    # Commitando as mudanças
    conexao.commit()
    
    return "nova"

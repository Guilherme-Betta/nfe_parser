import unicodedata
from datetime import UTC, datetime

PERMITIDOS = "abcdefghijklmnopqrstuvwxyz0123456789"

def normalizar_descricao(descricao: str) -> str:
    descricao = descricao.lower()
    descricao = unicodedata.normalize("NFD", descricao)
    descricao = ''.join(c for c in descricao if unicodedata.category(c) != "Mn")
    descricao = ''.join(c if c in PERMITIDOS else " " for c in descricao)
    descricao = " ".join(descricao.split())
    return descricao

def resolver_produto_por_gtin(conexao, gtin, descricao_exemplo):
    cursor = conexao.execute("SELECT id FROM produtos WHERE gtin = ?", (gtin,))
    resultado = cursor.fetchone()
    
    if resultado:
        return resultado[0]
    
    criado_em = datetime.now(UTC).isoformat()
    cursor.execute("""
        INSERT INTO produtos (identidade_origem, gtin, descricao_exemplo, criado_em, atualizado_em)
        VALUES (?, ?, ?, ?, ?)
    """, ('gtin', gtin, descricao_exemplo, criado_em, criado_em))
    
    return cursor.lastrowid

def resolver_produto_por_texto(conexao, descricao, emit_cnpj):
    normalizada = normalizar_descricao(descricao)
    cursor = conexao.execute("""
        SELECT id FROM produtos
        WHERE gtin IS NULL AND descricao_normalizada = ? AND emit_cnpj = ?
    """, (normalizada, emit_cnpj))
    resultado = cursor.fetchone()
    
    if resultado:
        return resultado[0]
    
    criado_em = datetime.now(UTC).isoformat()
    cursor.execute("""
        INSERT INTO produtos (identidade_origem, descricao_normalizada, emit_cnpj, descricao_exemplo, criado_em, atualizado_em)
        VALUES (?, ?, ?, ?, ?, ?)
    """, ('texto', normalizada, emit_cnpj, descricao, criado_em, criado_em))
    
    return cursor.lastrowid

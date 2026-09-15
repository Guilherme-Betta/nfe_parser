import sqlite3

def _migracao_01_esquema_classificacao(conexao):
    conexao.execute("""
        CREATE TABLE IF NOT EXISTS categorias (
          id INTEGER PRIMARY KEY,
          slug TEXT NOT NULL UNIQUE,
          nome TEXT NOT NULL,
          parent_id INTEGER REFERENCES categorias(id),
          is_bucket INTEGER NOT NULL DEFAULT 0
        )
    """)
    conexao.execute("""
        CREATE TABLE IF NOT EXISTS ncm_ancora (
          prefixo TEXT PRIMARY KEY,
          categoria_id INTEGER NOT NULL REFERENCES categorias(id)
        )
    """)
    conexao.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
          id INTEGER PRIMARY KEY,
          identidade_origem TEXT NOT NULL CHECK (identidade_origem IN ('gtin','texto')),
          gtin TEXT,
          descricao_normalizada TEXT, emit_cnpj TEXT,
          descricao_exemplo TEXT,
          categoria_id INTEGER REFERENCES categorias(id),
          origem TEXT CHECK (origem IN ('manual','memoria','ncm','llm')),
          confianca REAL,
          criado_em TEXT NOT NULL, atualizado_em TEXT NOT NULL
        )
    """)
    conexao.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ux_produtos_gtin
          ON produtos(gtin) WHERE gtin IS NOT NULL
    """)
    conexao.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ux_produtos_texto
          ON produtos(descricao_normalizada, emit_cnpj) WHERE gtin IS NULL
    """)
    conexao.execute("""
        CREATE TABLE IF NOT EXISTS tags (id INTEGER PRIMARY KEY, nome TEXT NOT NULL UNIQUE)
    """)
    conexao.execute("""
        CREATE TABLE IF NOT EXISTS produto_tags (
          produto_id INTEGER NOT NULL REFERENCES produtos(id),
          tag_id INTEGER NOT NULL REFERENCES tags(id),
          PRIMARY KEY (produto_id, tag_id)
        )
    """)


def _migracao_02_produto_id_em_itens(conexao):
    conexao.execute("ALTER TABLE itens ADD COLUMN produto_id INTEGER REFERENCES produtos(id)")
    conexao.execute("CREATE INDEX IF NOT EXISTS idx_itens_produto ON itens(produto_id)")

MIGRACOES = [_migracao_01_esquema_classificacao, _migracao_02_produto_id_em_itens]

def _migracao_01_esquema_classificacao(conexao):
    conexao.execute("""
        CREATE TABLE IF NOT EXISTS categorias (
          id INTEGER PRIMARY KEY,
          slug TEXT NOT NULL UNIQUE,
          nome TEXT NOT NULL,
          parent_id INTEGER REFERENCES categorias(id),
          is_bucket INTEGER NOT NULL DEFAULT 0
        )
    """)
    conexao.execute("""
        CREATE TABLE IF NOT EXISTS ncm_ancora (
          prefixo TEXT PRIMARY KEY,
          categoria_id INTEGER NOT NULL REFERENCES categorias(id)
        )
    """)
    conexao.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
          id INTEGER PRIMARY KEY,
          identidade_origem TEXT NOT NULL CHECK (identidade_origem IN ('gtin','texto')),
          gtin TEXT,
          descricao_normalizada TEXT, emit_cnpj TEXT,
          descricao_exemplo TEXT,
          categoria_id INTEGER REFERENCES categorias(id),
          origem TEXT CHECK (origem IN ('manual','memoria','ncm','llm')),
          confianca REAL,
          criado_em TEXT NOT NULL, atualizado_em TEXT NOT NULL
        )
    """)
    conexao.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ux_produtos_gtin
          ON produtos(gtin) WHERE gtin IS NOT NULL
    """)
    conexao.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ux_produtos_texto
          ON produtos(descricao_normalizada, emit_cnpj) WHERE gtin IS NULL
    """)
    conexao.execute("""
        CREATE TABLE IF NOT EXISTS tags (id INTEGER PRIMARY KEY, nome TEXT NOT NULL UNIQUE)
    """)
    conexao.execute("""
        CREATE TABLE IF NOT EXISTS produto_tags (
          produto_id INTEGER NOT NULL REFERENCES produtos(id),
          tag_id INTEGER NOT NULL REFERENCES tags(id),
          PRIMARY KEY (produto_id, tag_id)
        )
    """)


def _migracao_02_produto_id_em_itens(conexao):
    conexao.execute("ALTER TABLE itens ADD COLUMN produto_id INTEGER REFERENCES produtos(id)")
    conexao.execute("CREATE INDEX IF NOT EXISTS idx_itens_produto ON itens(produto_id)")

def versao_do_banco(conexao) -> int:
    return conexao.execute("PRAGMA user_version").fetchone()[0]


def aplicar_migracoes(conexao, migracoes=None) -> int:
    if migracoes is None:
        migracoes = MIGRACOES

    atual = versao_do_banco(conexao)
    for indice, migracao in enumerate(migracoes):
        versao = indice + 1
        if versao <= atual:
            continue
        conexao.execute("BEGIN")
        try:
            migracao(conexao)
            conexao.execute(f"PRAGMA user_version = {versao}")
            conexao.execute("COMMIT")
        except Exception:
            conexao.execute("ROLLBACK")
            raise

    return versao_do_banco(conexao)

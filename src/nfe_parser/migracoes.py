"""Versionamento do esquema do banco, via `PRAGMA user_version` do SQLite.

O `criar_esquema` de `banco.py` e idempotente — todo comando dele tem
`IF NOT EXISTS` — e por isso pode rodar a cada abertura. `ALTER TABLE` nao tem
essa propriedade: rodar duas vezes levanta `duplicate column name`. Este modulo
existe para dar um lugar a comandos que so podem rodar UMA vez.

A versao mora no proprio arquivo do banco (`PRAGMA user_version`), nao numa
tabela de controle: e um inteiro que o SQLite ja guarda no cabecalho, de graca.

⛔ Uma migracao ja aplicada e IMUTAVEL, pela mesma razao que um commit publicado
e: pode existir banco no disco marcado com aquela versao, e editar a funcao nao
alcancaria esse banco — ele ficaria meio migrado, sem sintoma. Mudanca de
esquema e sempre uma migracao NOVA no fim de `MIGRACOES`.
"""


def versao_do_banco(conexao) -> int:
    """Le a versao de esquema gravada no arquivo. Banco novo devolve 0."""

    return conexao.execute("PRAGMA user_version").fetchone()[0]


def aplicar_migracoes(conexao, migracoes=None) -> int:
    """Roda as migracoes que faltam, em ordem, e devolve a versao final.

    O parametro `migracoes` existe para os testes injetarem uma lista propria:
    exercitar o registro real amarraria o oraculo de uma tarefa ao numero de
    migracoes que as tarefas seguintes acrescentam.

    Cada migracao roda dentro da SUA transacao, com a gravacao da versao junto.
    Isso nao e zelo: se a versao avancasse sem a migracao ter terminado, a
    abertura seguinte pularia essa migracao e o banco ficaria quebrado para
    sempre, sem nada no codigo denunciando. DDL do SQLite obedece transacao, e o
    `user_version` volta atras no `ROLLBACK` junto com o resto.

    ⛔ E por isso que nenhuma migracao pode usar `executescript`: ele faz COMMIT
    implicito antes de rodar, o que destruiria a transacao aberta aqui.

    A excecao sobe para quem chamou. Migracao que falha e defeito de programa, e
    engoli-la deixaria o banco num estado que ninguem pediu.
    """

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


def _migracao_01_esquema_classificacao(conexao):
    """Cria as tabelas do paragrafo 2 de `specs/02_spec_classificacao.md`.

    Nenhuma linha de dado: o seed da taxonomia e outra story.

    Os dois indices sao PARCIAIS, e o `WHERE` de cada um e a razao de ele
    existir: a identidade de um produto e o GTIN quando ele tem GTIN, e o par
    (descricao normalizada, CNPJ da loja) quando nao tem. Sem o `WHERE`, o
    primeiro indice recusaria o segundo produto sem codigo de barras — que e a
    maioria das linhas de uma NFC-e.
    """

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
    """Liga cada item ao seu produto. O unico ponto nao-idempotente da spec 02.

    A coluna nasce NULL em todas as linhas antigas, e essa e a resposta honesta:
    ninguem sabe ainda qual produto e cada item. Quem preenche e outra story.

    ⛔ Nao ha `IF NOT EXISTS` para `ADD COLUMN` no SQLite, e nao deve haver
    `try/except` em volta: o controle de versao ja garante a chamada unica, e um
    `except` aqui mascararia o unico sintoma de um executor quebrado.
    """

    conexao.execute("ALTER TABLE itens ADD COLUMN produto_id INTEGER REFERENCES produtos(id)")
    conexao.execute("CREATE INDEX IF NOT EXISTS idx_itens_produto ON itens(produto_id)")


# A POSICAO E A VERSAO: indice 0 e a migracao v1, indice 1 e a v2. A lista torna
# impossivel um numero de versao duplicado ou um buraco na sequencia.
MIGRACOES = [_migracao_01_esquema_classificacao, _migracao_02_produto_id_em_itens]

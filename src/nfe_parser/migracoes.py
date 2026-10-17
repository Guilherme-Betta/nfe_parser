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
    exercitar o registro real amarraria esses testes ao numero de migracoes que
    existirem, e toda migracao nova os quebraria.

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

    Nenhuma linha de dado: quem preenche a taxonomia e o seed (`seed.py`), que ⛔
    NAO e migracao — ele precisa poder rodar de novo, e migracao roda uma vez so.

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
    ninguem sabe qual produto e cada item. Quem preenche e `persistencia.py`, para
    os itens importados daqui em diante; ⛔ nao ha backfill dos antigos.

    ⛔ Nao ha `IF NOT EXISTS` para `ADD COLUMN` no SQLite, e nao deve haver
    `try/except` em volta: o controle de versao ja garante a chamada unica, e um
    `except` aqui mascararia o unico sintoma de um executor quebrado.
    """

    conexao.execute("ALTER TABLE itens ADD COLUMN produto_id INTEGER REFERENCES produtos(id)")
    conexao.execute("CREATE INDEX IF NOT EXISTS idx_itens_produto ON itens(produto_id)")


def _migracao_03_lapide_de_categorias(conexao):
    """Guarda o slug de cada categoria que o usuario apagou. A "lapide".

    Sem ela, apagar categoria nao e definitivo: o seed (`seed.py`) insere o que
    falta, e uma categoria apagada e, para ele, uma categoria que falta. Ela
    voltaria no proximo `carregar_seed_padrao` — com `id` novo e sem os produtos
    que tinha, sendo prestativa e desfazendo uma decisao de quem usa o programa.

    ⛔ NAO ha `REFERENCES categorias(id)`, e nao e esquecimento: a linha de
    `categorias` nao existe mais. E exatamente isso que esta tabela registra.

    ⭐ Tabela separada, e nao uma coluna `apagada_em` em `categorias` (o "soft
    delete"): com a coluna, a linha continuaria la, e TODA consulta futura sobre
    categorias — relatorio, UI, soma por categoria — passaria a precisar de
    `WHERE apagada_em IS NULL`. Esquecer o filtro em um lugar so ja volta a
    mostrar a categoria apagada. Aqui, quem esta em `categorias` E uma categoria.

    ⚠️ O `slug` e a chave, e nao o `id`, porque e por slug que o seed casa. Um
    `id` de categoria apagada nao significa mais nada para ninguem.
    """

    conexao.execute("""
        CREATE TABLE IF NOT EXISTS categorias_apagadas (
          slug TEXT PRIMARY KEY,
          apagada_em TEXT NOT NULL
        )
    """)


def _migracao_04_orcamentos(conexao):
    """O teto de gasto por categoria e mes — spec 04 §2.

    ⭐ `ON DELETE CASCADE`: apagar a categoria apaga os tetos dela. Sem isso, a
    chave estrangeira impediria `taxonomia.apagar_categoria` de apagar qualquer
    categoria orcada — e ensinar `taxonomia.py` a conhecer esta tabela misturaria
    o nucleo da spec 02 com um componente que veio depois. O teto era daquela
    categoria; o gasto dela vai para o bucket, que nao tem teto.

    ⚠️ As regras de negocio (so nivel 1, nunca o bucket, `limite > 0`) moram em
    `orcamento.py`, nao em CHECK: "nivel 1" depende de OUTRA linha (o
    `parent_id` da categoria), e CHECK do SQLite so enxerga a linha que grava.
    """

    conexao.execute("""
        CREATE TABLE IF NOT EXISTS orcamentos (
          id INTEGER PRIMARY KEY,
          categoria_id INTEGER NOT NULL REFERENCES categorias(id) ON DELETE CASCADE,
          mes TEXT NOT NULL,
          limite INTEGER NOT NULL,
          criado_em TEXT NOT NULL, atualizado_em TEXT NOT NULL,
          UNIQUE (categoria_id, mes)
        )
    """)
    conexao.execute("CREATE INDEX IF NOT EXISTS idx_orcamentos_mes ON orcamentos(mes)")


def _migracao_05_eventos(conexao):
    """Guarda todo evento de NF-e, e o log de importacao passa a aceitar `evento_registrado`.

    Spec 01 §2 e §6.2; decisao do Gui de 2026-10-16.

    ⛔ `eventos.chave` NAO tem `REFERENCES notas(chave)`: um evento pode chegar
    ANTES da nota (outro lote), e e justamente para ele estar la quando a nota
    chegar que ele e guardado.

    🔴 O CHECK de `importacao_arquivos.resultado` nao se altera no SQLite: so
    reconstruindo a tabela. O caminho e o que a documentacao do SQLite manda —
    criar a nova, copiar, apagar a velha, renomear —, tudo na transacao que o
    executor abriu. Nenhuma tabela aponta para `importacao_arquivos`, entao o
    `DROP` nao esbarra em chave estrangeira. O `criar_esquema` de `banco.py`
    continua com o CHECK antigo, e nao faz mal: o `IF NOT EXISTS` dele nunca mais
    cria esta tabela num banco migrado, e num banco novo esta migracao roda logo
    depois e a reconstroi.
    """

    conexao.execute("""
        CREATE TABLE IF NOT EXISTS eventos (
          id INTEGER PRIMARY KEY,
          chave TEXT NOT NULL,
          tp_evento TEXT NOT NULL,
          n_seq INTEGER NOT NULL,
          dh_evento TEXT,
          descricao TEXT,
          correcao TEXT,
          xml_raw TEXT NOT NULL,
          importacao_id INTEGER REFERENCES importacoes(id),
          criado_em TEXT NOT NULL,
          UNIQUE (chave, tp_evento, n_seq)
        )
    """)
    conexao.execute("CREATE INDEX IF NOT EXISTS idx_eventos_chave ON eventos(chave)")

    conexao.execute("""
        CREATE TABLE importacao_arquivos_v5 (
          id INTEGER PRIMARY KEY,
          importacao_id INTEGER NOT NULL REFERENCES importacoes(id),
          arquivo TEXT, arquivo_hash TEXT, chave TEXT,
          resultado TEXT NOT NULL CHECK (resultado IN (
            'nova','duplicada','invalida',
            'cancelamento_aplicado','cancelamento_orfao','nao_suportado_sat',
            'evento_registrado')),
          detalhe TEXT
        )
    """)
    conexao.execute(
        "INSERT INTO importacao_arquivos_v5"
        " (id, importacao_id, arquivo, arquivo_hash, chave, resultado, detalhe)"
        " SELECT id, importacao_id, arquivo, arquivo_hash, chave, resultado, detalhe"
        " FROM importacao_arquivos"
    )
    conexao.execute("DROP TABLE importacao_arquivos")
    conexao.execute("ALTER TABLE importacao_arquivos_v5 RENAME TO importacao_arquivos")


# A POSICAO E A VERSAO: indice 0 e a migracao v1, indice 1 e a v2. A lista torna
# impossivel um numero de versao duplicado ou um buraco na sequencia.
MIGRACOES = [
    _migracao_01_esquema_classificacao,
    _migracao_02_produto_id_em_itens,
    _migracao_03_lapide_de_categorias,
    _migracao_04_orcamentos,
    _migracao_05_eventos,
]

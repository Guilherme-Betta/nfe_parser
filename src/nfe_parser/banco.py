import sqlite3

from nfe_parser.migracoes import aplicar_migracoes


def criar_esquema(conexao):
    """Executa o DDL do paragrafo 2 de specs/01_spec_parser_modelo.md.

    Idempotente: todo CREATE tem IF NOT EXISTS, entao rodar de novo num banco
    ja populado nao apaga nem duplica nada.
    """

    ddl = """
    CREATE TABLE IF NOT EXISTS importacoes (
      id INTEGER PRIMARY KEY,
      origem TEXT NOT NULL, iniciado_em TEXT NOT NULL, finalizado_em TEXT,
      total_arquivos INTEGER DEFAULT 0, notas_novas INTEGER DEFAULT 0,
      duplicadas INTEGER DEFAULT 0, invalidas INTEGER DEFAULT 0,
      cancelamentos_aplicados INTEGER DEFAULT 0, nao_suportadas INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS notas (
      chave TEXT PRIMARY KEY,                    -- 44 dígitos
      modelo INTEGER NOT NULL,                   -- 55 | 65
      serie INTEGER, numero INTEGER, dh_emi TEXT NOT NULL,
      emit_nome TEXT, emit_cnpj TEXT, emit_municipio TEXT, emit_uf TEXT,
      valor_total INTEGER NOT NULL,              -- centavos (vNF)
      forma_pagamento TEXT,
      status TEXT NOT NULL DEFAULT 'ok' CHECK (status IN ('ok','cancelada')),
      cancelado_em TEXT, xml_raw TEXT NOT NULL,
      importacao_id INTEGER REFERENCES importacoes(id), criado_em TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_notas_dh_emi ON notas(dh_emi);

    CREATE TABLE IF NOT EXISTS itens (
      id INTEGER PRIMARY KEY,
      nota_chave TEXT NOT NULL REFERENCES notas(chave),
      n_item INTEGER NOT NULL,                   -- nItem
      descricao TEXT NOT NULL,                   -- xProd (cru)
      cprod TEXT, ncm TEXT, gtin TEXT,           -- gtin NULL quando "SEM GTIN"
      quantidade TEXT NOT NULL, unidade TEXT,
      valor_unitario TEXT, valor_linha INTEGER NOT NULL,  -- centavos (vProd)
      criado_em TEXT NOT NULL,
      UNIQUE (nota_chave, n_item)
    );
    CREATE INDEX IF NOT EXISTS idx_itens_nota ON itens(nota_chave);
    CREATE INDEX IF NOT EXISTS idx_itens_ncm  ON itens(ncm);
    CREATE INDEX IF NOT EXISTS idx_itens_gtin ON itens(gtin);

    CREATE TABLE IF NOT EXISTS importacao_arquivos (  -- log por arquivo do lote
      id INTEGER PRIMARY KEY,
      importacao_id INTEGER NOT NULL REFERENCES importacoes(id),
      arquivo TEXT, arquivo_hash TEXT, chave TEXT,
      resultado TEXT NOT NULL CHECK (resultado IN (
        'nova','duplicada','invalida',
        'cancelamento_aplicado','cancelamento_orfao','nao_suportado_sat')),
      detalhe TEXT
    );
    """

    conexao.executescript(ddl)


def abrir_banco(caminho):
    """Abre (criando se preciso) o banco em `caminho` e devolve a conexao pronta.

    O `PRAGMA foreign_keys = ON` nao e detalhe: no SQLite ele vem DESLIGADO por
    padrao e vale POR CONEXAO, nao pelo arquivo. Sem ele, os REFERENCES do DDL
    sao decorativos e um item orfao entra em silencio.

    A ordem das duas ultimas chamadas tambem nao e estilo. `criar_esquema` poe de
    pe as tabelas da spec 01, e a migracao v2 faz `ALTER TABLE itens` — num banco
    novo essa tabela so existe depois de `criar_esquema` ter rodado. Invertidas, a
    primeira abertura de um banco novo quebraria.
    """

    conexao = sqlite3.connect(caminho)
    conexao.execute("PRAGMA foreign_keys = ON")
    criar_esquema(conexao)
    aplicar_migracoes(conexao)
    return conexao

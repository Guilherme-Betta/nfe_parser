"""Cascata deterministica: descobrir A QUE CATEGORIA um produto pertence.

Implementa o paragrafo 4 de `specs/02_spec_classificacao.md`, passos 1, 2 e 4 —
o MVP que a propria spec declara: "base (memoria+NCM+bucket) e o MVP e funciona
sem LLM". ⛔ O passo 3 (LLM) e a story 012 e NAO existe aqui.

A story 008 respondeu "QUAL produto e este item". Este modulo responde a outra
metade: "que categoria e este produto". Classifica-se o PRODUTO, nunca a linha
solta — todo item que resolve para a mesma linha de `produtos` herda a categoria
de graca, e e isso que a spec chama de realimentacao.

A cascata tem tres degraus, e a ORDEM entre eles e o contrato inteiro:

1. **Memoria** — produto com `origem in ('manual','memoria')` fica como esta.
2. **NCM ancora** — o mapa curado, pelo prefixo MAIS LONGO que casar.
3. **Bucket** — o resto vai para `uncategorized`, com `origem` NULL.

🔴 O que protege um produto e a `origem`, NAO o fato de ele ja ter categoria.
Produto no bucket tem `categoria_id` preenchido e `origem` NULL, e TEM de ser
reprocessado: o mapa NCM cresce (a story 010 existe para faze-lo crescer), e
rodar a cascata de novo tem de resgatar quem caiu la. Uma implementacao que
parasse em `if categoria_atual is not None` prenderia no bucket, para sempre,
todo produto que caisse la uma vez.

⚠️ `origem='memoria'` e RESPEITADO aqui, mas nunca escrito. Com a identidade da
008, a realimentacao nao precisa copiar nada — todo item do mesmo produto cai na
mesma linha, e a categoria ja esta la. Nao existe um segundo lugar para onde
"lembrar" a decisao. O valor fica protegido para quem venha a escreve-lo.

⚠️ Nenhuma funcao daqui chama `conexao.commit()`. Quem abriu a transacao e que a
fecha — mesma regra de `produtos.py`, e pelo mesmo motivo: a divida de
`persistir_nota` commitar por conta propria vence na 013, e nao se paga uma
divida abrindo outra igual ao lado.

⛔ Este modulo nao le `itens`: ele RECEBE o `ncm` por parametro. Quem os liga e a
story 013.
"""

from datetime import UTC, datetime


def buscar_categoria_por_ncm(conexao, ncm):
    """Devolve a categoria que o mapa curado da a este NCM, ou `None`.

    O NCM e hierarquico: os dois primeiros digitos dizem o capitulo, os quatro
    primeiros a posicao, os oito o item. O mapa de `ncm_ancora` aproveita isso e
    guarda prefixos de larguras diferentes apontando para niveis diferentes da
    taxonomia — `04` para Mercado, `0403` para Mercado > Laticinios.

    🔴 Por isso a busca e pelo prefixo MAIS LONGO, e o `ORDER BY
    LENGTH(prefixo) DESC` e a funcao inteira. Quando os tres candidatos existem,
    os tres casam ao mesmo tempo, e sem a ordenacao o SQLite devolveria qualquer
    um deles — a categoria sairia certa umas vezes e generica demais outras, sem
    sintoma nenhum. ⛔ Ordenar por `prefixo` seria ordem alfabetica, que nao tem
    relacao com especificidade.

    Prefixo repetido na lista do `IN` nao atrapalha, porque `IN` e um conjunto:
    com `ncm="0403"`, as fatias `[:8]` e `[:4]` dao o mesmo valor. E por isso que
    nao ha `if` nenhum sobre o comprimento do NCM.

    🔴 NCM vazio devolve `None` em vez de levantar, e aqui o remedio e o OPOSTO
    do de `resolver_produto_por_gtin`. La, GTIN vazio e erro de programacao — quem
    nao tem codigo de barras nunca deveria ter chamado aquela funcao. Aqui, item
    sem NCM e caso normal e comum em NFC-e: nao e erro de ninguem, e a cascata ja
    tem resposta pronta para ele, que e o bucket.

    ⚠️ Mas a guarda precisa vir ANTES das fatias, por dois motivos independentes:
    `None[:8]` levanta `TypeError`, e em SQL `WHERE prefixo = NULL` nao casa com
    nada — a consulta responderia "nao achei" pelo motivo errado, em silencio.
    """

    if not ncm:
        return None

    cursor = conexao.execute(
        """
        SELECT categoria_id FROM ncm_ancora
        WHERE prefixo IN (?, ?, ?)
        ORDER BY LENGTH(prefixo) DESC
        LIMIT 1
        """,
        (ncm[:8], ncm[:4], ncm[:2]),
    )

    resultado = cursor.fetchone()
    if resultado:
        return resultado[0]

    return None


def _categoria_do_bucket(conexao):
    """Devolve o `id` do bucket "Nao Classificado". Levanta se ele nao existir.

    ⚠️ `categorias` nasce VAZIA da migracao v1 — o seed e a story 010, que vem
    depois desta. Um banco sem linha `is_bucket = 1` nao consegue completar o
    passo 4 da cascata, e falhar alto e melhor que gravar NULL em silencio.

    ⭐ Quem chama so a invoca no ramo que precisa dela. A checagem e PREGUICOSA
    de proposito: um banco cujo mapa NCM cobre o produto classifica normalmente
    sem bucket nenhum, e levantar na entrada proibiria um caso que funciona.
    """

    linha = conexao.execute("SELECT id FROM categorias WHERE is_bucket = 1").fetchone()

    if linha is None:
        raise LookupError(
            "nenhuma categoria com is_bucket = 1;"
            " o seed da taxonomia (story 010) nao foi carregado neste banco"
        )

    return linha[0]


def classificar_produto(conexao, produto_id, ncm):
    """Roda a cascata sobre um produto, GRAVA o resultado, e devolve a categoria.

    Os tres degraus estao escritos em sequencia, e nao como lista de regras no
    nivel do modulo. ⭐ Sao tres passos fixos sem ponto de extensao externo: a
    indirecao custaria mais do que economiza, e a story 012 acrescenta o degrau
    do LLM editando esta funcao, que e uma linha de diff.

    🔴 O passo 1 olha a `origem`, nunca o `categoria_id`. Ver o cabecalho do
    modulo: confundir os dois prenderia no bucket todo produto que caisse la.

    ⭐ A leitura de abertura faz DOIS trabalhos: traz a origem atual e prova que o
    produto existe. `fetchone()` devolvendo `None` cobre tanto o id inexistente
    quanto `produto_id=None`, porque `WHERE id = NULL` nao casa com nada. Sem
    ela, o UPDATE la embaixo afetaria ZERO linhas em silencio e a funcao
    devolveria uma categoria que nao foi gravada em lugar nenhum — mentira sem
    sintoma, que foi o defeito que a story 008 achou tarde.

    ⛔ `LookupError`, e nao `ValueError`: o argumento esta bem formado; o que
    falta e a linha no banco.

    O ramo do bucket grava `origem = None`, que vira NULL. ⛔ Nao e a string
    "bucket": a coluna tem `CHECK (origem IN ('manual','memoria','ncm','llm'))` e
    o banco recusaria — e e esse NULL que marca a linha como reprocessavel.
    """

    linha = conexao.execute(
        "SELECT categoria_id, origem FROM produtos WHERE id = ?", (produto_id,)
    ).fetchone()

    if linha is None:
        raise LookupError(f"produto {produto_id} nao existe")

    categoria_atual, origem_atual = linha[0], linha[1]

    if origem_atual in ("manual", "memoria"):
        return categoria_atual

    categoria = buscar_categoria_por_ncm(conexao, ncm)
    if categoria is None:
        categoria = _categoria_do_bucket(conexao)
        origem = None
    else:
        origem = "ncm"

    conexao.execute(
        "UPDATE produtos SET categoria_id = ?, origem = ?, atualizado_em = ? WHERE id = ?",
        (categoria, origem, datetime.now(UTC).isoformat(), produto_id),
    )

    return categoria


def definir_categoria_manual(conexao, produto_id, categoria_id):
    """Grava a decisao de um humano, que a cascata nunca mais sobrescreve.

    E a contraparte do passo 1: `classificar_produto` recusa mexer em
    `origem in ('manual','memoria')`, e esta funcao e quem poe o `'manual'` la.

    🔴 A assimetria e o ponto da story, e vale nos dois sentidos: a MAO
    sobrescreve a MAQUINA sem pedir licenca, e a maquina nunca sobrescreve a mao.
    Por isso nao ha checagem nenhuma sobre o que estava gravado antes.

    ⛔ O `categoria_id` NAO e validado contra `categorias`. A coluna tem
    `REFERENCES categorias(id)` e o `abrir_banco` liga `PRAGMA foreign_keys = ON`,
    entao uma categoria inexistente ja levanta `sqlite3.IntegrityError` vinda do
    banco. Um `SELECT` a mais so trocaria essa excecao por outra.

    🔴 Mas categoria VAZIA a chave estrangeira NAO pega, e o estrago seria mudo —
    e este e o contrato que o passo 4 acrescentou (spec §7, C4). `categoria_id`
    NULL passa pela FK, porque NULL em coluna anulavel e valor legitimo, e seria
    gravado junto com `origem='manual'`. O produto ficaria PROTEGIDO pelo passo 1
    da cascata e sem categoria nenhuma: preso fora do bucket, para sempre,
    invisivel a qualquer relatorio que some por categoria.

    ⚠️ Nenhum teste do passo 2 pegava isso, e a cobertura tambem nao — as linhas
    existem e sao executadas; o que faltava era uma chamada com a chave vazia
    passando por elas. E o mesmo modo de falha que a story 008 achou lendo o
    codigo inteiro, e a mesma licao: cobertura e diagnostico, nao prova.
    """

    if not categoria_id:
        raise ValueError(
            "definir_categoria_manual exige uma categoria nao vazia;"
            " gravar NULL com origem='manual' prenderia o produto fora do bucket"
        )

    linha = conexao.execute("SELECT id FROM produtos WHERE id = ?", (produto_id,)).fetchone()

    if linha is None:
        raise LookupError(f"produto {produto_id} nao existe")

    conexao.execute(
        "UPDATE produtos SET categoria_id = ?, origem = 'manual', atualizado_em = ? WHERE id = ?",
        (categoria_id, datetime.now(UTC).isoformat(), produto_id),
    )

"""Cascata de classificacao: descobrir A QUE CATEGORIA um produto pertence.

Implementa o paragrafo 4 de `specs/02_spec_classificacao.md`. Classifica-se o
PRODUTO, nunca a linha solta de nota: todo item que resolve para a mesma linha de
`produtos` herda a categoria de graca — e isso que a spec chama de realimentacao.

A cascata tem quatro degraus, e a ORDEM entre eles e o contrato inteiro:

1. **Memoria** — produto com `origem in ('manual','memoria')` fica como esta.
2. **NCM ancora** — o mapa curado, pelo prefixo MAIS LONGO que casar.
3. **LLM** — opcional: so existe se quem chama passar um `llm`.
4. **Bucket** — o resto vai para `uncategorized`, com `origem` NULL.

⭐ O codigo separa DECIDIR de GRAVAR. `decidir_categoria` percorre os degraus 2 a 4
e devolve uma `Decisao`, sem escrever nada; `gravar_decisao` escreve categoria,
origem e confianca JUNTAS, num UPDATE so. Gravar o trio em pedacos deixava sobrar a
`confianca` de uma decisao do LLM num produto que ja tinha saido dela.

🔴 O que protege um produto e a `origem`, NAO o fato de ele ja ter categoria.
Produto no bucket tem `categoria_id` preenchido e `origem` NULL, e TEM de ser
reprocessado: o mapa NCM cresce, e rodar a cascata de novo tem de resgatar quem
caiu la. Uma implementacao que parasse em `if categoria_atual is not None`
prenderia no bucket, para sempre, todo produto que caisse la uma vez.

⚠️ `origem='memoria'` e RESPEITADO aqui, mas nunca escrito. Como todo item do mesmo
produto cai na mesma linha de `produtos`, a categoria ja esta la: nao existe um
segundo lugar para onde "lembrar" a decisao. O valor fica protegido para quem venha
a escreve-lo.

⭐ O `llm` e uma FUNCAO `llm(descricao, slugs) -> (slug, confianca) | None`, recebida
por parametro (quem a constroi e `llm.py`). E isso que deixa o degrau 3 opcional —
sem `llm`, ele nao existe — e testavel sem Ollama nenhum.

⚠️ Nenhuma funcao daqui chama `conexao.commit()`. Quem abriu a transacao e que a
fecha.

⛔ Este modulo nao le `itens`: ele RECEBE o `ncm` por parametro. Quem liga produto e
item e `varredura.py`.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from nfe_parser.vocabulario import OrigemClassificacao


@dataclass(frozen=True)
class Decisao:
    """O que a cascata decidiu para um produto.

    `origem` None quer dizer bucket: a linha continua PENDENTE e sera varrida de
    novo. ⛔ Nao e a string "bucket" — a coluna tem `CHECK (origem IN
    ('manual','memoria','ncm','llm'))`, e o banco a recusaria.

    `confianca` so tem valor quando `origem` e `'llm'`. Nas outras, None — e e por
    isso que ela e gravada sempre, junto: e o None que apaga a de uma decisao velha.

    `frozen=True` torna a decisao imutavel depois de criada: ninguem altera um
    campo dela no caminho entre decidir e gravar.
    """

    categoria_id: int
    origem: OrigemClassificacao | None
    confianca: float | None = None


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


def categoria_do_bucket(conexao):
    """Devolve o `id` do bucket "Nao Classificado". Levanta se ele nao existir.

    ⚠️ `categorias` nasce VAZIA; quem a preenche e o seed (`seed.py`). Um banco sem
    linha `is_bucket = 1` nao consegue completar o degrau 4 da cascata, e falhar
    alto e melhor que gravar NULL em silencio.

    ⭐ A checagem e PREGUICOSA de proposito: so quem precisa do bucket a invoca. Um
    banco cujo mapa NCM cobre o produto classifica normalmente sem bucket nenhum,
    e levantar na entrada proibiria um caso que funciona.

    ⛔ `taxonomia.apagar_categoria` tambem a usa, em vez de uma subconsulta
    `SET categoria_id = (SELECT id FROM categorias WHERE is_bucket = 1)`: num banco
    sem bucket a subconsulta devolve NULL, e o UPDATE gravaria NULL em silencio. E
    o `LookupError` daqui que faz o defeito ter sintoma.
    """

    linha = conexao.execute("SELECT id FROM categorias WHERE is_bucket = 1").fetchone()

    if linha is None:
        raise LookupError(
            "nenhuma categoria com is_bucket = 1;"
            " o seed da taxonomia (seed.carregar_seed_padrao) nao foi carregado neste banco"
        )

    return linha[0]


def decidir_categoria(conexao, ncm, descricao, llm=None):
    """Os degraus 2 a 4 da cascata, NA ORDEM da spec: NCM, LLM, bucket.

    Devolve uma `Decisao` e ⛔ nao grava nada. O degrau 1 (memoria) nao esta aqui
    porque ele nao decide: ele decide NAO mexer, e isso depende do que ja esta
    gravado no produto — quem o aplica e `classificar_produto`.
    """

    categoria = buscar_categoria_por_ncm(conexao, ncm)
    if categoria is not None:
        return Decisao(categoria, OrigemClassificacao.NCM)

    decisao_do_llm = _perguntar_ao_llm(conexao, llm, descricao)
    if decisao_do_llm is not None:
        return decisao_do_llm

    return Decisao(categoria_do_bucket(conexao), None)


def _perguntar_ao_llm(conexao, llm, descricao):
    """O degrau 3. Devolve a `Decisao` do LLM, ou `None` se ele nao resolveu.

    ⚠️ Sem `llm` ou sem descricao, nao ha pergunta: devolve `None` direto.

    ⭐ A lista de slugs vem do banco, SEM o bucket e EM ORDEM. Sem o `ORDER BY` a
    lista mudaria de ordem entre execucoes, e o prompt tambem.

    🔴 O slug que volta e conferido NO BANCO antes de virar decisao, mesmo que o
    `llm` de `llm.py` ja confira a lista. O `llm` e um parametro e pode ser
    QUALQUER funcao; quem garante que nenhuma categoria e inventada e esta
    consulta. E o `AND is_bucket = 0` impede o LLM de "escolher" o bucket: com
    `origem = 'llm'` ali, o produto sairia da varredura para sempre sem ter sido
    classificado.
    """

    if llm is None or not descricao:
        return None

    slugs = [
        linha[0]
        for linha in conexao.execute(
            "SELECT slug FROM categorias WHERE is_bucket = 0 ORDER BY slug"
        )
    ]

    resposta = llm(descricao, slugs)
    if resposta is None:
        return None
    slug, confianca = resposta

    linha = conexao.execute(
        "SELECT id FROM categorias WHERE slug = ? AND is_bucket = 0", (slug,)
    ).fetchone()
    if linha is None:
        return None

    return Decisao(linha[0], OrigemClassificacao.LLM, confianca)


def gravar_decisao(conexao, produto_id, decisao):
    """Grava a categoria, a origem e a confianca JUNTAS, num UPDATE so.

    E o unico lugar que escreve uma decisao de classificacao num produto, e e por
    isso que o trio nunca fica pela metade.
    """

    conexao.execute(
        "UPDATE produtos SET categoria_id = ?, origem = ?, confianca = ?, atualizado_em = ?"
        " WHERE id = ?",
        (
            decisao.categoria_id,
            decisao.origem,
            decisao.confianca,
            datetime.now(UTC).isoformat(),
            produto_id,
        ),
    )


def classificar_produto(conexao, produto_id, ncm, llm=None):
    """Roda a cascata sobre um produto, GRAVA o resultado, e devolve a categoria.

    🔴 O degrau 1 olha a `origem`, nunca o `categoria_id`. Ver o cabecalho do
    modulo: confundir os dois prenderia no bucket todo produto que caisse la.

    ⭐ A leitura de abertura faz DOIS trabalhos: traz a origem atual e prova que o
    produto existe. `fetchone()` devolvendo `None` cobre tanto o id inexistente
    quanto `produto_id=None`, porque `WHERE id = NULL` nao casa com nada. Sem
    ela, o UPDATE la embaixo afetaria ZERO linhas em silencio e a funcao
    devolveria uma categoria que nao foi gravada em lugar nenhum.

    ⛔ `LookupError`, e nao `ValueError`: o argumento esta bem formado; o que
    falta e a linha no banco.
    """

    linha = conexao.execute(
        "SELECT categoria_id, origem, descricao_exemplo FROM produtos WHERE id = ?",
        (produto_id,),
    ).fetchone()

    if linha is None:
        raise LookupError(f"produto {produto_id} nao existe")

    categoria_atual, origem_atual, descricao = linha

    if origem_atual in (OrigemClassificacao.MANUAL, OrigemClassificacao.MEMORIA):
        return categoria_atual

    decisao = decidir_categoria(conexao, ncm, descricao, llm)
    gravar_decisao(conexao, produto_id, decisao)
    return decisao.categoria_id


def definir_categoria_manual(conexao, produto_id, categoria_id):
    """Grava a decisao de um humano, que a cascata nunca mais sobrescreve.

    E a contraparte do degrau 1: `classificar_produto` recusa mexer em
    `origem in ('manual','memoria')`, e esta funcao e quem poe o `'manual'` la.

    🔴 A assimetria vale nos dois sentidos: a MAO sobrescreve a MAQUINA sem pedir
    licenca, e a maquina nunca sobrescreve a mao. Por isso nao ha checagem
    nenhuma sobre o que estava gravado antes.

    ⛔ O `categoria_id` NAO e validado contra `categorias`. A coluna tem
    `REFERENCES categorias(id)` e o `abrir_banco` liga `PRAGMA foreign_keys = ON`,
    entao uma categoria inexistente ja levanta `sqlite3.IntegrityError` vinda do
    banco. Um `SELECT` a mais so trocaria essa excecao por outra.

    🔴 Mas categoria VAZIA a chave estrangeira NAO pega, e o estrago seria mudo.
    `categoria_id` NULL passa pela FK, porque NULL em coluna anulavel e valor
    legitimo, e seria gravado junto com `origem='manual'`. O produto ficaria
    PROTEGIDO pelo degrau 1 e sem categoria nenhuma: preso fora do bucket, para
    sempre, invisivel a qualquer relatorio que some por categoria.
    """

    if not categoria_id:
        raise ValueError(
            "definir_categoria_manual exige uma categoria nao vazia;"
            " gravar NULL com origem='manual' prenderia o produto fora do bucket"
        )

    linha = conexao.execute("SELECT id FROM produtos WHERE id = ?", (produto_id,)).fetchone()

    if linha is None:
        raise LookupError(f"produto {produto_id} nao existe")

    gravar_decisao(conexao, produto_id, Decisao(categoria_id, OrigemClassificacao.MANUAL))

"""Editar a taxonomia: criar, apagar, mover e renomear categoria.

Implementa o ultimo bloco do paragrafo 4 de `specs/02_spec_classificacao.md` —
"apagar categoria com historico → produtos vao pro bucket; renomear → mantem
vinculos (id estavel); mover subcategoria → vinculos seguem".

🔴 As tres funcoes acham a categoria pelo `slug`, nunca pelo `id`. O slug e a
chave natural: e por ele que o seed casa, e por ele que a lapide registra o que
foi apagado, e e por ele que uma futura UI vai se referir a uma categoria sem ter
visto o `id` nascer. O `id` continua sendo o que `produtos.categoria_id` e
`ncm_ancora.categoria_id` referenciam — slug e a chave de FORA, id a de DENTRO.

⭐ Renomear e mover sao baratos exatamente porque o `id` nao muda: nada em outra
tabela precisa ser reescrito, e o vinculo sobrevive sozinho. Apagar e o unico
caso em que o vinculo MUDA, e por isso e a unica funcao longa daqui.

⚠️ Nenhuma funcao deste modulo chama `conexao.commit()`, e aqui a regra ganha um
motivo proprio: `apagar_categoria` faz quatro escritas em sequencia, e commitar
no meio deixaria o banco com os produtos ja no bucket e a categoria ainda de pe,
se a ultima falhasse.

🔴 A ARVORE TEM NO MAXIMO 2 NIVEIS, e criar e mover sao as duas portas por onde
um terceiro nivel entraria. As duas recusam: o pai tem de ser nivel 1, e uma
categoria com filhas nao vira filha de ninguem. O bucket nunca e pai — ele e o
"resto", e um galho embaixo dele seria classificado e nao-classificado ao mesmo
tempo.
"""

import re
import unicodedata
from datetime import UTC, datetime

from nfe_parser.categorizacao import categoria_do_bucket


def _slug_de(nome):
    """`Pão & Café` → `pao-cafe`: sem acento, minusculo, um hifen entre palavras.

    ⭐ O `NFKD` separa a letra do acento (`ã` vira `a` + til), e o `encode` para
    ASCII com `ignore` joga o til fora. Sem esse passo, o `re.sub` trocaria o `ã`
    inteiro por hifen e `Pão` viraria `p-o`.
    """

    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", sem_acento.lower()).strip("-")


def _pai_valido(conexao, parent_slug):
    """Devolve o `id` do pai, se ele puder ter filhas. Levanta se nao puder.

    E a regra dos 2 niveis vista do lado do pai, comum a criar e mover.
    """

    pai = conexao.execute(
        "SELECT id, parent_id, is_bucket FROM categorias WHERE slug = ?", (parent_slug,)
    ).fetchone()
    if pai is None:
        raise LookupError(f"nao existe categoria com slug {parent_slug!r} para ser o pai")
    if pai[2]:
        raise ValueError(f"a categoria {parent_slug!r} e o bucket; o bucket nao tem subcategorias")
    if pai[1] is not None:
        raise ValueError(
            f"a categoria {parent_slug!r} ja e subcategoria; a arvore tem no maximo 2 niveis"
        )
    return pai[0]


def criar_categoria(conexao, nome, parent_slug=None):
    """Cria uma categoria nivel 1 (ou subcategoria de `parent_slug`). Devolve o slug.

    🔴 O slug nasce do nome AGORA e, dali em diante, e dado: `renomear_categoria`
    nunca o recalcula (ver o cabecalho de `seed.py`). O prefixo do pai segue a
    convencao do arquivo de seed (`mercado-frutas`), e e o que evita que
    "Outros" em dois pais diferentes colida.

    ⚠️ A guarda do nome olha o SLUG, nao so o nome: `!!!` e um nome nao vazio que
    da slug vazio, e um slug vazio passaria pelo `NOT NULL` da coluna em
    silencio.

    ⭐ Slug repetido e conferido antes do INSERT para virar `ValueError` com
    mensagem; o `UNIQUE` da coluna levantaria `IntegrityError`, que a camada web
    nao saberia distinguir de um defeito.
    """

    nome = (nome or "").strip()
    base = _slug_de(nome)
    if not base:
        raise ValueError(f"criar_categoria exige um nome com letra ou digito; recebeu {nome!r}")

    parent_id = None
    slug = base
    if parent_slug is not None:
        parent_id = _pai_valido(conexao, parent_slug)
        slug = f"{parent_slug}-{base}"

    if conexao.execute("SELECT 1 FROM categorias WHERE slug = ?", (slug,)).fetchone():
        raise ValueError(f"ja existe categoria com slug {slug!r}")

    conexao.execute(
        "INSERT INTO categorias (slug, nome, parent_id) VALUES (?, ?, ?)", (slug, nome, parent_id)
    )
    return slug


def apagar_categoria(conexao, slug):
    """Apaga a categoria e manda os produtos dela para o bucket.

    🔴 A ORDEM DAS ESCRITAS E OBRIGATORIA, e nao e estilo. `produtos.categoria_id`
    e `ncm_ancora.categoria_id` apontam para `categorias(id)`, e o `abrir_banco`
    liga `PRAGMA foreign_keys = ON`. Apagar a categoria com produto ou ancora
    ainda apontando para ela levanta `IntegrityError` e nada acontece. Por isso:
    produtos, ancoras, lapide, e SO ENTAO a categoria.

    🔴 Os produtos vao para o bucket com `origem = NULL`, INCLUSIVE os que
    estavam em `'manual'`, e este e o ponto mais fino da funcao. O que protege um
    produto da cascata e a `origem`, nao a categoria (ver o cabecalho de
    `categorizacao.py`). Um `'manual'` preservado deixaria o produto protegido
    DENTRO do bucket, para sempre — preso exatamente onde nada pode ficar preso.
    ⭐ E zerar e a resposta honesta: aquela decisao manual apontava para uma
    categoria que nao existe mais. A `confianca` sai junto, pelo mesmo motivo: ela
    descrevia uma decisao que deixou de valer.

    ⚠️ As ancoras NCM sao APAGADAS junto, e nao reapontadas. `ncm_ancora.
    categoria_id` e `NOT NULL`, entao nao ha como "desapontar" uma ancora. As
    duas alternativas sao piores: reapontar para o bucket gravaria
    `origem = 'ncm'` no produto daquele NCM — e origem nao-NULL o PROTEGE, que e
    o oposto do que o bucket significa; reapontar para o pai so funciona quando
    ha pai.

    ⛔ Apagar o bucket e RECUSADO: `categoria_do_bucket` levanta quando nao ha
    linha `is_bucket = 1`, e o degrau do bucket da cascata morre inteiro.

    ⛔ Apagar categoria que tem FILHAS tambem e recusado, e a mensagem diz quantas
    sao e o que fazer antes. Cascatear apagaria curadoria de quem usa o programa
    de surpresa, num comando pedido para UMA categoria; promover as filhas
    mudaria a forma da arvore sem ninguem ter pedido, e `mover_categoria` ja
    existe para quem quiser isso. Recusar nao destroi nada e e afrouxavel depois.

    ⭐ A lapide usa `ON CONFLICT(slug) DO NOTHING` porque o mesmo slug pode ser
    apagado duas vezes ao longo da vida do banco: a categoria volta por um seed
    antigo e e apagada de novo. E ela que faz apagar ser DEFINITIVO — sem a
    lapide, o seed trataria a categoria apagada como "faltando" e a inseriria de
    volta, prestativo, desfazendo a decisao de quem usa o programa.
    """

    linha = conexao.execute(
        "SELECT id, is_bucket FROM categorias WHERE slug = ?", (slug,)
    ).fetchone()
    if linha is None:
        raise LookupError(f"nao existe categoria com slug {slug!r}")
    categoria_id, is_bucket = linha[0], linha[1]

    if is_bucket:
        raise ValueError(f"a categoria {slug!r} e o bucket; apaga-la quebraria a classificacao")

    filhas = conexao.execute(
        "SELECT COUNT(*) FROM categorias WHERE parent_id = ?", (categoria_id,)
    ).fetchone()[0]
    if filhas:
        raise ValueError(
            f"a categoria {slug!r} tem {filhas} subcategoria(s);"
            " mova ou apague as subcategorias antes de apagar esta"
        )

    conexao.execute(
        "UPDATE produtos SET categoria_id = ?, origem = NULL, confianca = NULL, atualizado_em = ?"
        " WHERE categoria_id = ?",
        (categoria_do_bucket(conexao), datetime.now(UTC).isoformat(), categoria_id),
    )
    conexao.execute("DELETE FROM ncm_ancora WHERE categoria_id = ?", (categoria_id,))
    conexao.execute(
        "INSERT INTO categorias_apagadas (slug, apagada_em) VALUES (?, ?)"
        " ON CONFLICT(slug) DO NOTHING",
        (slug, datetime.now(UTC).isoformat()),
    )
    conexao.execute("DELETE FROM categorias WHERE id = ?", (categoria_id,))


def mover_categoria(conexao, slug, novo_parent_slug):
    """Troca o pai da categoria. `novo_parent_slug` None a sobe para nivel 1.

    ⭐ Escreve a coluna `parent_id`, e so ela. O `id` nao muda, entao produtos e
    ancoras seguem junto de graca — nenhuma outra tabela e tocada.

    🔴 A SUBIDA e a funcao inteira. Mover uma categoria para dentro de uma
    descendente dela propria fecha um CICLO na arvore: ela deixa de ter fim, e
    quem a percorrer depois roda para sempre. ⛔ A chave estrangeira nao pega
    isso, porque cada linha, sozinha, aponta para um pai que existe — o estrago e
    mudo ate alguem caminhar a arvore.

    ⚠️ O teste tem de ser a subida inteira, ⛔ nao um nivel so: um ciclo pode se
    fechar tres ou quatro niveis acima. Mover a categoria para dentro dela mesma
    e o caso degenerado, pego na primeira volta.

    ⭐ O `while` SEMPRE termina: ou chega a uma categoria de nivel 1
    (`parent_id` NULL) ou reencontra a categoria movida.

    🔴 Depois do ciclo vem a regra dos 2 niveis (ver o cabecalho): o novo pai tem
    de ser nivel 1 e nao o bucket, e quem tem filhas nao desce. A ordem preserva a
    mensagem de ciclo para quem tenta mover uma categoria para dentro de si.
    """

    linha = conexao.execute("SELECT id FROM categorias WHERE slug = ?", (slug,)).fetchone()
    if linha is None:
        raise LookupError(f"nao existe categoria com slug {slug!r}")
    categoria_id = linha[0]

    if novo_parent_slug is None:
        conexao.execute("UPDATE categorias SET parent_id = NULL WHERE id = ?", (categoria_id,))
        return

    pai = conexao.execute(
        "SELECT id FROM categorias WHERE slug = ?", (novo_parent_slug,)
    ).fetchone()
    if pai is None:
        raise LookupError(f"nao existe categoria com slug {novo_parent_slug!r} para ser o novo pai")

    atual = pai[0]
    while atual is not None:
        if atual == categoria_id:
            raise ValueError(
                f"mover {slug!r} para dentro de {novo_parent_slug!r} criaria um ciclo na arvore"
            )
        atual = conexao.execute(
            "SELECT parent_id FROM categorias WHERE id = ?", (atual,)
        ).fetchone()[0]

    _pai_valido(conexao, novo_parent_slug)
    filhas = conexao.execute(
        "SELECT COUNT(*) FROM categorias WHERE parent_id = ?", (categoria_id,)
    ).fetchone()[0]
    if filhas:
        raise ValueError(
            f"a categoria {slug!r} tem {filhas} subcategoria(s); dentro de {novo_parent_slug!r}"
            " elas virariam um terceiro nivel"
        )

    conexao.execute("UPDATE categorias SET parent_id = ? WHERE id = ?", (pai[0], categoria_id))


def renomear_categoria(conexao, slug, nome):
    """Troca o `nome` da categoria. ⛔ NUNCA toca no `slug`.

    🔴 Se o slug mudasse junto com o nome, a categoria renomeada viraria
    "faltando" para o seed, que a inseriria de novo com o slug antigo: quem
    editou UMA categoria ficaria com DUAS, e sem erro nenhum. Ha ainda dois
    motivos menores, e cada um bastaria — a lapide casa por slug, e o
    `taxonomia_seed.json` casa as ancoras NCM com a categoria pelo slug.

    ⭐ E o argumento do slug-como-dado (ver o cabecalho de `seed.py`) visto do
    outro lado: slug derivado do nome faria "corrigir um acento" mudar a
    identidade da linha.

    ⚠️ A guarda do nome vazio vem ANTES de ir ao banco, e existe porque
    `nome TEXT NOT NULL` ⛔ NAO recusa string vazia. E o mesmo modo de falha de
    `definir_categoria_manual` com categoria vazia: a coluna nao defende, e o
    dano e mudo. `ValueError`, porque o argumento esta
    malformado — nao e coisa que falte no banco.
    """

    if not nome:
        raise ValueError(f"renomear_categoria exige um nome nao vazio; recebeu {nome!r}")

    linha = conexao.execute("SELECT id FROM categorias WHERE slug = ?", (slug,)).fetchone()
    if linha is None:
        raise LookupError(f"nao existe categoria com slug {slug!r}")

    conexao.execute("UPDATE categorias SET nome = ? WHERE slug = ?", (nome, slug))

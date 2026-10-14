"""Carrega a taxonomia e o mapa NCM curado — o dado de que a cascata vive.

Sem o seed, `categoria_do_bucket` levanta `LookupError` e o degrau do bucket da
cascata nao existe.

🔴 O contrato central e a IDEMPOTENCIA, e ela nao e enfeite. Produto no bucket e
REPROCESSAVEL, e a razao de isso valer a pena e esta aqui: crescer o mapa NCM e
carregar de novo resgata quem caiu no bucket. Um seed que so pudesse rodar uma
vez — numa migracao, por exemplo — tornaria esse resgate impossivel em todo
banco que ja existisse. E por isso que o seed ⛔ NAO e uma migracao.

⭐ A chave de identidade e o `slug`, e ele e DADO, nao calculado do nome. Se
fosse calculado, renomear uma categoria mudaria o slug, e o carregador inseriria
uma linha NOVA em vez de renomear a antiga: os produtos continuariam apontando
para a velha, e a taxonomia teria duas. ⛔ Isso quebraria o requisito "renomear
mantem vinculos, o id e estavel". A prova de que a regra calculada nao fecharia
sozinha esta no proprio seed: o bucket se chama "Nao Classificado" e o slug dele
e `uncategorized`, fixado pela spec de produto.

🔴 O SEED E UMA BASE DEFAULT, NAO O DONO DA TABELA. Ele INSERE o que falta e
⛔ NUNCA toca no que ja existe. O usuario pode remover, editar e adicionar
categorias (`taxonomia.py`), e a edicao dele e DEFINITIVA: o arquivo de dados e
so um ponto de partida.

⚠️ Por isso nao ha `ON CONFLICT(slug) DO UPDATE` em `carregar_categorias`. Ele
faria sentido se o arquivo de dados fosse o UNICO autor de `categorias`; com o
usuario como segundo autor, rodar o seed de novo desfaria o renomear E o mover.

⛔ E ele nao apaga nada. Tirar uma categoria do arquivo de dados nao a
apaga do banco: apagar e `taxonomia.apagar_categoria`, que tem regra propria para
os produtos e as ancoras pendurados.

⭐ `categorias_apagadas` — a lapide da migracao v3 — e o que fecha o circulo.
Sem ela, "insere o que falta" trataria uma categoria APAGADA como faltando e a
traria de volta, prestativo, com `id` novo e sem os produtos que tinha.

⚠️ Nenhuma funcao daqui chama `conexao.commit()` — mesma regra de `produtos.py` e
`categorizacao.py`. Aqui ela ainda ganha uma razao a mais: categorias e ancoras
devem entrar ou nao entrar JUNTAS, e quem controla isso e o chamador.
"""

import json
from pathlib import Path

_CAMINHO_PADRAO = Path(__file__).parent / "dados" / "taxonomia_seed.json"


def _slugs(conexao, consulta):
    """Devolve um conjunto com a primeira coluna de `consulta`."""

    return {linha[0] for linha in conexao.execute(consulta)}


def carregar_categorias(conexao, categorias):
    """Insere as categorias que FALTAM. ⛔ Nao toca nas que ja existem.

    Cada item e um dicionario com `slug` e `nome` sempre, e `parent` (o slug do
    pai) e `is_bucket` opcionais.

    🔴 Rodar de novo com a mesma lista nao muda NADA no banco, e essa e a forma
    forte da idempotencia. A forma fraca — inserir ou sobrescrever — tambem
    deixaria o banco igual, mas so enquanto ninguem tivesse editado nada. Ver o
    cabecalho do modulo: o usuario e o segundo autor desta tabela, e entre os
    dois quem ganha e ele.

    ⭐ O preco dessa escolha, e ele e real: corrigir um nome errado no arquivo de
    dados nao tem efeito em banco que ja rodou o seed. Isso e aceitavel porque
    existe `taxonomia.renomear_categoria`, que e por onde a correcao e feita.
    ⛔ O que NAO seria aceitavel e o contrario: o arquivo desfazendo, calado, o
    que a pessoa editou.

    🔴 SAO DUAS PASSADAS, e e isso que torna a ORDEM DA LISTA irrelevante. Se o
    `parent` fosse resolvido na mesma passada que insere, um filho que aparecesse
    antes do pai nao o encontraria. ⭐ O teste poe `mercado-frutas` antes de
    `mercado` de proposito: uma lista "arrumada" deixaria a versao de uma passada
    so passar inteira.

    ⚠️ A segunda passada roda so sobre os RECEM-INSERIDOS. Se rodasse sobre todos,
    desfaria o "mover": um `UPDATE ... SET parent_id` incondicional devolveria
    toda categoria para o pai que o arquivo declara, toda vez.

    ⭐ Categoria cujo `parent` esta na lapide e pulada junto, em silencio. Levantar
    ali quebraria o seed inteiro, para sempre, por causa de uma remocao legitima —
    e o galho foi removido de proposito. ⛔ Ja `parent` simplesmente AUSENTE
    continua levantando: isso e erro de digitacao no arquivo de dados.

    🔴 O invariante do bucket conta NO BANCO, nao na lista recebida, e a diferenca
    tem um caso concreto: duas listas carregadas em sequencia, cada uma com o seu
    bucket, deixam o banco com dois — e contar a lista diria 1 nas duas vezes. E
    o estado do banco que a cascata consulta, entao e ele que precisa valer.

    ⚠️ Dois buckets nao dao erro em lugar nenhum: `categoria_do_bucket` faz
    `SELECT ... WHERE is_bucket = 1` seguido de `fetchone()` e devolve um QUALQUER
    dos dois. Metade dos produtos nao classificados iria para um e metade para o
    outro, para sempre, sem sintoma.

    ⭐ Conferir DEPOIS de gravar parece errado e nao e: como nada aqui commita,
    quem abriu a transacao recebe a excecao com a gravacao ainda por confirmar e
    desfaz.
    """

    sepultados = _slugs(conexao, "SELECT slug FROM categorias_apagadas")
    existentes = _slugs(conexao, "SELECT slug FROM categorias")

    novas = [
        cat
        for cat in categorias
        if cat["slug"] not in sepultados
        and cat["slug"] not in existentes
        and cat.get("parent") not in sepultados
    ]

    for cat in novas:
        conexao.execute(
            "INSERT INTO categorias (slug, nome, is_bucket) VALUES (?, ?, ?)",
            (cat["slug"], cat["nome"], 1 if cat.get("is_bucket") else 0),
        )

    for cat in novas:
        pai_slug = cat.get("parent")
        if pai_slug:
            pai = conexao.execute(
                "SELECT id FROM categorias WHERE slug = ?", (pai_slug,)
            ).fetchone()
            if pai is None:
                raise LookupError(
                    f"a categoria {cat['slug']} aponta para o pai {pai_slug}, que nao esta no seed"
                )
            conexao.execute(
                "UPDATE categorias SET parent_id = ? WHERE slug = ?", (pai[0], cat["slug"])
            )

    quantos = conexao.execute("SELECT COUNT(*) FROM categorias WHERE is_bucket = 1").fetchone()[0]
    if quantos != 1:
        raise ValueError(
            f"o banco ficou com {quantos} categorias is_bucket = 1; tem de haver exatamente uma"
        )


def carregar_ncm_ancora(conexao, ancoras):
    """Grava o mapa prefixo NCM -> categoria. Idempotente, e reaponta.

    Cada item e um dicionario com `prefixo` e `categoria` — esta ultima e o
    SLUG, nao o id: o arquivo de dados nao conhece id nenhum, e e justamente
    isso que o deixa revisavel por um humano.

    🔴 A largura 2, 4 ou 8 nao e regra de gosto; e consequencia mecanica do
    codigo da cascata. `buscar_categoria_por_ncm` consulta exatamente `ncm[:8]`,
    `ncm[:4]` e `ncm[:2]`. Um prefixo de 5 ou 6 digitos ficaria gravado,
    visivel, parecendo mapeamento, e NUNCA casaria com nada. ⛔ Dado morto e
    mudo e pior que erro: recusar na entrada e o unico jeito de ele ter sintoma.

    ⚠️ `ValueError` para a largura e `LookupError` para o slug, e a distincao e
    a de sempre: a largura e argumento malformado; o slug e coisa que falta no
    banco.

    ⭐ O slug e resolvido ANTES do INSERT, em Python, e nao como subconsulta.
    Parece rodeio e nao e: com subconsulta, slug inexistente daria NULL, o
    INSERT bateria no `NOT NULL` da coluna, e a mensagem do SQLite seria "NOT
    NULL constraint failed: ncm_ancora.categoria_id" — que nao diz QUAL prefixo
    nem QUAL slug, num arquivo de dezenas de linhas.

    ⚠️ Nao se valida que o prefixo so tem digitos. A largura tem consequencia
    provada; "so digitos" e qualidade do dado, e mora no teste do arquivo real.

    🔴 Ancora cujo slug esta na LAPIDE e pulada, em silencio, e essa e a unica
    excecao ao paragrafo acima. Depois que alguem apaga uma categoria, o arquivo
    de dados continua declarando as ancoras dela — e sem este `continue` o seed
    inteiro passaria a levantar `LookupError` para sempre, por causa de uma
    remocao legitima. ⭐ A lapide e o que distingue os dois casos: slug sepultado
    e decisao registrada; slug simplesmente ausente e erro de digitacao, e
    continua levantando.

    ⚠️ ⛔ Aqui o `ON CONFLICT ... DO UPDATE` FICA, ao contrario de
    `carregar_categorias`. Nao ha incoerencia: nenhuma funcao de `taxonomia.py`
    edita ancora, entao nao existe edicao de gente para preservar — e crescer o
    mapa NCM e exatamente o que resgata produto preso no bucket.
    """

    sepultados = _slugs(conexao, "SELECT slug FROM categorias_apagadas")

    for ancora in ancoras:
        prefixo = ancora["prefixo"]
        slug = ancora["categoria"]

        if slug in sepultados:
            continue

        if len(prefixo) not in (2, 4, 8):
            raise ValueError(
                f"o prefixo NCM {prefixo} tem {len(prefixo)} digitos;"
                " so 2, 4 ou 8 casam com a busca"
            )

        linha = conexao.execute("SELECT id FROM categorias WHERE slug = ?", (slug,)).fetchone()
        if linha is None:
            raise LookupError(
                f"o prefixo {prefixo} aponta para a categoria {slug}, que nao esta no seed"
            )

        conexao.execute(
            """
            INSERT INTO ncm_ancora (prefixo, categoria_id) VALUES (?, ?)
            ON CONFLICT(prefixo) DO UPDATE SET categoria_id = excluded.categoria_id
            """,
            (prefixo, linha[0]),
        )


def carregar_seed(conexao, dados):
    """Carrega taxonomia e mapa NCM, nesta ordem.

    ⚠️ A ordem nao e arbitraria: `carregar_ncm_ancora` resolve slug contra
    `categorias`, entao a arvore precisa estar gravada antes. Invertida, toda
    ancora levantaria `LookupError` na primeira rodada — e passaria na segunda,
    que e o tipo de defeito que so aparece em banco novo.
    """

    carregar_categorias(conexao, dados["categorias"])
    carregar_ncm_ancora(conexao, dados["ncm_ancora"])


def carregar_seed_padrao(conexao):
    """Carrega o seed versionado junto com o pacote.

    ⚠️ O arquivo mora dentro do pacote, e nao na raiz do repositorio, por um
    motivo pratico: assim ele viaja com a instalacao. O `pyproject.toml` precisa
    declara-lo em `[tool.setuptools.package-data]`, senao o `packages.find`
    recolhe so os `.py` e o JSON some no `pip install` — defeito que a suite NAO
    pegaria, porque o venv de desenvolvimento e editavel e le a arvore direto.
    """

    with _CAMINHO_PADRAO.open(encoding="utf-8") as arquivo:
        carregar_seed(conexao, json.load(arquivo))

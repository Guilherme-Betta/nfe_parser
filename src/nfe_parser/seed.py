"""Carrega a taxonomia e o mapa NCM curado — o dado de que a cascata vive.

A story 009 escreveu a cascata; esta escreve o que ela consulta. Sem o seed, o
`_categoria_do_bucket` levanta `LookupError` e o passo 4 da classificacao nao
existe — a mensagem daquele erro aponta para esta story pelo numero.

🔴 O contrato central e a IDEMPOTENCIA, e ela nao e enfeite. A D3 da 009 diz que
produto no bucket e REPROCESSAVEL, e a razao de isso valer a pena e esta aqui:
crescer o mapa NCM e carregar de novo resgata quem caiu no bucket. Um seed que
so pudesse rodar uma vez — numa migracao, por exemplo — tornaria esse resgate
impossivel em todo banco que ja existisse. E por isso que a 010 NAO acrescenta
migracao, e o banco continua em `user_version = 2`.

⭐ A chave de identidade e o `slug`, e ele e DADO, nao calculado do nome. Se
fosse calculado, renomear uma categoria mudaria o slug, e o carregador inseriria
uma linha NOVA em vez de renomear a antiga: os produtos continuariam apontando
para a velha, e a taxonomia teria duas. ⛔ Isso quebraria de frente o requisito
da 011 — "renomear mantem vinculos, o id e estavel". A prova de que a regra
calculada nao fecharia sozinha esta no proprio seed: o bucket se chama "Nao
Classificado" e o slug dele e `uncategorized`, fixado pela spec de produto.

⚠️ O seed INSERE e ATUALIZA; ⛔ nunca apaga. Tirar uma categoria do arquivo de
dados nao a apaga do banco, e categoria que perdeu o `parent` fica com o pai
antigo. Apagar e mover sao a story 011, que tem regra propria para o que fazer
com os produtos pendurados. Um carregador que apagasse em silencio ou romperia a
chave estrangeira, ou deixaria produto orfao.

⚠️ Nenhuma funcao daqui chama `conexao.commit()` — mesma regra de `produtos.py` e
`categorizacao.py`. Aqui ela ainda ganha uma razao a mais: categorias e ancoras
devem entrar ou nao entrar JUNTAS, e quem controla isso e o chamador.
"""

import json
from pathlib import Path

_CAMINHO_PADRAO = Path(__file__).parent / "dados" / "taxonomia_seed.json"


def carregar_categorias(conexao, categorias):
    """Grava a arvore de categorias. Idempotente, e o `id` sobrevive.

    Cada item e um dicionario com `slug` e `nome` sempre, e `parent` (o slug do
    pai) e `is_bucket` opcionais.

    🔴 SAO DUAS PASSADAS, e e isso que torna a ORDEM DA LISTA irrelevante. Se o
    `parent` fosse resolvido na mesma passada que insere, um filho que aparecesse
    antes do pai nao o encontraria. ⭐ A fixture do oraculo poe `mercado-frutas`
    antes de `mercado` de proposito: uma fixture "arrumada" deixaria a versao de
    uma passada so passar inteira.

    ⭐ O `ON CONFLICT(slug) DO UPDATE` e o que separa "idempotente" das duas
    alternativas erradas, e as duas foram medidas por mutacao:

    - `INSERT OR IGNORE` insere uma vez e nunca mais atualiza. Corrigir um nome
      errado no arquivo de dados nao teria efeito nenhum, sem sintoma.
    - `INSERT OR REPLACE` apaga e reinsere, e o `id` MUDA. Todo
      `produtos.categoria_id` apontaria para o nada.

    🔴 O passo 3 conta os buckets NO BANCO, nao na lista recebida, e a diferenca
    tem um caso concreto: duas listas carregadas em sequencia, cada uma com o seu
    bucket, deixam o banco com dois — e contar a lista diria 1 nas duas vezes. E
    o estado do banco que a 009 consulta, entao e ele que precisa valer.

    ⚠️ Dois buckets nao dao erro em lugar nenhum: `_categoria_do_bucket` faz
    `SELECT ... WHERE is_bucket = 1` seguido de `fetchone()` e devolve um QUALQUER
    dos dois. Metade dos produtos nao classificados iria para um e metade para o
    outro, para sempre, sem sintoma.

    ⭐ Conferir DEPOIS de gravar parece errado e nao e: como nada aqui commita,
    quem abriu a transacao recebe a excecao com a gravacao ainda por confirmar e
    desfaz. Conferir antes exigiria prever em Python o resultado do UPSERT — ou
    seja, reimplementar o banco para adivinhar o banco.
    """

    for cat in categorias:
        conexao.execute(
            """
            INSERT INTO categorias (slug, nome, is_bucket) VALUES (?, ?, ?)
            ON CONFLICT(slug) DO UPDATE SET nome = excluded.nome, is_bucket = excluded.is_bucket
            """,
            (cat["slug"], cat["nome"], 1 if cat.get("is_bucket") else 0),
        )

    for cat in categorias:
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
    codigo da 009. O `buscar_categoria_por_ncm` consulta exatamente `ncm[:8]`,
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
    """

    for ancora in ancoras:
        prefixo = ancora["prefixo"]
        slug = ancora["categoria"]

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

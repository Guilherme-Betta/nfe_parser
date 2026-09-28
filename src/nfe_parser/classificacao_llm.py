"""O degrau do LLM na cascata: so para o que a cascata deterministica mandou ao bucket.

Implementa o passo 3 da spec 02 (§4) do lado do BANCO. A conversa com o modelo e
de `llm.py`; aqui se decide QUANDO perguntar e O QUE gravar.

🔴 Este degrau mora aqui, e NAO dentro de `classificar_produto`, embora a
docstring daquela funcao prometesse "uma linha de diff". A promessa era do tempo
do `--edit-format diff`: com `whole`, a linha custa o arquivo inteiro na ida e
na volta, e a tarefa nao cabia na janela de 8192 do modelo local. E o degrau faz
I/O de rede, que a cascata deterministica nunca fez. O argumento inteiro esta na
§2 da spec da story 012.

⭐ Entao ele e COMPOSICAO: roda a cascata da 009 intacta, e so pergunta ao LLM se a
`origem` continuou NULL. A ordem da spec 02 — memoria > NCM > LLM > bucket — sai
de graca: manual e memoria o passo 1 da cascata protege, NCM ja resolveu, e so o
que caiu no bucket chega aqui.

⚠️ Nenhuma funcao daqui chama `conexao.commit()` — mesma regra de
`categorizacao.py`, `varredura.py` e dos demais.
"""

from datetime import UTC, datetime

from nfe_parser.categorizacao import classificar_produto


def classificar_produto_com_llm(conexao, produto_id, ncm, llm=None):
    """Roda a cascata e, se o produto ficou no bucket, pergunta ao `llm`.

    `llm` e uma funcao `llm(descricao, slugs) -> (slug, confianca) | None`, e
    `None` e o padrao: sem ela, o resultado e EXATAMENTE o de
    `classificar_produto`. E isso que torna o LLM opt-in.

    ⚠️ O produto que o LLM resgata e gravado DUAS vezes na mesma transacao:
    primeiro no bucket, pela cascata; depois na categoria do LLM. Custo assumido
    da composicao — ninguem de fora ve o estado do meio.

    🔴 A condicao para perguntar e `origem is None`, comparada so com `is not
    None`. ⛔ Nunca contra a lista de valores de `origem` (risco R1 do recorte).

    ⚠️ Produto sem `descricao_exemplo` nao e enviado: sem texto, nao ha pergunta.

    ⭐ A lista de slugs vem do banco, SEM o bucket e EM ORDEM. Sem o `ORDER BY` a
    lista mudaria de ordem entre execucoes, e o prompt tambem. Categoria apagada
    nao aparece: a lapide da 011 guarda o slug FORA de `categorias`.

    🔴 O slug que volta e conferido NO BANCO antes de gravar, mesmo que o `llm`
    ja confira a lista. O `llm` e um parametro e pode ser QUALQUER funcao; quem
    garante que nenhuma categoria e inventada e esta consulta. E o `AND
    is_bucket = 0` impede o LLM de "escolher" o bucket: com `origem = 'llm'` ali,
    o produto sairia da varredura para sempre sem ter sido classificado.
    """

    categoria = classificar_produto(conexao, produto_id, ncm)
    if llm is None:
        return categoria

    origem, descricao = conexao.execute(
        "SELECT origem, descricao_exemplo FROM produtos WHERE id = ?", (produto_id,)
    ).fetchone()
    if origem is not None or not descricao:
        return categoria

    slugs = [
        linha[0]
        for linha in conexao.execute(
            "SELECT slug FROM categorias WHERE is_bucket = 0 ORDER BY slug"
        ).fetchall()
    ]

    resposta = llm(descricao, slugs)
    if resposta is None:
        return categoria
    slug, confianca = resposta

    linha = conexao.execute(
        "SELECT id FROM categorias WHERE slug = ? AND is_bucket = 0", (slug,)
    ).fetchone()
    if linha is None:
        return categoria

    conexao.execute(
        "UPDATE produtos SET categoria_id = ?, origem = 'llm', confianca = ?, atualizado_em = ?"
        " WHERE id = ?",
        (linha[0], confianca, datetime.now(UTC).isoformat(), produto_id),
    )
    return linha[0]

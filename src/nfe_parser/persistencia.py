"""Uma nota extraida do XML vira linhas no banco: `notas`, `itens` e `produtos`.

Cada item resolve QUAL produto ele e (ver `produtos.py`) e grava esse
`produto_id` junto.

🔴 NENHUMA FUNCAO DAQUI CHAMA `conexao.commit()`. Resolver o produto e inserir o
item TEM de ser a mesma transacao: com um commit no meio, a nota e os itens ja
estariam gravados quando a resolucao de um item POSTERIOR falhasse, e o banco
ficaria com item sem produto, sem sintoma nenhum. Quem abre e fecha a transacao
e `importar`.

⭐ O SQL usa parametros NOMEADOS (`:chave`), e nao `?`. Com `?`, a lista de
colunas e a lista de valores sao duas sequencias que tem de bater por POSICAO, e
trocar duas de lugar grava um campo na coluna do outro sem erro nenhum. Com o
nome, cada valor e procurado pela chave no dicionario — e as chaves que
`extrair_nota` devolve ja sao os nomes das colunas.

⛔ Este modulo NAO classifica. O produto nasce com `categoria_id` e `origem` NULL,
que e o estado "pendente" que `varredura.py` procura depois.
"""

from datetime import UTC, datetime

from nfe_parser.produtos import resolver_produto_por_gtin, resolver_produto_por_texto

_INSERIR_NOTA = """
    INSERT INTO notas (
      chave, modelo, serie, numero, dh_emi, emit_nome, emit_cnpj, emit_municipio,
      emit_uf, valor_total, forma_pagamento, xml_raw, importacao_id, criado_em
    ) VALUES (
      :chave, :modelo, :serie, :numero, :dh_emi, :emit_nome, :emit_cnpj, :emit_municipio,
      :emit_uf, :valor_total, :forma_pagamento, :xml_raw, :importacao_id, :criado_em
    )
"""

_INSERIR_ITEM = """
    INSERT INTO itens (
      nota_chave, n_item, descricao, cprod, ncm, gtin, quantidade, unidade,
      valor_unitario, valor_linha, criado_em, produto_id
    ) VALUES (
      :nota_chave, :n_item, :descricao, :cprod, :ncm, :gtin, :quantidade, :unidade,
      :valor_unitario, :valor_linha, :criado_em, :produto_id
    )
"""


def resolver_produto_do_item(conexao, item, emit_cnpj):
    """Despacha um item de nota para a resolucao de identidade que serve a ele.

    A regra e curta: quem tem codigo de barras se identifica por ele; quem nao
    tem cai na chave de texto, que so vale DENTRO da loja que emitiu.

    🔴 Ele mora AQUI, e nao em `produtos.py`, de proposito. A regra de despacho
    e uma politica sobre ITEM DE NOTA, e aquele modulo declara no cabecalho que
    nao sabe o que e um item: ele fala de GTIN e de texto+CNPJ, nunca de `itens`.
    Este modulo existe justamente para transformar item de nota em linha de
    banco, e e aqui que a politica pertence.

    ⚠️ Item sem GTIN em nota sem CNPJ (emitente com CPF) levanta `ValueError`,
    vindo de `resolver_produto_por_texto`. ⛔ O erro SOBE e derruba o lote:
    engoli-lo deixaria `produto_id` NULL em silencio, e uma chave de texto sem
    loja nao identificaria nada.
    """

    if item["gtin"]:
        return resolver_produto_por_gtin(conexao, item["gtin"], item["descricao"])
    return resolver_produto_por_texto(conexao, item["descricao"], emit_cnpj)


def persistir_nota(conexao, extraido: dict, importacao_id: int | None = None) -> str:
    """Persiste uma nota e seus itens, resolvendo a identidade de cada item.

    Devolve `"duplicada"` se a chave ja existe, e `"nova"` se gravou.

    ⭐ A checagem de duplicada e a PRIMEIRA coisa: nota repetida sai pela porta de
    cima sem criar produto nenhum.

    `{**nota, "criado_em": agora}` monta um dicionario NOVO com tudo de `nota`
    mais as chaves da direita — sem alterar o `nota` que veio de fora.
    """

    nota = extraido["nota"]
    if conexao.execute("SELECT 1 FROM notas WHERE chave = ?", (nota["chave"],)).fetchone():
        return "duplicada"

    agora = datetime.now(UTC).isoformat()
    conexao.execute(_INSERIR_NOTA, {**nota, "importacao_id": importacao_id, "criado_em": agora})

    for item in extraido["itens"]:
        produto_id = resolver_produto_do_item(conexao, item, nota["emit_cnpj"])
        conexao.execute(
            _INSERIR_ITEM,
            {**item, "nota_chave": nota["chave"], "produto_id": produto_id, "criado_em": agora},
        )

    return "nova"

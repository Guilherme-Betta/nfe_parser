"""A varredura: rodar a cascata de novo sobre quem ainda nao tem resposta.

Este modulo existe porque o MAPA DE NCM CRESCE. Um produto que chegou antes de a
ancora dele existir caiu no bucket; quando a ancora entra, alguem tem de voltar la
e resgata-lo. `classificar_produto` faz isso para UM produto; esta funcao e a
passagem sobre todos os pendentes.

🔴 Ele mora em modulo PROPRIO, e nao em `categorizacao.py`, porque PRECISA ler
`itens`: a tabela `produtos` nao tem coluna `ncm`, e e do item que ele vem. A
cascata recebe o `ncm` por parametro, e e isso que a mantem testavel sem nota
nenhuma no banco. Este e o modulo que liga as duas coisas — ⛔ sem reimplementar
degrau nenhum.

⭐ O `llm` e opcional e so e repassado: sem ele, a varredura e so NCM e bucket.

⚠️ Nenhuma funcao daqui chama `conexao.commit()`. Quem abriu a transacao e que a
fecha.

⚠️ `importar` NAO chama esta funcao, e isso e deliberado. `abrir_banco` nao semeia
a taxonomia, e `categoria_do_bucket` levanta em banco sem `is_bucket = 1`. Banco
sem seed e legal, e importar nele tem de continuar funcionando: com a varredura
dentro da importacao, TODA importacao em banco nao semeado explodiria. Quem decide
varrer e quem tem taxonomia carregada.
"""

from nfe_parser.categorizacao import decidir_categoria, gravar_decisao


def classificar_produtos_pendentes(conexao, llm=None) -> int:
    """Roda a cascata sobre todo produto PENDENTE. Devolve quantos sairam de la.

    🔴 PENDENTE E `origem IS NULL`, e nunca `categoria_id IS NULL`. E o mesmo erro
    que o cabecalho de `categorizacao.py` ja nomeia: o que protege um produto e a
    `origem`, NAO o fato de ele ja ter categoria. Produto no bucket TEM
    `categoria_id` preenchido e `origem` NULL — e e justamente ele que esta
    funcao existe para resgatar. Uma consulta por `categoria_id IS NULL` nunca
    mais olharia para o bucket, e o produto ficaria preso la para sempre.

    ⭐ A condicao cobre os dois casos de uma vez: produto recem-criado pela
    importacao, e produto que caiu no bucket. `manual` e `memoria` ficam de fora
    porque a cascata os respeita; `ncm` e `llm` porque ja estao resolvidos.

    ⭐ Por isso a varredura vai direto a `decidir_categoria` + `gravar_decisao`,
    sem passar por `classificar_produto`: pendente nunca e `manual` nem
    `memoria`, entao o degrau 1 nao teria o que fazer aqui.

    ⚠️ O `.fetchall()` do inicio nao e preguica: o laco faz UPDATE em `produtos`,
    e iterar um cursor aberto sobre a mesma tabela que se esta gravando nao tem
    resultado definido no SQLite.

    ⭐ Resgatado e quem SAIU do pendente, ⛔ nao quem foi visitado: o que caiu de
    novo no bucket volta com `origem` None. Por isso a comparacao e `is not
    None`, ⛔ e nunca contra a lista de valores validos de `origem`.
    """

    pendentes = conexao.execute(
        "SELECT id, descricao_exemplo FROM produtos WHERE origem IS NULL"
    ).fetchall()
    resgatados = 0

    for produto_id, descricao in pendentes:
        ncm = _ncm_mais_recente(conexao, produto_id)
        decisao = decidir_categoria(conexao, ncm, descricao, llm)
        gravar_decisao(conexao, produto_id, decisao)
        if decisao.origem is not None:
            resgatados += 1

    return resgatados


def _ncm_mais_recente(conexao, produto_id):
    """O NCM do item de MAIOR `id` do produto, ou `None` se ele nao tem item.

    ⚠️ Um produto pode ter itens com NCMs diferentes — lojas classificam
    diferente —, e a escolha e a informacao mais nova. ⛔ Sem `ORDER BY` o SQLite
    nao garante ordem nenhuma, e o defeito passaria despercebido em banco
    pequeno. Produto sem item recebe `None`, que a cascata ja sabe tratar.
    """

    linha = conexao.execute(
        "SELECT ncm FROM itens WHERE produto_id = ? ORDER BY id DESC LIMIT 1",
        (produto_id,),
    ).fetchone()
    return linha[0] if linha else None

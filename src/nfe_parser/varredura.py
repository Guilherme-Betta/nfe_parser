"""A varredura: rodar a cascata de novo sobre quem ainda nao tem resposta.

Este modulo existe porque o MAPA DE NCM CRESCE. Um produto que chegou antes de a
ancora dele existir caiu no bucket; quando a ancora entra, alguem tem de voltar
la e resgata-lo. `classificar_produto` faz isso para UM produto por vez, e esta
funcao e a passagem sobre todos.

🔴 E ele mora em modulo PROPRIO, e nao dentro de `categorizacao.py`, por uma
razao que aquele modulo declara no proprio cabecalho: "este modulo nao le
`itens`: ele RECEBE o `ncm` por parametro. Quem os liga e a story 013". Esta
funcao PRECISA ler `itens` — a tabela `produtos` nao tem coluna `ncm`, e e do
item que ele vem. Poe-la la quebraria a invariante que mantem a cascata testavel
sem nota nenhuma no banco.

⭐ Entao este e o modulo "que os liga": ele conhece `produtos`, conhece `itens`, e
chama a cascata. ⛔ Ele NAO reimplementa degrau nenhum dela.

⭐ Desde a story 012 ele chama a cascata COM o degrau do LLM
(`classificar_produto_com_llm`), e passa adiante o `llm` que receber. Sem `llm`,
o comportamento e exatamente o da 013: o LLM e opt-in, e quem o liga e quem
chama a varredura.

⚠️ Nenhuma funcao daqui chama `conexao.commit()` — mesma regra de `produtos.py`,
`categorizacao.py`, `seed.py`, `taxonomia.py` e, desde a 013, `persistencia.py`.

⚠️ `importar` NAO chama esta funcao, e isso e deliberado. `abrir_banco` nao
semeia a taxonomia, e `categoria_do_bucket` levanta em banco sem `is_bucket = 1`.
Banco sem seed e legal, e importar nele tem de continuar funcionando: com a
varredura dentro da importacao, TODA importacao em banco nao semeado explodiria.
Quem decide varrer e quem tem taxonomia carregada.
"""

from nfe_parser.classificacao_llm import classificar_produto_com_llm


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
    porque a cascata os respeita; `ncm` fica de fora porque ja esta resolvido.

    ⚠️ O `.fetchall()` do inicio nao e preguica: o laco faz UPDATE em `produtos`,
    e iterar um cursor aberto sobre a mesma tabela que se esta gravando nao tem
    resultado definido no SQLite.

    ⚠️ O NCM que vale e o do item de MAIOR `id`, o mais recente. Um produto pode
    ter itens com NCMs diferentes — lojas classificam diferente —, e a escolha e
    a informacao mais nova. ⛔ Sem `ORDER BY` o SQLite nao garante ordem nenhuma,
    e o defeito passaria despercebido em banco pequeno. Produto sem item nenhum
    recebe `ncm = None`, que a cascata ja sabe tratar.

    ⭐ A releitura da `origem` depois de classificar e o que define o retorno:
    resgatado e quem SAIU do pendente, ⛔ nao quem foi visitado. Quem caiu no
    bucket continua com `origem` NULL e sera varrido de novo — e e por isso que a
    comparacao e `is not None`, e ⛔ nunca contra a lista de valores validos, que
    a story 012 vai aumentar.
    """

    pendentes = conexao.execute("SELECT id FROM produtos WHERE origem IS NULL").fetchall()
    resgatados = 0

    for (produto_id,) in pendentes:
        linha = conexao.execute(
            "SELECT ncm FROM itens WHERE produto_id = ? ORDER BY id DESC LIMIT 1",
            (produto_id,),
        ).fetchone()
        ncm = linha[0] if linha else None

        classificar_produto_com_llm(conexao, produto_id, ncm, llm)
        origem = conexao.execute(
            "SELECT origem FROM produtos WHERE id = ?", (produto_id,)
        ).fetchone()[0]
        if origem is not None:
            resgatados += 1

    return resgatados

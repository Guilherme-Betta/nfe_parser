"""Identidade de produto: descobrir QUAL produto e cada item de nota fiscal.

Implementa o paragrafo 3 de `specs/02_spec_classificacao.md`. ⛔ Nao diz nada
sobre o que o produto E — categoria e a story seguinte, e `categoria_id` nasce
NULL em toda linha criada aqui.

A tabela `itens` guarda um evento de compra por linha: a descricao crua do
`xProd`, o `gtin` quando existe. Para perguntar "quanto gastei em arroz este
mes" alguem precisa primeiro responder "estas 14 linhas sao o mesmo arroz". E o
que este modulo faz.

Ha DUAS identidades, e elas nao valem a mesma coisa:

- **GTIN** — o codigo de barras e global. Duas lojas que vendem o mesmo produto
  mandam o mesmo GTIN, e o casamento entre elas e confiavel.
- **Texto + CNPJ** — sem codigo de barras, a chave e a descricao normalizada
  MAIS o CNPJ de quem emitiu. Cada loja escreve o `xProd` do seu jeito, entao
  este casamento vale so DENTRO da loja.

🔴 A assimetria e requisito, nao limitacao a ser escondida. A spec chama isso de
honestidade: casar por texto entre lojas produziria historico de preco
misturando produtos diferentes, e o numero sairia errado sem sintoma nenhum. A
coluna `identidade_origem` existe para avisar quem consome qual dos dois casos
produziu aquela linha.

⚠️ Nenhuma funcao daqui chama `conexao.commit()`. Quem abriu a transacao e que a
fecha. E deliberado: a divida tecnica de `persistir_nota` commitar por conta
propria ja esta anotada para a story 013, e nao se paga uma divida abrindo outra
igual ao lado.
"""

import unicodedata
from datetime import UTC, datetime

# Whitelist EXPLICITA, e ela nao pode virar `str.isalnum()`. Foi medido: o
# `isalnum` do Python e Unicode-aware e considera letra ou numero caracteres
# como `º`, `ø` e `µ`. Nenhum deles decompoe em NFD — a barra do `ø` faz parte
# do glifo, nao e acento —, entao passariam pelo filtro e a saida deixaria de
# ser ASCII. O estrago seria silencioso: um dia dois produtos que deviam casar
# nao casam porque um deles tem um `º` no meio.
PERMITIDOS = "abcdefghijklmnopqrstuvwxyz0123456789"


def normalizar_descricao(descricao: str) -> str:
    """Reduz a descricao crua a uma chave de igualdade estavel.

    Duas descricoes que sao o mesmo produto escrito de jeitos diferentes tem de
    sair identicas daqui. O resultado so contem `a-z`, `0-9` e espaco simples.

    Sao quatro passos, e a ORDEM entre o segundo e o terceiro nao e estilo: se o
    filtro rodasse antes da decomposicao, o `ç` nao viraria `c` — seria
    descartado inteiro, e `acucar` sairia como `a ucar`, dois tokens onde havia
    um.

    Pontuacao vira ESPACO, nao vira vazio. Apagar juntaria palavras que a
    pontuacao separava: `PAO/QUEIJO` viraria `paoqueijo`, um token que nao existe
    em descricao nenhuma. Trocar por espaco no maximo parte o que estava junto.

    ⛔ Numero e unidade atravessam sem tratamento: o MVP nao interpreta numero.
    Como efeito, `1,5L` sai como `1 5l` — a virgula e pontuacao como qualquer
    outra. Isso esta certo, porque o que se quer aqui e uma chave de igualdade e
    nao um valor a ser lido. O que importa e `1,5L` e `1.5 L` cairem no mesmo
    lugar, e caem.

    A funcao e total: entrada vazia, so espacos ou so pontuacao devolve `""`.
    ⚠️ Colapsar tudo isso na mesma chave e limitacao conhecida e aceita — na
    pratica `xProd` e NOT NULL e nunca e so pontuacao.
    """

    descricao = descricao.lower()
    descricao = unicodedata.normalize("NFD", descricao)
    descricao = "".join(c for c in descricao if unicodedata.category(c) != "Mn")
    descricao = "".join(c if c in PERMITIDOS else " " for c in descricao)
    descricao = " ".join(descricao.split())
    return descricao


def resolver_produto_por_gtin(conexao, gtin, descricao_exemplo):
    """Devolve o `id` do produto daquele codigo de barras, criando se faltar.

    Procura primeiro, insere so se nao achou. ⛔ Nao se usa `INSERT OR IGNORE`
    nem `ON CONFLICT`: quando o INSERT e descartado, `lastrowid` fica com um
    valor que nao e o id daquela linha, e a funcao devolveria o id errado a
    partir da segunda chamada — sem erro nenhum aparecendo.

    Achar a linha nao atualiza nada. O mesmo GTIN vindo com outra descricao e o
    mesmo produto: o codigo de barras e global, e duas lojas descrevem a mesma
    caixa de arroz de jeitos diferentes. `descricao_exemplo` guarda a primeira
    descricao vista, crua, so para leitura humana.

    `descricao_normalizada` e `emit_cnpj` ficam NULL de proposito. O indice
    unico `ux_produtos_texto` so cobre linhas com `gtin IS NULL`, entao valores
    ali nao teriam unicidade garantida — e ainda poderiam ser devolvidos por
    engano pela busca por texto.

    🔴 GTIN vazio levanta `ValueError` em vez de seguir. Sem isso o erro seria
    MUDO e caro: `WHERE gtin = NULL` nao casa com nada em SQL — nem com outra
    linha de gtin NULL —, entao cada chamada criaria uma linha nova, e o indice
    parcial nao reclamaria porque ele so cobre `gtin IS NOT NULL`. A tabela
    encheria de produtos fantasma sem nada quebrar. Quem nao tem codigo de
    barras vai para `resolver_produto_por_texto`.
    """

    if not gtin:
        raise ValueError(
            "resolver_produto_por_gtin exige um GTIN nao vazio;"
            " item sem codigo de barras se resolve por resolver_produto_por_texto"
        )

    cursor = conexao.execute("SELECT id FROM produtos WHERE gtin = ?", (gtin,))
    resultado = cursor.fetchone()

    if resultado:
        return resultado[0]

    criado_em = datetime.now(UTC).isoformat()
    cursor.execute(
        """
        INSERT INTO produtos (identidade_origem, gtin, descricao_exemplo,
                              criado_em, atualizado_em)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("gtin", gtin, descricao_exemplo, criado_em, criado_em),
    )

    return cursor.lastrowid


def resolver_produto_por_texto(conexao, descricao, emit_cnpj):
    """Devolve o `id` do produto SEM codigo de barras, criando se faltar.

    Mesma forma da resolucao por GTIN — procurar, criar se nao achou, devolver o
    id — com outra chave: o par (descricao normalizada, CNPJ da loja).

    🔴 O `gtin IS NULL` do SELECT nao e enfeite. A busca por texto so pode
    enxergar linhas sem codigo de barras: quem tem GTIN e identificado pelo
    GTIN, e nunca deve ser devolvido aqui nem que a descricao seja identica. O
    indice unico que garante a unicidade deste par tambem so cobre linhas com
    `gtin IS NULL` — sem a condicao, o SELECT procuraria em linhas que aquele
    indice nem cobre.

    🔴 O CNPJ faz parte da chave, e casar so pela descricao seria pior que nao
    casar. `identidade_origem='texto'` e o sinal de *best-effort* que os
    componentes consumidores leem para saber que aquele casamento vale dentro da
    loja, e nao entre lojas.

    🔴 CNPJ vazio levanta `ValueError` pelo mesmo motivo que o GTIN vazio na
    funcao acima: `WHERE emit_cnpj = NULL` nao casa com nada, cada chamada
    criaria uma linha, e o indice unico nao pegaria — ele indexa o par, e um par
    com NULL dentro nao colide com outro igual. Um produto sem loja tambem nao
    significaria nada: a chave de texto so vale DENTRO de uma loja.
    """

    if not emit_cnpj:
        raise ValueError(
            "resolver_produto_por_texto exige o CNPJ do emitente:"
            " a chave de texto so identifica um produto dentro de uma loja"
        )

    normalizada = normalizar_descricao(descricao)
    cursor = conexao.execute(
        """
        SELECT id FROM produtos
        WHERE gtin IS NULL AND descricao_normalizada = ? AND emit_cnpj = ?
        """,
        (normalizada, emit_cnpj),
    )
    resultado = cursor.fetchone()

    if resultado:
        return resultado[0]

    criado_em = datetime.now(UTC).isoformat()
    cursor.execute(
        """
        INSERT INTO produtos (identidade_origem, descricao_normalizada, emit_cnpj,
                              descricao_exemplo, criado_em, atualizado_em)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("texto", normalizada, emit_cnpj, descricao, criado_em, criado_em),
    )

    return cursor.lastrowid

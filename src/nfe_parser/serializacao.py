"""A saida do parser: uma nota do banco vira JSON.

Fecha a ultima invariante do §5 da `specs/01_spec_parser_modelo.md` ("Saidas
serializam em JSON"). Este e o unico modulo de `src/` que importa `json`: os
outros leem XML e gravam no SQLite, e este entrega para fora.

⭐ DINHEIRO SAI DUAS VEZES, e as duas do mesmo inteiro. O campo `_centavos` e a
fonte de verdade, espelho da coluna do banco, e e com ele que se faz conta. A
string ao lado e apresentacao, derivada na hora de serializar -- nunca guardada,
nunca lida do banco. Nao sao dois dados: e um dado e uma apresentacao dele.

📋 Contrato para quem consome: some o `_centavos`, exiba a string. Somar strings
esta errado.
"""

import json


def de_centavos(centavos: int) -> str:
    """Formata um valor em centavos como string decimal de duas casas.

    ⛔ SO ARITMETICA DE INTEIRO. `centavos / 100` e divisao de ponto flutuante
    binario, que nao representa decimais exatamente -- acima de 2**53 o float64
    nem representa mais inteiros, e o ultimo centavo se perde em silencio. Com
    `//` e `%` o resultado e exato em qualquer magnitude.

    O sinal e separado antes da conta porque, em Python, `-5 // 100` e -1 e
    `-5 % 100` e 95: a forma ingenua devolveria "-1.95" para cinco centavos
    negativos.
    """
    sinal = "-" if centavos < 0 else ""
    valor = abs(centavos)
    reais = valor // 100
    resto = valor % 100
    return f"{sinal}{reais}.{resto:02d}"


def nota_para_json(conexao, chave: str) -> str | None:
    r"""Devolve a nota `chave` e seus itens como STRING JSON, ou None se nao existe.

    O desfecho para chave ausente e `None`, e nao excecao nem `"{}"`: "nao achei"
    e um resultado normal de consulta, e `"{}"` seria um JSON valido que mente --
    quem o recebesse acharia que existe uma nota sem nenhum campo.

    ⛔ `xml_raw`, `importacao_id` e `criado_em` ficam de fora. O primeiro e o
    documento inteiro (e `nfe_parser` e repositorio publico); os outros dois sao
    escrituracao interna do banco, nao fazem parte da nota.

    O `ensure_ascii=False` nao e enfeite: o padrao do `json.dumps` escaparia
    "Sao Paulo" com til para `"S\\u00e3o Paulo"`. O arquivo continua sendo JSON
    valido, mas ilegivel para quem o abre -- e ser legivel e metade da razao de
    existir uma saida em JSON.
    """
    cursor = conexao.execute(
        "SELECT chave, modelo, serie, numero, dh_emi, emit_nome, emit_cnpj,"
        " emit_municipio, emit_uf, valor_total, forma_pagamento, status, cancelado_em"
        " FROM notas WHERE chave = ?",
        (chave,),
    )
    linha = cursor.fetchone()
    if linha is None:
        return None

    # `cursor.description` da os nomes das colunas na ordem em que vieram, o que
    # evita montar o dicionario contando posicoes -- onde nasce campo trocado.
    dados = dict(zip([d[0] for d in cursor.description], linha))

    # `status` e `cancelado_em` sao copiados como vieram, sem conversao. O SQLite
    # devolve coluna TEXT como `str`, e qualquer tentativa de "normalizar" data
    # aqui so pode destruir o dado que o banco ja guarda pronto.
    saida = {
        "chave": dados["chave"],
        "modelo": dados["modelo"],
        "serie": dados["serie"],
        "numero": dados["numero"],
        "dh_emi": dados["dh_emi"],
        "emit_nome": dados["emit_nome"],
        "emit_cnpj": dados["emit_cnpj"],
        "emit_municipio": dados["emit_municipio"],
        "emit_uf": dados["emit_uf"],
        "valor_total_centavos": dados["valor_total"],
        "valor_total": de_centavos(dados["valor_total"]),
        "forma_pagamento": dados["forma_pagamento"],
        "status": dados["status"],
        "cancelado_em": dados["cancelado_em"],
    }
    saida["itens"] = _itens_da_nota(conexao, chave)

    return json.dumps(saida, ensure_ascii=False)


def _itens_da_nota(conexao, chave: str) -> list[dict]:
    """Os itens da nota, ordenados por `n_item`. Lista vazia quando nao ha nenhum.

    O `ORDER BY` nao e detalhe: sem ele o SQLite nao garante ordem. Em banco
    pequeno a ordem de insercao quase sempre coincide com a ordenada, entao o
    defeito passaria despercebido fora de um teste que embaralha de proposito.

    `id` e `nota_chave` ficam de fora: o primeiro e chave artificial do SQLite, o
    segundo ja esta na nota que contem a lista.
    """
    cursor = conexao.execute(
        "SELECT n_item, descricao, cprod, ncm, gtin, quantidade, unidade,"
        " valor_unitario, valor_linha"
        " FROM itens WHERE nota_chave = ? ORDER BY n_item",
        (chave,),
    )
    colunas = [d[0] for d in cursor.description]

    itens = []
    for linha in cursor.fetchall():
        item = dict(zip(colunas, linha))
        centavos = item["valor_linha"]
        itens.append(
            {
                "n_item": item["n_item"],
                "descricao": item["descricao"],
                "cprod": item["cprod"],
                "ncm": item["ncm"],
                "gtin": item["gtin"],
                "quantidade": item["quantidade"],
                "unidade": item["unidade"],
                "valor_unitario": item["valor_unitario"],
                "valor_linha_centavos": centavos,
                "valor_linha": de_centavos(centavos),
            }
        )
    return itens

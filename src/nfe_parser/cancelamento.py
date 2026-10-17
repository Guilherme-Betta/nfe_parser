from datetime import UTC, datetime

from nfe_parser.eventos import ler_evento

# O unico `tpEvento` que cancela uma nota. Os outros existem e sao validos --
# `110110` e carta de correcao, por exemplo -- mas nao mudam o status da nota.
TP_EVENTO_CANCELAMENTO = "110111"


def extrair_evento(xml_texto: str) -> dict:
    """Le um evento e devolve os tres campos que o cancelamento usa.

    Campo ausente vira `None` em vez de excecao: um evento capenga e dado ruim,
    e quem decide o que fazer com ele e `aplicar_cancelamento`. So um XML que
    nao ABRE vira erro (`ValueError`).

    ⭐ A leitura e de `eventos.ler_evento`, pelo binding GENERICO do nfelib: o de
    cancelamento recusava a carta de correcao real e a marcava `invalida` (ver o
    cabecalho de `eventos.py`).

    ⚠️ O `getattr(..., "value", ...)` de la nao e paranoia: o xsdata devolve
    `tpEvento` como ENUM quando o valor e conhecido (o texto fica em `.value`) e
    como STRING CRUA para qualquer outro. Um `.value` direto funciona no caminho
    feliz e estoura `AttributeError` na primeira carta de correcao que chegar.
    """

    evento = ler_evento(xml_texto)
    return {campo: evento[campo] for campo in ("ch_nfe", "tp_evento", "dh_evento")}


def aplicar_cancelamento(conexao, evento: dict) -> str:
    """Cancela a nota que o evento aponta. Devolve o `resultado` para o log.

    A regra e uma so: existe nota no banco para esta chave, e este evento e de
    cancelamento? Entao `'cancelamento_aplicado'`. Caso contrario
    `'cancelamento_orfao'`, sem escrever nada.

    ⛔ Um evento orfao NUNCA inventa a nota que falta. Sem nota, nada e escrito.
    """

    ch_nfe = evento.get("ch_nfe")
    tp_evento = evento.get("tp_evento")

    if tp_evento != TP_EVENTO_CANCELAMENTO or ch_nfe is None:
        return "cancelamento_orfao"

    query_check = "SELECT 1 FROM notas WHERE chave = ?"
    if not conexao.execute(query_check, (ch_nfe,)).fetchone():
        return "cancelamento_orfao"

    # ⭐ O `AND status = 'ok'` e o que torna a funcao idempotente: reimportar o
    # mesmo lote nao move o `cancelado_em` da primeira vez. O desfecho continua
    # sendo "aplicado" porque a pergunta que ele responde e "este evento
    # corresponde a uma nota cancelada?", e a resposta e sim nas duas vezes.
    #
    # `cancelado_em` e a hora do CANCELAMENTO, como veio no XML (spec 01 §6.2). A
    # hora da importacao so entra se o evento nao trouxer `dhEvento` — fora do
    # leiaute, mas nota cancelada nunca fica sem carimbo.
    cancelado_em = evento.get("dh_evento") or datetime.now(UTC).isoformat()
    query_update = (
        "UPDATE notas SET status = 'cancelada', cancelado_em = ? WHERE chave = ? AND status = 'ok'"
    )
    conexao.execute(query_update, (cancelado_em, ch_nfe))

    return "cancelamento_aplicado"


def cancelamento_guardado(conexao, chave):
    """O cancelamento ja guardado em `eventos` para a nota `chave`, ou `None`.

    Serve a nota que chega DEPOIS do seu cancelamento, num lote posterior (spec 01
    §6.2): o evento foi `cancelamento_orfao` no lote dele, mas ficou guardado.
    Devolve as chaves que `aplicar_cancelamento` le, mais o `importacao_id` do
    lote em que o cancelamento chegou.

    ⭐ `ORDER BY id`: se houver mais de um (fora do leiaute), o primeiro guardado
    vence — a mesma regra do carimbo.
    """

    linha = conexao.execute(
        "SELECT dh_evento, importacao_id FROM eventos"
        " WHERE chave = ? AND tp_evento = ? ORDER BY id LIMIT 1",
        (chave, TP_EVENTO_CANCELAMENTO),
    ).fetchone()
    if linha is None:
        return None
    dh_evento, importacao_id = linha
    return {
        "ch_nfe": chave,
        "tp_evento": TP_EVENTO_CANCELAMENTO,
        "dh_evento": dh_evento,
        "importacao_id": importacao_id,
    }

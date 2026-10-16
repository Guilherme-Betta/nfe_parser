"""Eventos de NF-e: ler qualquer um, guardar todo o que tem chave, listar por nota.

Spec 01 §2 e §6.2. Decisao do Gui de 2026-10-16: todo evento que abre e traz
`chNFe` e guardado, com o XML inteiro — coerente com o `xml_raw` das notas, e a
informacao nao se perde se o arquivo original sumir. Quem CANCELA continua sendo
`cancelamento.py`; este modulo so le, guarda e devolve.

🔴 A leitura usa o binding GENERICO de evento do nfelib, e nao o de cancelamento.
O de cancelamento descreve o `detEvento` de um cancelamento, e uma carta de
correcao real traz `xCorrecao`, que ele nao conhece: o parser levantava e a carta
virava `invalida`. No generico, o `detEvento` e um curinga (`any_element`) que
aceita o detalhe de qualquer tipo de evento.

⚠️ Nenhuma funcao daqui chama `conexao.commit()`. Quem abriu a transacao e que a
fecha (aqui, o lote de `importar`).
"""

from datetime import UTC, datetime

from nfelib.nfe_evento_generico.bindings.v1_0.proc_evento_nfe_v1_00 import ProcEventoNfe
from xsdata.exceptions import ParserError
from xsdata.formats.dataclass.parsers import XmlParser

TP_CARTA_DE_CORRECAO = "110110"


def ler_evento(xml_texto: str) -> dict:
    """Le um evento de qualquer tipo. Campo ausente vira `None`; so XML que nao abre levanta.

    Devolve `ch_nfe`, `tp_evento`, `dh_evento`, `n_seq`, `descricao` e `correcao`
    (este so na carta de correcao).

    ⚠️ O `getattr(..., "value", ...)` cobre o xsdata devolvendo enum para valor
    conhecido e string crua para o resto — ver `cancelamento.extrair_evento`.
    """

    try:
        proc = XmlParser().from_string(xml_texto, ProcEventoNfe)
    except ParserError:
        raise ValueError("Erro ao parsear o XML") from None

    inf = proc.evento.infEvento if proc.evento is not None else None
    if inf is None:
        return dict.fromkeys(("ch_nfe", "tp_evento", "dh_evento", "n_seq", "descricao", "correcao"))

    detalhe = _campos_do_detalhe(inf.detEvento)
    return {
        "ch_nfe": getattr(inf.chNFe, "value", inf.chNFe),
        "tp_evento": getattr(inf.tpEvento, "value", inf.tpEvento),
        "dh_evento": getattr(inf.dhEvento, "value", inf.dhEvento),
        "n_seq": int(inf.nSeqEvento) if inf.nSeqEvento else None,
        "descricao": detalhe.get("descEvento"),
        "correcao": detalhe.get("xCorrecao"),
    }


def _campos_do_detalhe(det):
    """`{nome local: texto}` dos filhos do `detEvento` curinga. Sem detalhe, `{}`.

    ⭐ Cada filho vem como `AnyElement` com o nome qualificado
    (`{namespace}descEvento`); o nome local e o que vem depois do `}`.
    """
    if det is None:
        return {}
    return {elemento.qname.split("}")[-1]: elemento.text for elemento in det.any_element}


def guardar_evento(conexao, evento, xml_texto, importacao_id=None):
    """Guarda o evento ja lido. Sem `ch_nfe` nao ha nota a que liga-lo, e nada e gravado.

    ⭐ `ON CONFLICT DO NOTHING`: reimportar o mesmo evento nao duplica, e o primeiro
    guardado vence — a mesma regra do `cancelado_em`. `n_seq` ausente vale 1, que e
    o que o leiaute manda para o primeiro evento de cada tipo.
    """
    if evento["ch_nfe"] is None or evento["tp_evento"] is None:
        return
    conexao.execute(
        "INSERT INTO eventos (chave, tp_evento, n_seq, dh_evento, descricao, correcao,"
        " xml_raw, importacao_id, criado_em) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
        " ON CONFLICT (chave, tp_evento, n_seq) DO NOTHING",
        (
            evento["ch_nfe"],
            evento["tp_evento"],
            evento["n_seq"] or 1,
            evento["dh_evento"],
            evento["descricao"],
            evento["correcao"],
            xml_texto,
            importacao_id,
            datetime.now(UTC).isoformat(),
        ),
    )


def eventos_da_nota(conexao, chave):
    """Os eventos guardados da nota `chave`, na ordem de chegada. ⛔ Sem o XML."""
    linhas = conexao.execute(
        "SELECT tp_evento, n_seq, dh_evento, descricao, correcao FROM eventos"
        " WHERE chave = ? ORDER BY id",
        (chave,),
    ).fetchall()
    campos = ("tp_evento", "n_seq", "dh_evento", "descricao", "correcao")
    return [dict(zip(campos, linha, strict=True)) for linha in linhas]

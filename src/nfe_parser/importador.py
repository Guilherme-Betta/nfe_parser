"""Importar um lote — um `.zip` ou um `.xml` avulso — para o banco.

Cada arquivo vira UMA linha em `importacao_arquivos`, com o desfecho dele no
campo `resultado`, e o lote vira uma linha em `importacoes`, com os contadores.

🔴 Nenhum arquivo derruba o lote por causa do CONTEUDO (C4 da spec 004): XML que
nao abre, nota incompleta, SAT e evento orfao viram linha no log, nao excecao.
O que SOBE e derruba o lote e erro de gravacao — e ai o lote inteiro e desfeito.

⭐ DUAS PASSADAS: primeiro as notas, depois os eventos de cancelamento. E o que
permite aplicar um evento que veio ANTES da sua nota dentro do `.zip`: quando a
segunda passada comeca, todas as notas do lote ja estao no banco.
"""

import hashlib
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from nfe_parser.cancelamento import TP_EVENTO_CANCELAMENTO, aplicar_cancelamento
from nfe_parser.classificador import classificar_xml
from nfe_parser.eventos import guardar_evento, ler_evento
from nfe_parser.extrator import extrair_nota
from nfe_parser.persistencia import persistir_nota


@dataclass(frozen=True)
class _Arquivo:
    """Um XML do lote, ja decodificado e com o tipo descoberto."""

    nome: str
    conteudo: bytes  # os bytes ORIGINAIS: e deles que sai o hash do log
    texto: str
    tipo: str  # o que `classificar_xml` devolveu: "nfe", "evento", "invalida"...


def importar(conexao, caminho, origem: str | None = None) -> int:
    """Importa um `.zip` ou um `.xml` avulso e devolve o id da importacao.

    🔴 O lote e UMA transacao, e quem a abre e fecha e esta funcao. O
    `with conexao:` do `sqlite3` faz as duas metades: se o bloco termina, COMMIT;
    se algo levanta la dentro, ROLLBACK — e a excecao continua subindo.
    ⛔ Ele NAO fecha a conexao; so decide o destino da transacao.

    Sem o ROLLBACK, uma excecao no meio do lote deixaria a transacao aberta com a
    metade ja gravada, e o proximo `commit()` daquela conexao a gravaria junto.
    """

    caminho = Path(caminho)

    with conexao:
        importacao_id = conexao.execute(
            "INSERT INTO importacoes (origem, iniciado_em) VALUES (?, ?)",
            (origem if origem is not None else str(caminho), datetime.now(UTC).isoformat()),
        ).lastrowid

        arquivos = [_decodificar(nome, conteudo) for nome, conteudo in _ler_lote(caminho)]
        notas = [arquivo for arquivo in arquivos if arquivo.tipo != "evento"]
        eventos = [arquivo for arquivo in arquivos if arquivo.tipo == "evento"]

        for arquivo in notas:
            resultado, chave, detalhe = _processar_nota(conexao, importacao_id, arquivo)
            _registrar(conexao, importacao_id, arquivo, resultado, chave, detalhe)

        for arquivo in eventos:
            resultado, chave, detalhe = _processar_evento(conexao, importacao_id, arquivo)
            _registrar(conexao, importacao_id, arquivo, resultado, chave, detalhe)

        _fechar_importacao(conexao, importacao_id)

    return importacao_id


def _ler_lote(caminho):
    """Entrega `(nome, bytes)` de cada XML do lote, seja ele `.zip` ou avulso.

    ⭐ E aqui, e SO aqui, que `.zip` e `.xml` avulso sao diferentes; dai em
    diante o caminho de codigo e um so (C5 da spec 004).

    Uma funcao com `yield` e um GERADOR: ela entrega um item de cada vez a quem a
    percorre, em vez de montar a lista inteira antes de devolver.

    ⚠️ No `.zip`, membro que nao termina em `.xml` (maiuscula ou minuscula) e
    entrada de diretorio sao ignorados: nao viram linha nem entram na contagem.
    """

    if caminho.suffix.lower() != ".zip":
        yield caminho.name, caminho.read_bytes()
        return

    with zipfile.ZipFile(caminho) as arquivo_zip:
        for membro in arquivo_zip.namelist():
            if membro.lower().endswith(".xml") and not membro.endswith("/"):
                yield membro, arquivo_zip.read(membro)


def _decodificar(nome, conteudo):
    texto = conteudo.decode("utf-8", errors="replace")
    return _Arquivo(nome, conteudo, texto, classificar_xml(texto))


def _processar_nota(conexao, importacao_id, arquivo):
    """Grava uma nota do lote. Devolve `(resultado, chave, detalhe)` para o log.

    🔴 `persistir_nota` fica FORA do `try`, e nao e estilo. Dentro dele, um erro de
    gravacao — ou da resolucao de produto — sairia registrado como "XML
    invalido", e o log apontaria para o lugar errado. Erro de gravacao SOBE e
    derruba o lote, que e o desfecho honesto.
    """

    if arquivo.tipo == "nao_suportado_sat":
        return "nao_suportado_sat", None, None
    if arquivo.tipo == "invalida":
        return "invalida", None, "Conteúdo inválido"

    try:
        extraido = extrair_nota(arquivo.texto)
    except ValueError as e:
        return "invalida", None, str(e)

    resultado = persistir_nota(conexao, extraido, importacao_id)
    return resultado, extraido["nota"]["chave"], None


def _processar_evento(conexao, importacao_id, arquivo):
    """Guarda o evento e, se for cancelamento, aplica. Devolve `(resultado, chave, detalhe)`.

    Mesma regra de `_processar_nota`: evento que nao ABRE e `'invalida'`, como
    uma nota que nao abre — sem isso a excecao derrubaria o lote inteiro,
    inclusive as notas boas. Mas falhar ao GRAVAR e outra coisa, e por isso
    guardar e aplicar ficam fora do `try`.

    ⭐ Todo evento com chave e tipo e guardado, inclusive o cancelamento (spec 01
    §6.2). So `110111` cancela; os outros sao `'evento_registrado'`, com a
    descricao no detalhe. 🔴 "Registrado" so para o que FOI guardado: sem chave ou
    sem tipo, o evento continua indo para `aplicar_cancelamento`, que o chama de
    orfao, como antes.
    """

    try:
        evento = ler_evento(arquivo.texto)
    except ValueError as e:
        return "invalida", None, str(e)

    guardado = guardar_evento(conexao, evento, arquivo.texto, importacao_id)
    if guardado and evento["tp_evento"] != TP_EVENTO_CANCELAMENTO:
        return "evento_registrado", evento["ch_nfe"], evento["descricao"]
    return aplicar_cancelamento(conexao, evento), evento["ch_nfe"], None


def _registrar(conexao, importacao_id, arquivo, resultado, chave, detalhe):
    """Grava a linha do arquivo no log do lote.

    ⛔ O hash e dos BYTES originais, nao do texto decodificado: `errors="replace"`
    pode trocar bytes invalidos, e o hash deixaria de identificar o que entrou.
    """

    conexao.execute(
        "INSERT INTO importacao_arquivos"
        " (importacao_id, arquivo, arquivo_hash, chave, resultado, detalhe)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (
            importacao_id,
            arquivo.nome,
            hashlib.sha256(arquivo.conteudo).hexdigest(),
            chave,
            resultado,
            detalhe,
        ),
    )


def _fechar_importacao(conexao, importacao_id):
    """Grava `finalizado_em` e os contadores do lote, contados a partir do log.

    ⚠️ `cancelamento_orfao` entra no total mas nao tem contador proprio: o
    esquema da spec 01 nao tem coluna para ele.
    """

    por_resultado = dict(
        conexao.execute(
            "SELECT resultado, COUNT(*) FROM importacao_arquivos"
            " WHERE importacao_id = ? GROUP BY resultado",
            (importacao_id,),
        )
    )

    conexao.execute(
        """
        UPDATE importacoes SET
          finalizado_em = :finalizado_em,
          total_arquivos = :total_arquivos,
          notas_novas = :notas_novas,
          duplicadas = :duplicadas,
          invalidas = :invalidas,
          nao_suportadas = :nao_suportadas,
          cancelamentos_aplicados = :cancelamentos_aplicados
        WHERE id = :id
        """,
        {
            "id": importacao_id,
            "finalizado_em": datetime.now(UTC).isoformat(),
            "total_arquivos": sum(por_resultado.values()),
            "notas_novas": por_resultado.get("nova", 0),
            "duplicadas": por_resultado.get("duplicada", 0),
            "invalidas": por_resultado.get("invalida", 0),
            "nao_suportadas": por_resultado.get("nao_suportado_sat", 0),
            "cancelamentos_aplicados": por_resultado.get("cancelamento_aplicado", 0),
        },
    )

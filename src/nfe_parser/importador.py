import hashlib
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from nfe_parser.cancelamento import aplicar_cancelamento, extrair_evento
from nfe_parser.classificador import classificar_xml
from nfe_parser.extrator import extrair_nota
from nfe_parser.persistencia import persistir_nota


def _processar_arquivo(conexao, importacao_id, nome, conteudo_bytes) -> None:
    arquivo_hash = hashlib.sha256(conteudo_bytes).hexdigest()
    texto = conteudo_bytes.decode("utf-8", errors="replace")
    classificacao = classificar_xml(texto)
    resultado = None
    chave = None
    detalhe = None

    if classificacao == "nfe":
        try:
            extraido = extrair_nota(texto)
            resultado = persistir_nota(conexao, extraido, importacao_id)
            chave = extraido["nota"]["chave"]
        except ValueError as e:
            resultado = "invalida"
            detalhe = str(e)
    elif classificacao == "nao_suportado_sat":
        resultado = "nao_suportado_sat"
    elif classificacao == "invalida":
        resultado = "invalida"
        detalhe = "Conteúdo inválido"

    # INSERT em `importacao_arquivos`
    conexao.execute(
        "INSERT INTO importacao_arquivos (importacao_id, arquivo, arquivo_hash, chave, resultado, detalhe) VALUES (?, ?, ?, ?, ?, ?)",
        (importacao_id, nome, arquivo_hash, chave, resultado, detalhe),
    )


def _processar_evento(conexao, importacao_id, nome, conteudo_bytes) -> None:
    """Aplica um evento de cancelamento e registra a linha dele no log do lote.

    So e chamada na SEGUNDA passada de `importar`, quando todas as notas do
    lote ja estao no banco -- e o que permite aplicar um evento que veio antes
    da sua nota dentro do `.zip`.
    """

    arquivo_hash = hashlib.sha256(conteudo_bytes).hexdigest()
    texto = conteudo_bytes.decode("utf-8", errors="replace")
    chave = None
    detalhe = None

    try:
        evento = extrair_evento(texto)
        resultado = aplicar_cancelamento(conexao, evento)
        chave = evento["ch_nfe"]
    except ValueError as e:
        # Evento que nao abre e `invalida`, o mesmo tratamento que uma nota que
        # nao abre recebe. Sem este `except` a excecao sobe e derruba o lote
        # inteiro -- inclusive as notas boas, que nao tem culpa nenhuma.
        resultado = "invalida"
        detalhe = str(e)

    # INSERT em `importacao_arquivos`
    conexao.execute(
        "INSERT INTO importacao_arquivos (importacao_id, arquivo, arquivo_hash, chave, resultado, detalhe) VALUES (?, ?, ?, ?, ?, ?)",
        (importacao_id, nome, arquivo_hash, chave, resultado, detalhe),
    )


def importar(conexao, caminho, origem: str | None = None) -> int:
    caminho = Path(caminho)
    # 1. INSERT em `importacoes`
    if origem is None:
        origem = str(caminho)
    iniciado_em = datetime.now(UTC).isoformat()
    cursor = conexao.execute(
        "INSERT INTO importacoes (origem, iniciado_em) VALUES (?, ?)", (origem, iniciado_em)
    )
    importacao_id = cursor.lastrowid

    notas = []
    eventos = []

    if caminho.suffix.lower() == ".zip":
        # 2. Abre o .zip
        with zipfile.ZipFile(caminho, "r") as arquivo_zip:
            for membro in arquivo_zip.namelist():
                if not membro.lower().endswith(".xml") or membro.endswith("/"):
                    continue
                bytes_content = arquivo_zip.read(membro)
                texto = bytes_content.decode("utf-8", errors="replace")
                if classificar_xml(texto) == "evento":
                    eventos.append((membro, bytes_content))
                else:
                    notas.append((membro, bytes_content))
    else:
        # Trata como um arquivo XML avulso
        bytes_content = caminho.read_bytes()
        texto = bytes_content.decode("utf-8", errors="replace")
        if classificar_xml(texto) == "evento":
            eventos.append((caminho.name, bytes_content))
        else:
            notas.append((caminho.name, bytes_content))

    # PRIMEIRA passada -- so a lista `notas`
    for nome, conteudo_bytes in notas:
        _processar_arquivo(conexao, importacao_id, nome, conteudo_bytes)

    # SEGUNDA passada -- so a lista `eventos`, depois de todas as notas estarem no banco
    for nome, conteudo_bytes in eventos:
        _processar_evento(conexao, importacao_id, nome, conteudo_bytes)

    # 3. UPDATE em `importacoes`
    finalizado_em = datetime.now(UTC).isoformat()
    conexao.execute(
        """
        UPDATE importacoes
        SET
            finalizado_em = ?,
            total_arquivos = (
                SELECT COUNT(*) FROM importacao_arquivos WHERE importacao_id = ?
            ),
            notas_novas = (
                SELECT COUNT(*) FROM importacao_arquivos WHERE importacao_id = ? AND resultado = 'nova'
            ),
            duplicadas = (
                SELECT COUNT(*) FROM importacao_arquivos WHERE importacao_id = ? AND resultado = 'duplicada'
            ),
            invalidas = (
                SELECT COUNT(*) FROM importacao_arquivos WHERE importacao_id = ? AND resultado = 'invalida'
            ),
            nao_suportadas = (
                SELECT COUNT(*) FROM importacao_arquivos WHERE importacao_id = ? AND resultado = 'nao_suportado_sat'
            ),
            cancelamentos_aplicados = (
                SELECT COUNT(*) FROM importacao_arquivos
                WHERE importacao_id = ? AND resultado = 'cancelamento_aplicado'
            )
        WHERE id = ?
        """,
        (
            finalizado_em,
            importacao_id,
            importacao_id,
            importacao_id,
            importacao_id,
            importacao_id,
            importacao_id,
            importacao_id,
        ),
    )

    # 4. Devolve o importacao_id
    return importacao_id

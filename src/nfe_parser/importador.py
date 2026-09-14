import hashlib
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from nfe_parser.classificador import classificar_xml
from nfe_parser.extrator import extrair_nota
from nfe_parser.persistencia import persistir_nota
from nfe_parser.cancelamento import extrair_evento, aplicar_cancelamento  # Adicionado importação


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
    else:
        resultado = "desconhecido"
        detalhe = "Classificação desconhecida"

    # INSERT em `importacao_arquivos`
    if resultado is None:
        resultado = "desconhecido"
    if resultado not in ['nova', 'duplicada', 'invalida', 'cancelamento_aplicado', 'cancelamento_orfao', 'nao_suportado_sat']:
        resultado = "invalida"
    conexao.execute(
        "INSERT INTO importacao_arquivos (importacao_id, arquivo, arquivo_hash, chave, resultado, detalhe) VALUES (?, ?, ?, ?, ?, ?)",
        (importacao_id, nome, arquivo_hash, chave, resultado, detalhe),
    )

def _processar_evento(conexao, importacao_id, nome, conteudo_bytes) -> None:
    arquivo_hash = hashlib.sha256(conteudo_bytes).hexdigest()
    texto = conteudo_bytes.decode("utf-8", errors="replace")
    try:
        evento = extrair_evento(texto)
        resultado = aplicar_cancelamento(conexao, evento)
        chave = evento.get("ch_nfe")
    except ValueError as e:
        resultado = "invalida"
        detalhe = str(e)
        chave = None

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

    membros = []
    if caminho.suffix.lower() == ".zip":
        # 2. Abre o .zip
        with zipfile.ZipFile(caminho, "r") as arquivo_zip:
            for membro in arquivo_zip.namelist():
                if not membro.lower().endswith(".xml") or membro.endswith("/"):
                    continue
                bytes_content = arquivo_zip.read(membro)
                membros.append((membro, bytes_content))
    else:
        # Trata como um arquivo XML avulso
        bytes_content = caminho.read_bytes()
        membros.append((caminho.name, bytes_content))

    # Primeira passada: persistir as notas
    for nome, conteudo_bytes in membros:
        _processar_arquivo(conexao, importacao_id, nome, conteudo_bytes)

    # Segunda passada: aplicar os eventos
    for nome, conteudo_bytes in membros:
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
            cancelamentos_aplicados = 0
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
        ),
    )

    # 4. Devolve o importacao_id
    return importacao_id

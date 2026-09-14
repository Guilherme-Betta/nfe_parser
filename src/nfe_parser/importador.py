import hashlib
import zipfile
from datetime import datetime, timezone
from pathlib import Path

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
    elif classificacao == "evento":
        resultado = "cancelamento_orfao"
    elif classificacao == "invalida":
        resultado = "invalida"
        detalhe = "Conteúdo inválido"

    # INSERT em `importacao_arquivos`
    print(f"Processing file: {nome}")  # Adicionado para debug
    conexao.execute(
        "INSERT INTO importacao_arquivos (importacao_id, arquivo, arquivo_hash, chave, resultado, detalhe) VALUES (?, ?, ?, ?, ?, ?)",
        (importacao_id, nome, arquivo_hash, chave, resultado, detalhe)
    )

def importar(conexao, caminho, origem: str | None = None) -> int:
    caminho = Path(caminho)
    # 1. INSERT em `importacoes`
    if origem is None:
        origem = str(caminho)
    iniciado_em = datetime.now(timezone.utc).isoformat()
    cursor = conexao.execute(
        "INSERT INTO importacoes (origem, iniciado_em) VALUES (?, ?)",
        (origem, iniciado_em)
    )
    importacao_id = cursor.lastrowid

    if caminho.suffix.lower() == ".zip":
        # 2. Abre o .zip
        with zipfile.ZipFile(caminho, "r") as arquivo_zip:
            for membro in arquivo_zip.namelist():
                if not membro.lower().endswith(".xml") or membro.endswith("/"):
                    continue
                bytes_content = arquivo_zip.read(membro)
                _processar_arquivo(conexao, importacao_id, membro, bytes_content)
    else:
        # Trata como um arquivo XML avulso
        bytes_content = caminho.read_bytes()
        _processar_arquivo(conexao, importacao_id, caminho.name, bytes_content)

    # 3. UPDATE em `importacoes`
    finalizado_em = datetime.now(timezone.utc).isoformat()
    conexao.execute(
        "UPDATE importacoes SET finalizado_em = ? WHERE id = ?",
        (finalizado_em, importacao_id)
    )

    # 4. Devolve o importacao_id
    return importacao_id

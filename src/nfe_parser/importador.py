import hashlib
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from nfe_parser.classificador import classificar_xml
from nfe_parser.extrator import extrair_nota
from nfe_parser.persistencia import persistir_nota

def importar(conexao, caminho, origem: str | None = None) -> int:
    # 1. INSERT em `importacoes`
    if origem is None:
        origem = str(caminho)
    iniciado_em = datetime.now(timezone.utc).isoformat()
    conexao.execute(
        "INSERT INTO importacoes (origem, iniciado_em) VALUES (?, ?)",
        (origem, iniciado_em)
    )
    importacao_id = conexao.lastrowid

    # 2. Abre o .zip
    with zipfile.ZipFile(caminho, "r") as arquivo_zip:
        for membro in arquivo_zip.namelist():
            if not membro.endswith(".xml") or membro.endswith("/"):
                continue
            bytes_content = arquivo_zip.read(membro)
            arquivo_hash = hashlib.sha256(bytes_content).hexdigest()
            texto = bytes_content.decode("utf-8", errors="replace")
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
            conexao.execute(
                "INSERT INTO importacao_arquivos (importacao_id, arquivo, arquivo_hash, chave, resultado, detalhe) VALUES (?, ?, ?, ?, ?, ?)",
                (importacao_id, membro, arquivo_hash, chave, resultado, detalhe)
            )

    # 3. UPDATE em `importacoes`
    finalizado_em = datetime.now(timezone.utc).isoformat()
    conexao.execute(
        "UPDATE importacoes SET finalizado_em = ? WHERE id = ?",
        (finalizado_em, importacao_id)
    )

    # 4. Devolve o importacao_id
    return importacao_id

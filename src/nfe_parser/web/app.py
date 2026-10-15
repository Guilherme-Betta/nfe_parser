"""O app FastAPI da spec 03: monta API, paginas e arquivos estaticos.

Subir: `uvicorn nfe_parser.web.app:criar_app_do_ambiente --factory`.

⭐ `criar_app` recebe o caminho do banco e o `llm` por parametro, em vez de ler o
ambiente: e o que deixa os testes subirem o app sobre um banco temporario e com um
LLM falso, sem rede. Quem le o ambiente e so `criar_app_do_ambiente`, a porta de
entrada de producao.

🔴 O banco e preparado DENTRO de `criar_app`, e nao num evento de startup: banco
quebrado ou configuracao errada derrubam o boot na hora, com a mensagem, em vez
de subir um app que falha na primeira requisicao.
"""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from nfe_parser import operacoes
from nfe_parser.llm import llm_do_ambiente
from nfe_parser.web import api, paginas

_PASTA = Path(__file__).parent


def criar_app(caminho_banco, llm=None):
    """O app sobre o banco em `caminho_banco`. `llm` None = LLM desligado."""
    operacoes.preparar_banco(caminho_banco)

    app = FastAPI(title="NF-e Despesas")
    app.state.caminho_banco = caminho_banco
    app.state.llm = llm
    app.mount("/static", StaticFiles(directory=_PASTA / "static"), name="static")
    app.include_router(api.roteador)
    app.include_router(paginas.roteador)
    return app


def criar_app_do_ambiente():
    """O app configurado SO por variavel de ambiente (spec 03 §2).

    ⚠️ As duas leituras vem ANTES de tocar no banco: configuracao errada falha sem
    deixar arquivo novo para tras.
    """
    caminho = os.environ.get("APP_DB_PATH")
    if not caminho:
        raise ValueError(
            "Variavel de ambiente APP_DB_PATH não definida: diga onde fica o arquivo SQLite"
        )
    return criar_app(caminho, llm=llm_do_ambiente())

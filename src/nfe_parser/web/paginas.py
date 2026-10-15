"""As paginas server-rendered da spec 03 §5 (Jinja2 + HTMX).

⭐ As paginas chamam as MESMAS funcoes que a API (`consultas`, `operacoes`), nao a
API por HTTP: e um processo so, e a requisicao a si mesmo seria so latencia.

⚠️ Filtro vazio de formulario chega como string vazia (`mes=`), e nao como
ausente. Por isso as paginas recebem texto e trocam vazio por None, em vez de
validar o formato como a API — la, um `mes` fora do padrao e 422; aqui seria uma
tela de erro por causa de um campo deixado em branco.
"""

import json
import sqlite3
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from nfe_parser import consultas, operacoes
from nfe_parser.serializacao import nota_para_json
from nfe_parser.web.comum import (
    UploadRecusado,
    decimal_br,
    importar_upload,
    obter_conexao,
    reais,
)

roteador = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
templates.env.filters["reais"] = reais
templates.env.filters["decimal_br"] = decimal_br

Conexao = Annotated[sqlite3.Connection, Depends(obter_conexao)]


def _tela(request, nome, contexto=None, status=200):
    return templates.TemplateResponse(request, nome, contexto or {}, status_code=status)


def _nao_encontrado(request, mensagem):
    return _tela(request, "erro.html", {"mensagem": mensagem}, status=404)


def _vazio_e_none(valor):
    return valor or None


def _opcoes_de_categoria(conexao):
    """A arvore achatada para um `<select>`: `(slug, rotulo)`. ⛔ Sem o bucket:
    classificar A MAO no bucket protegeria o produto la dentro, fora da fila."""
    opcoes = []
    for raiz in consultas.arvore_categorias(conexao):
        if raiz["is_bucket"]:
            continue
        opcoes.append((raiz["slug"], raiz["nome"]))
        opcoes.extend(
            (filha["slug"], f"{raiz['nome']} › {filha['nome']}") for filha in raiz["filhas"]
        )
    return opcoes


# --- importacao -----------------------------------------------------------------


def _inicio(request, conexao, erro=None, status=200):
    contexto = {"importacoes": consultas.listar_importacoes(conexao, limite=10), "erro": erro}
    return _tela(request, "inicio.html", contexto, status)


@roteador.get("/")
def inicio(request: Request, conexao: Conexao):
    return _inicio(request, conexao)


@roteador.post("/importar")
def importar(request: Request, arquivo: UploadFile, conexao: Conexao):
    try:
        importacao_id = importar_upload(conexao, arquivo)
    except UploadRecusado as e:
        return _inicio(request, conexao, erro=str(e), status=400)
    return RedirectResponse(f"/importacoes/{importacao_id}", status_code=303)


@roteador.get("/importacoes/{importacao_id}")
def ver_importacao(request: Request, importacao_id: int, conexao: Conexao):
    dados = consultas.importacao(conexao, importacao_id)
    if dados is None:
        return _nao_encontrado(request, f"Não existe a importação {importacao_id}.")
    return _tela(request, "importacao.html", {"imp": dados})


# --- notas ----------------------------------------------------------------------


@roteador.get("/notas")
def notas(
    request: Request,
    conexao: Conexao,
    mes: str | None = None,
    loja_cnpj: str | None = None,
    status: str | None = None,
    pagina: int = 1,
):
    filtros = {
        "mes": _vazio_e_none(mes),
        "loja_cnpj": _vazio_e_none(loja_cnpj),
        "status": _vazio_e_none(status),
    }
    pagina = max(pagina, 1)
    dados = consultas.listar_notas(conexao, **filtros, pagina=pagina, por_pagina=50)
    return _tela(request, "notas.html", {"dados": dados, "filtros": filtros})


@roteador.get("/notas/{chave}")
def ver_nota(request: Request, chave: str, conexao: Conexao):
    texto = nota_para_json(conexao, chave)
    if texto is None:
        return _nao_encontrado(request, f"Não existe nota com a chave {chave}.")
    contexto = {
        "nota": json.loads(texto),
        "aproximados": consultas.itens_aproximados(conexao, chave),
    }
    return _tela(request, "nota.html", contexto)


# --- revisao --------------------------------------------------------------------


@roteador.get("/revisar")
def revisar(request: Request, conexao: Conexao, todos: bool = False, pagina: int = 1):
    pagina = max(pagina, 1)
    dados = consultas.listar_produtos(
        conexao, classificado=None if todos else False, pagina=pagina, por_pagina=50
    )
    contexto = {
        "dados": dados,
        "todos": todos,
        "opcoes": _opcoes_de_categoria(conexao),
        "llm_ativo": request.app.state.llm is not None,
    }
    return _tela(request, "revisar.html", contexto)


@roteador.post("/revisar/llm")
def revisar_com_llm(request: Request, conexao: Conexao):
    llm = request.app.state.llm
    if llm is not None:
        operacoes.classificar_com_llm(conexao, llm)
    return RedirectResponse("/revisar", status_code=303)


@roteador.post("/revisar/{produto_id}")
def classificar(
    request: Request,
    produto_id: int,
    categoria_slug: Annotated[str, Form()],
    conexao: Conexao,
):
    """Com HTMX (`HX-Request`), devolve SO a linha atualizada; sem, redireciona."""
    try:
        operacoes.classificar_manual(conexao, produto_id, categoria_slug)
    except LookupError as e:
        return _nao_encontrado(request, str(e))

    if request.headers.get("HX-Request") != "true":
        return RedirectResponse("/revisar", status_code=303)
    contexto = {
        "p": consultas.produto(conexao, produto_id),
        "opcoes": _opcoes_de_categoria(conexao),
        "salvo": True,
    }
    return _tela(request, "_linha_produto.html", contexto)


# --- taxonomia ------------------------------------------------------------------


def _taxonomia(request, conexao, erro=None, status=200):
    arvore = consultas.arvore_categorias(conexao)
    niveis_1 = [(raiz["slug"], raiz["nome"]) for raiz in arvore if not raiz["is_bucket"]]
    contexto = {"arvore": arvore, "niveis_1": niveis_1, "erro": erro}
    return _tela(request, "taxonomia.html", contexto, status)


def _editar_taxonomia(request, conexao, acao):
    """Roda `acao`; sucesso redireciona, recusa do nucleo volta a tela com a mensagem."""
    try:
        acao()
    except LookupError as e:
        return _taxonomia(request, conexao, erro=str(e), status=404)
    except ValueError as e:
        return _taxonomia(request, conexao, erro=str(e), status=400)
    return RedirectResponse("/taxonomia", status_code=303)


@roteador.get("/taxonomia")
def taxonomia(request: Request, conexao: Conexao):
    return _taxonomia(request, conexao)


@roteador.post("/taxonomia")
def criar_categoria(
    request: Request,
    conexao: Conexao,
    nome: Annotated[str, Form()] = "",
    parent_slug: Annotated[str, Form()] = "",
):
    return _editar_taxonomia(
        request,
        conexao,
        lambda: operacoes.criar_categoria(conexao, nome, _vazio_e_none(parent_slug)),
    )


@roteador.post("/taxonomia/{slug}/renomear")
def renomear_categoria(
    request: Request, slug: str, conexao: Conexao, nome: Annotated[str, Form()] = ""
):
    return _editar_taxonomia(
        request, conexao, lambda: operacoes.editar_categoria(conexao, slug, nome=nome)
    )


@roteador.post("/taxonomia/{slug}/mover")
def mover_categoria(
    request: Request, slug: str, conexao: Conexao, parent_slug: Annotated[str, Form()] = ""
):
    return _editar_taxonomia(
        request,
        conexao,
        lambda: operacoes.editar_categoria(conexao, slug, parent_slug=_vazio_e_none(parent_slug)),
    )


@roteador.post("/taxonomia/{slug}/apagar")
def apagar_categoria(request: Request, slug: str, conexao: Conexao):
    return _editar_taxonomia(request, conexao, lambda: operacoes.apagar_categoria(conexao, slug))

"""A API JSON da spec 03 §4. So HTTP: a logica e dos nucleos, a transacao de `operacoes`."""

import sqlite3
from contextlib import contextmanager
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, UploadFile
from pydantic import BaseModel

from nfe_parser import consultas, operacoes
from nfe_parser.migracoes import versao_do_banco
from nfe_parser.serializacao import nota_para_json
from nfe_parser.web.comum import UploadRecusado, importar_upload, obter_conexao

roteador = APIRouter(prefix="/api")

Conexao = Annotated[sqlite3.Connection, Depends(obter_conexao)]
Pagina = Annotated[int, Query(ge=1)]
PorPagina = Annotated[int, Query(ge=1, le=200)]


@contextmanager
def erros_do_nucleo():
    """Traduz as excecoes dos nucleos em status HTTP: `LookupError` → 404, `ValueError` → 400.

    ⚠️ Envolve SO a chamada ao nucleo, nunca o endpoint inteiro: um `ValueError`
    de defeito em outro lugar viraria um 400 com cara de "voce pediu errado", e o
    500 honesto sumiria.
    """
    try:
        yield
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


class CategoriaManual(BaseModel):
    categoria_slug: str


class NovaCategoria(BaseModel):
    nome: str
    parent_slug: str | None = None


class EdicaoCategoria(BaseModel):
    nome: str | None = None
    parent_slug: str | None = None


@roteador.post("/importacoes", status_code=201)
def criar_importacao(arquivo: UploadFile, conexao: Conexao):
    try:
        importacao_id = importar_upload(conexao, arquivo)
    except UploadRecusado as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    dados = consultas.importacao(conexao, importacao_id)
    return {
        "importacao_id": importacao_id,
        "contadores": dados["contadores"],
        "classificacao": dados["classificacao"],
    }


@roteador.get("/importacoes")
def listar_importacoes(conexao: Conexao):
    return consultas.listar_importacoes(conexao)


@roteador.get("/importacoes/{importacao_id}")
def ver_importacao(importacao_id: int, conexao: Conexao):
    dados = consultas.importacao(conexao, importacao_id)
    if dados is None:
        raise HTTPException(status_code=404, detail=f"nao existe importacao {importacao_id}")
    return dados


@roteador.get("/notas")
def listar_notas(
    conexao: Conexao,
    mes: Annotated[str | None, Query(pattern=r"^\d{4}-\d{2}$")] = None,
    loja_cnpj: str | None = None,
    status: Literal["ok", "cancelada"] | None = None,
    pagina: Pagina = 1,
    por_pagina: PorPagina = 50,
):
    return consultas.listar_notas(conexao, mes, loja_cnpj, status, pagina, por_pagina)


@roteador.get("/notas/{chave}")
def ver_nota(chave: str, conexao: Conexao):
    """⭐ Devolve a string de `nota_para_json` como esta: reconverter para dict e
    deixar o FastAPI serializar de novo so arriscaria mudar o formato."""
    texto = nota_para_json(conexao, chave)
    if texto is None:
        raise HTTPException(status_code=404, detail=f"nao existe nota com chave {chave}")
    return Response(content=texto, media_type="application/json")


@roteador.get("/produtos")
def listar_produtos(
    conexao: Conexao,
    classificado: bool | None = None,
    origem: Literal["manual", "memoria", "ncm", "llm"] | None = None,
    pagina: Pagina = 1,
    por_pagina: PorPagina = 50,
):
    return consultas.listar_produtos(conexao, classificado, origem, pagina, por_pagina)


@roteador.post("/produtos/{produto_id}/categoria")
def classificar_produto(produto_id: int, corpo: CategoriaManual, conexao: Conexao):
    with erros_do_nucleo():
        operacoes.classificar_manual(conexao, produto_id, corpo.categoria_slug)
    return consultas.produto(conexao, produto_id)


@roteador.get("/categorias")
def arvore(conexao: Conexao):
    return consultas.arvore_categorias(conexao)


@roteador.post("/categorias", status_code=201)
def criar_categoria(corpo: NovaCategoria, conexao: Conexao):
    with erros_do_nucleo():
        slug = operacoes.criar_categoria(conexao, corpo.nome, corpo.parent_slug)
    return consultas.categoria(conexao, slug)


@roteador.patch("/categorias/{slug}")
def editar_categoria(slug: str, corpo: EdicaoCategoria, conexao: Conexao):
    """🔴 `model_fields_set` separa "nao mandou o campo" de "mandou null". Em
    `parent_slug` a diferenca e tudo: ausente = nao mover; `null` = subir para o
    nivel 1."""
    enviados = corpo.model_fields_set
    with erros_do_nucleo():
        operacoes.editar_categoria(
            conexao,
            slug,
            nome=corpo.nome if "nome" in enviados else operacoes.NAO_MUDA,
            parent_slug=corpo.parent_slug if "parent_slug" in enviados else operacoes.NAO_MUDA,
        )
    dados = consultas.categoria(conexao, slug)
    if dados is None:
        raise HTTPException(status_code=404, detail=f"nao existe categoria com slug {slug!r}")
    return dados


@roteador.delete("/categorias/{slug}", status_code=204)
def apagar_categoria(slug: str, conexao: Conexao):
    with erros_do_nucleo():
        operacoes.apagar_categoria(conexao, slug)
    return Response(status_code=204)


@roteador.post("/llm/classificar")
def classificar_com_llm(request: Request, conexao: Conexao):
    llm = request.app.state.llm
    if llm is None:
        raise HTTPException(
            status_code=409,
            detail="LLM desligado: defina OLLAMA_URL, OLLAMA_MODELO e LLM_LIMIAR",
        )
    return {"classificados": operacoes.classificar_com_llm(conexao, llm)}


@roteador.get("/health")
def saude(request: Request, conexao: Conexao):
    return {
        "status": "ok",
        "schema_version": versao_do_banco(conexao),
        "llm_ativo": request.app.state.llm is not None,
        "contagens": consultas.contagens(conexao),
    }

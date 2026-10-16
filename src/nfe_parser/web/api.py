"""A API JSON da spec 03 §4. So HTTP: a logica e dos nucleos, a transacao de `operacoes`."""

import sqlite3
from contextlib import contextmanager
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, UploadFile
from pydantic import BaseModel

from nfe_parser import consultas, operacoes, orcamento, relatorios
from nfe_parser.migracoes import versao_do_banco
from nfe_parser.serializacao import nota_para_json
from nfe_parser.web.comum import UploadRecusado, importar_upload, obter_conexao

roteador = APIRouter(prefix="/api")

Conexao = Annotated[sqlite3.Connection, Depends(obter_conexao)]
Pagina = Annotated[int, Query(ge=1)]
PorPagina = Annotated[int, Query(ge=1, le=200)]
MES = r"^\d{4}-(0[1-9]|1[0-2])$"


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
    mes: Annotated[str | None, Query(pattern=MES)] = None,
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


class NovoOrcamento(BaseModel):
    categoria_slug: str
    mes: str
    limite: int


class AlteracaoDeLimite(BaseModel):
    limite: int


@roteador.get("/orcamentos")
def orcamentos_do_mes(conexao: Conexao, mes: Annotated[str, Query(pattern=MES)]):
    return orcamento.orcamentos_do_mes(conexao, mes)


@roteador.post("/orcamentos", status_code=201)
def criar_orcamento(corpo: NovoOrcamento, conexao: Conexao):
    with erros_do_nucleo():
        orcamento_id = operacoes.definir_orcamento(
            conexao, corpo.categoria_slug, corpo.mes, corpo.limite
        )
    return orcamento.orcamento(conexao, orcamento_id)


@roteador.patch("/orcamentos/{orcamento_id}")
def alterar_orcamento(orcamento_id: int, corpo: AlteracaoDeLimite, conexao: Conexao):
    with erros_do_nucleo():
        operacoes.alterar_limite(conexao, orcamento_id, corpo.limite)
    return orcamento.orcamento(conexao, orcamento_id)


@roteador.delete("/orcamentos/{orcamento_id}", status_code=204)
def apagar_orcamento(orcamento_id: int, conexao: Conexao):
    with erros_do_nucleo():
        operacoes.apagar_orcamento(conexao, orcamento_id)
    return Response(status_code=204)


def _filtros_comuns(
    de: Annotated[str | None, Query(pattern=MES)] = None,
    ate: Annotated[str | None, Query(pattern=MES)] = None,
    categoria_slug: str | None = None,
    loja_cnpj: str | None = None,
):
    return {"de": de, "ate": ate, "categoria_slug": categoria_slug, "loja_cnpj": loja_cnpj}


def _filtros(comuns: Annotated[dict, Depends(_filtros_comuns)], produto_id: int | None = None):
    """Os filtros da spec 05 §3, validados pelo FastAPI. O `preco-no-tempo` usa so
    os comuns: la, `produto_id` e obrigatorio e vem como parametro proprio."""
    return {**comuns, "produto_id": produto_id}


Filtros = Annotated[dict, Depends(_filtros)]
FiltrosComuns = Annotated[dict, Depends(_filtros_comuns)]


@roteador.get("/relatorios/gasto-mensal")
def gasto_mensal(conexao: Conexao, filtros: Filtros):
    with erros_do_nucleo():
        return relatorios.gasto_mensal(conexao, **filtros)


@roteador.get("/relatorios/gasto-categoria")
def gasto_categoria(conexao: Conexao, filtros: Filtros):
    with erros_do_nucleo():
        return relatorios.gasto_categoria(conexao, **filtros)


@roteador.get("/relatorios/gasto-loja")
def gasto_loja(conexao: Conexao, filtros: Filtros):
    with erros_do_nucleo():
        return relatorios.gasto_loja(conexao, **filtros)


@roteador.get("/relatorios/top-produtos")
def top_produtos(
    conexao: Conexao,
    filtros: Filtros,
    limite: Annotated[int, Query(ge=1, le=100)] = 20,
    ordenar: Literal["valor", "quantidade"] = "valor",
):
    with erros_do_nucleo():
        return relatorios.top_produtos(conexao, limite, ordenar, **filtros)


@roteador.get("/relatorios/preco-no-tempo")
def preco_no_tempo(conexao: Conexao, produto_id: int, filtros: FiltrosComuns):
    with erros_do_nucleo():
        return relatorios.preco_no_tempo(conexao, produto_id, **filtros)


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

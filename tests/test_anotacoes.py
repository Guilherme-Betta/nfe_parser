"""Testes de anotacao de tipo — tarefa 3 da story 003.

Escritos ANTES da implementacao (passo 2 do loop) e congelados por commit. O
modelo local recebe este arquivo como LEITURA (`--read`), nunca como arquivo
editavel.

Criterio C4 de `specs/003-nfce-65-multi-item/spec.md` §3, assercoes 4.1 a 4.4.

POR QUE ESTE MODULO EXISTE
--------------------------
Ele testa uma hipotese sobre o PROJETO, nao sobre a NF-e: *o tipo de retorno de
`para_centavos` foi errado duas vezes seguidas porque o codigo nao declara o que
devolve.* Se a rubrica da story 003 mostrar que o erro nao se repetiu, a
hipotese ganha um ponto; se ele se repetir mesmo com a anotacao no codigo, a
culpa nao era do codigo. Os dois desfechos sao resultado.

POR QUE POR INTROSPECAO, E NAO POR LISTA FIXA
---------------------------------------------
Uma lista fixa de funcoes envelhece: a funcao publica numero tres nasceria sem
cobertura e ninguem perceberia. Descobrindo o modulo em tempo de execucao, toda
funcao publica nova ja nasce coberta, sem ninguem precisar editar este arquivo.
"""

import inspect
import typing
from pathlib import Path

import pytest

from nfe_parser import extrator

FIXTURE = Path(__file__).parent / "fixtures" / "nfe_55_1item.xml"

# Uma entrada VALIDA por funcao publica, para a assercao 4.3 poder chamar cada
# uma e comparar o que ela devolve com o que ela declara. Funcao publica nova
# sem entrada aqui faz o teste 4.3 falhar com uma mensagem que diz o que fazer —
# preferivel a ela ser pulada em silencio.
ENTRADAS_VALIDAS = {
    "para_centavos": ("8.04",),
    "extrair_nota": (FIXTURE.read_text(encoding="utf-8"),),
}


def funcoes_publicas():
    """Funcoes DEFINIDAS neste modulo cujo nome nao comeca com `_`.

    O filtro por `__module__` e o que importa: sem ele, qualquer funcao
    importada no topo do `extrator.py` entraria na lista e o teste passaria a
    cobrar anotacao de codigo de terceiros.
    """
    return sorted(
        (
            nome
            for nome, obj in inspect.getmembers(extrator, inspect.isfunction)
            if not nome.startswith("_") and obj.__module__ == extrator.__name__
        )
    )


NOMES = funcoes_publicas()


def test_4_0_o_modulo_expoe_as_funcoes_publicas_conhecidas():
    """Guarda-corpo dos testes parametrizados abaixo.

    Se `funcoes_publicas()` devolvesse lista vazia — por um erro no filtro, ou
    porque alguem renomeou tudo para `_privado` — os testes parametrizados nao
    coletariam caso nenhum e a suite ficaria VERDE sem ter verificado nada. Esse
    e o pior modo de falha possivel num oraculo.
    """
    assert "para_centavos" in NOMES
    assert "extrair_nota" in NOMES


# --- C4.1 --------------------------------------------------------------------


@pytest.mark.parametrize("nome", NOMES)
def test_4_1_toda_funcao_publica_anota_o_retorno(nome):
    funcao = getattr(extrator, nome)
    anotacao = inspect.signature(funcao).return_annotation
    assert anotacao is not inspect.Signature.empty, (
        f"A funcao publica '{nome}' nao declara o tipo de retorno. "
        "Adicione a anotacao `-> tipo` na assinatura."
    )


# --- C4.2 --------------------------------------------------------------------


def _tipo_de_retorno(nome):
    funcao = getattr(extrator, nome)
    dicas = typing.get_type_hints(funcao)
    assert "return" in dicas, f"'{nome}' nao declara tipo de retorno (ver 4.1)"
    anotado = dicas["return"]
    # `get_origin` desembrulha `dict[str, Any]` em `dict`. Isso e proposital:
    # uma anotacao MAIS precisa que `dict` e melhor, e nao pode ser reprovada
    # por este teste. `get_origin` devolve None para tipos simples como `int`.
    return typing.get_origin(anotado) or anotado


def test_4_2_para_centavos_declara_int():
    assert _tipo_de_retorno("para_centavos") is int


def test_4_2_extrair_nota_declara_dict():
    assert _tipo_de_retorno("extrair_nota") is dict


# --- C4.3 --------------------------------------------------------------------


@pytest.mark.parametrize("nome", NOMES)
def test_4_3_a_anotacao_bate_com_o_retorno_real(nome):
    """Sozinha, a 4.1 passaria com uma anotacao ERRADA.

    E uma anotacao errada e pior que anotacao nenhuma: ela mente com autoridade,
    e quem le a assinatura para de desconfiar. Esta assercao chama a funcao de
    verdade e compara o tipo do que voltou com o tipo declarado.
    """
    assert nome in ENTRADAS_VALIDAS, (
        f"Funcao publica '{nome}' sem entrada valida em ENTRADAS_VALIDAS. "
        "Registre uma, senao ela fica sem esta cobertura."
    )
    esperado = _tipo_de_retorno(nome)
    retorno = getattr(extrator, nome)(*ENTRADAS_VALIDAS[nome])
    assert isinstance(retorno, esperado), (
        f"'{nome}' declara {esperado.__name__} e devolveu {type(retorno).__name__}."
    )


# --- C4.4 --------------------------------------------------------------------


@pytest.mark.parametrize("nome", NOMES)
def test_4_4_os_parametros_tambem_sao_anotados(nome):
    """Nao e o criterio pre-registrado, que fala do retorno.

    Entra porque uma assinatura meio anotada confunde mais que uma crua — quem
    le assume que o parametro sem anotacao e intencionalmente generico — e custa
    os mesmos caracteres.
    """
    assinatura = inspect.signature(getattr(extrator, nome))
    sem_anotacao = [
        p.name for p in assinatura.parameters.values() if p.annotation is inspect.Parameter.empty
    ]
    assert not sem_anotacao, f"Parametros sem anotacao em '{nome}': {', '.join(sem_anotacao)}"

"""O aviso de "apagar" diz para ONDE os produtos vao — spec 03 §5 e C12.

Subcategoria: para a categoria-mae (decisao do Gui de 2026-10-16). Nivel 1: para
Nao Classificado, como antes.
"""

import pytest


def _form_de_apagar(html, slug):
    marca = f'action="/taxonomia/{slug}/apagar"'
    assert marca in html, f"nao ha botao de apagar para {slug}"
    return html.split(marca, 1)[1].split("</form>", 1)[0]


@pytest.mark.parametrize(
    ("slug", "destino"),
    [("mercado-mercearia", "Mercado"), ("vestuario", "Não Classificado")],
    ids=["subcategoria", "nivel-1"],
)
def test_aviso_de_apagar_diz_para_onde_vao_os_produtos(cliente, slug, destino):
    form = _form_de_apagar(cliente.get("/taxonomia").text, slug)

    assert f'data-destino="{destino}"' in form
    assert f"iriam para {destino}" in form

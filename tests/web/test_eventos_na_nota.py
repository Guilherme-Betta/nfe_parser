"""A carta de correcao aparece na nota — spec 03 §4/§5 e C17.

Decisao do Gui de 2026-10-16 (rodada 02): guardar so serve se der para ver.
"""

from tests.apoio import CHAVE_1ITEM, carta_de_correcao, chave, enviar, texto, zip_de

CORRECAO = "Onde se le Rua A, 10, leia-se Rua A, 100."


def _lote_com_carta(cliente, *cartas):
    membros = {"nota.xml": texto("nfe_55_1item.xml")}
    for n, carta in enumerate(cartas, start=1):
        membros[f"cce{n}.xml"] = carta
    resposta = enviar(cliente, "lote.zip", zip_de(membros))
    assert resposta.status_code == 201
    return resposta.json()["importacao_id"]


def test_tela_da_nota_mostra_a_data_e_o_texto_da_correcao(cliente):
    _lote_com_carta(cliente, carta_de_correcao(CHAVE_1ITEM, CORRECAO))

    html = cliente.get(f"/notas/{CHAVE_1ITEM}").text

    assert "Carta de correção" in html
    assert CORRECAO in html
    assert "2026-07-02" in html


def test_com_mais_de_uma_carta_avisa_que_a_mais_recente_vale(cliente):
    _lote_com_carta(
        cliente,
        carta_de_correcao(CHAVE_1ITEM, "primeira", n_seq=1),
        carta_de_correcao(CHAVE_1ITEM, "segunda", n_seq=2, dh_evento="2026-07-03T09:00:00-03:00"),
    )

    html = cliente.get(f"/notas/{CHAVE_1ITEM}").text

    assert "primeira" in html and "segunda" in html
    assert "a mais recente substitui as anteriores" in html


def test_nota_sem_evento_nao_mostra_o_bloco(cliente):
    enviar(cliente, "nota.xml", texto("nfe_55_1item.xml"))

    assert "Carta de correção" not in cliente.get(f"/notas/{CHAVE_1ITEM}").text


def test_api_de_eventos_da_nota(cliente):
    _lote_com_carta(cliente, carta_de_correcao(CHAVE_1ITEM, CORRECAO))

    corpo = cliente.get(f"/api/notas/{CHAVE_1ITEM}/eventos").json()

    assert corpo == [
        {
            "tp_evento": "110110",
            "n_seq": 1,
            "dh_evento": "2026-07-02T09:00:00-03:00",
            "descricao": "Carta de Correcao",
            "correcao": CORRECAO,
        }
    ]
    assert cliente.get(f"/api/notas/{chave(999)}/eventos").status_code == 404


def test_tela_da_importacao_mostra_evento_registrado(cliente):
    importacao_id = _lote_com_carta(cliente, carta_de_correcao(CHAVE_1ITEM, CORRECAO))

    html = cliente.get(f"/importacoes/{importacao_id}").text

    assert "evento registrado" in html
    assert "cancelamento órfão" not in html
    assert "inválida" not in html.split("<h2>Arquivos</h2>", 1)[1]

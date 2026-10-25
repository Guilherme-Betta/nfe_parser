"""Lista de notas no celular — spec 03 §5 e C13: a situacao nao pode depender de rolagem.

Testes de HTML, nao de layout: conferem que a estrutura e as classes que o CSS usa
estao no lugar. Olhar a tela de verdade continua sendo passo manual (CLAUDE.md, passo 4).
"""

import re

from tests.apoio import chave, enviar, evento, texto, variante


def _linhas(html):
    tabela = re.search(r"<table>(.*?)</table>", html, re.DOTALL).group(1)
    return re.findall(r"<tr>(.*?)</tr>", tabela, re.DOTALL)


def test_situacao_aparece_sob_a_data_e_as_colunas_largas_sao_marcadas(cliente):
    cancelada = variante("nfe_55_1item.xml", chave(1))
    for nome, xml in (("a.xml", texto("nfe_65_1item.xml")), ("b.xml", cancelada)):
        assert enviar(cliente, nome, xml).status_code == 201
    assert enviar(cliente, "c.xml", evento(chave(1))).status_code == 201

    html = cliente.get("/notas").text
    cabecalho, *linhas = _linhas(html)

    assert '<th class="so-largo">Modelo</th>' in cabecalho
    assert '<th class="so-largo">Situação</th>' in cabecalho
    assert len(linhas) == 2
    for linha in linhas:
        primeira_celula = re.search(r'<td class="data">(.*?)</td>', linha, re.DOTALL).group(1)
        selos = re.findall(r'<span class="selo (ok|ruim)">', primeira_celula)
        assert selos, "a 1a celula (data) nao traz a situacao para a tela estreita"
        assert '<div class="so-estreito">' in primeira_celula
        assert re.search(r'<td class="so-largo"><span class="selo (ok|ruim)">', linha)
    assert sum("selo ruim" in l for l in linhas) == 1


def test_css_esconde_as_colunas_largas_so_em_tela_estreita(cliente):
    css = re.search(r"<style>(.*?)</style>", cliente.get("/notas").text, re.DOTALL).group(1)
    estreita = re.search(r"@media \(max-width: 480px\) \{(.*?)\n\s*\}", css, re.DOTALL)

    assert estreita, "falta a regra de tela estreita"
    assert re.search(r"\.so-largo \{[^}]*display: none", estreita.group(1))
    assert re.search(r"\.so-estreito \{[^}]*display: none", css.replace(estreita.group(0), ""))

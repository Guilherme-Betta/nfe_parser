#!/usr/bin/env python
"""
verify.py -- O ORACULO do projeto. Nome fixo; o kit sempre chama isto.

===========================================================================
 O QUE ESTE ARQUIVO E, E POR QUE ELE E O ARQUIVO MAIS IMPORTANTE DO KIT
===========================================================================

O modelo local nao para de mexer no codigo ate este script sair com codigo 0.
E o diff dele e aceito PORQUE este script passou. Ou seja: este arquivo e o
juiz de toda a arquitetura.

Consequencia direta: um juiz que o dono do projeto nao consegue ler e um juiz
em quem ele esta confiando cegamente. Por isso este arquivo e Python simples e
comentado, e nao um script esperto -- voce PRECISA conseguir auditar o proprio
oraculo. (E por isso tambem que e Python e nao PowerShell: roda igual em
qualquer shell, e o Gui le Python.)

  ⚠️ INVARIANTE 2 DO KIT: o bootstrap NAO TERMINA sem um `verify` que passa
  num checkout limpo. Um oraculo quebrado no inicio faz TODO diff parecer
  quebrado -- e a culpa cai injustamente no modelo local.

---------------------------------------------------------------------------
 O CONTRATO (a unica coisa que o kit exige)
---------------------------------------------------------------------------
  * o arquivo se chama `scripts/verify.py`;
  * roda com `python scripts/verify.py`, a partir da RAIZ do projeto;
  * sai com codigo 0 se esta tudo bem, e diferente de 0 se nao esta.

Nada mais. O QUE ele verifica e decisao de cada projeto -- por isso a lista
COMANDOS abaixo e o "miolo" que voce preenche no bootstrap.

---------------------------------------------------------------------------
 EXEMPLOS DE MIOLO, por tipo de projeto
---------------------------------------------------------------------------
  Tem testes        ->  [PY, "-m", "pytest", "-q"]      (PY = sys.executable)
  Sem testes        ->  importar os modulos + lint + rodar o caminho feliz
  Notebook          ->  ["jupyter", "nbconvert", "--execute", "notebooks/x.ipynb"]
  Script de dados   ->  rodar contra input fixo e comparar com output de referencia

Registre em `steering/verificacao.md` O QUE este verify checa NESTE projeto
e POR QUE -- e la que a decisao fica explicada para a proxima sessao.
"""

import subprocess
import sys

# ===========================================================================
#  ▼▼▼ O MIOLO -- E ISTO QUE VOCE EDITA POR PROJETO ▼▼▼
# ===========================================================================
# Cada item e um comando. Rodam em ordem; o primeiro que falhar aborta o resto.
# Cada comando e uma LISTA de strings, nao uma string unica: assim nao existe
# shell no meio, e argumento com espaco nao vira dois argumentos.
#
# ⚠️ USE `PY` (= sys.executable), NUNCA a string "python". `sys.executable` e o
# MESMO interpretador que esta rodando este script; a string "python" seria
# resolvida pelo PATH -- que, com a venv nao ativada, e o Python global da
# maquina. O sintoma e cruel: o oraculo reprova tudo por "No module named
# pytest" e a culpa parece ser do modelo local.
#
# Se o pytest nao estiver instalado NAQUELE interpretador, o comando falha ALTO
# em vez de passar despercebido -- que e exatamente o que um oraculo deve fazer.
#
# A ORDEM importa quando ha mais de um comando: o verify aborta no primeiro que
# falhar. Ponha os testes ANTES do lint, para gastar as 3 reflexoes do Aider em
# CORRETUDE antes de estilo. O inverso faz uma virgula fora do lugar bloquear o
# modelo de sequer ver o resultado dos testes.

PY = sys.executable

# ---------------------------------------------------------------------------
# NESTE PROJETO (nfe_parser): SO pytest. O ruff saiu do oraculo em 2026-09-08,
# depois de a story 001 ser reprovada por uma linha em branco.
#
# O que aconteceu, medido: o modelo local acertou a implementacao no PRIMEIRO
# turno (8 testes verdes). O ruff entao reprovou com I001 -- formatacao do bloco
# de import -- e o modelo gastou as TRES reflexoes tentando consertar, emitindo
# blocos SEARCH/REPLACE com o texto IDENTICO dos dois lados. Nao e teimosia: uma
# mudanca so de espaco em branco e praticamente inexprimivel no formato `diff`,
# porque SEARCH e REPLACE ficam visualmente iguais.
#
# A licao NAO e "ponha o lint depois dos testes" -- estava depois. Quando os
# testes passam de primeira, o lint herda o orcamento inteiro de reflexoes. A
# licao e: o oraculo do modelo local julga CORRETUDE. Estilo e do passo 4, onde
# um `ruff check --fix` resolve em um segundo.
#
# O buraco (codigo que passa aqui e reprova no CI) esta registrado em
# steering/verificacao.md, e quem o fecha e a revisao do passo 4.
# ---------------------------------------------------------------------------
COMANDOS = [
    [PY, "-m", "pytest", "-q"],
]

# Exemplo de projeto SEM testes (descomente e adapte):
# COMANDOS = [
#     [PY, "-c", "import meu_pacote"],          # importa: pega erro de sintaxe
#     [PY, "-m", "ruff", "check", "."],          # lint
#     [PY, "-m", "meu_pacote.cli", "--exemplo"], # caminho feliz de verdade
# ]

# ===========================================================================
#  ▲▲▲ FIM DO MIOLO -- daqui para baixo nao precisa mexer ▲▲▲
# ===========================================================================


def main():
    if not COMANDOS:
        # Um verify que nao verifica nada aprovaria qualquer coisa. Falha alto
        # em vez de dar um verde falso -- o modo de falha mais perigoso aqui e
        # o silencioso.
        print("verify: ERRO -- a lista COMANDOS esta vazia.", file=sys.stderr)
        print("        Um oraculo que nao verifica nada aprova qualquer diff.", file=sys.stderr)
        return 1

    for numero, comando in enumerate(COMANDOS, start=1):
        # flush=True e obrigatorio, nao enfeite: sem ele o print do Python fica no
        # buffer enquanto o subprocesso escreve DIRETO no terminal, e o cabecalho do
        # passo aparece DEPOIS da saida dele. Num log do Aider isso embaralha a leitura
        # justamente quando voce esta tentando descobrir qual passo falhou.
        print(f"verify [{numero}/{len(COMANDOS)}]: {' '.join(comando)}", flush=True)

        try:
            # check=False e proposital e explicito: quem decide o que fazer com um
            # codigo de saida != 0 e o loop abaixo, nao uma excecao do subprocess.
            resultado = subprocess.run(comando, check=False)
        except FileNotFoundError:
            # O executavel nem existe (ex.: "jupyter" nao instalado).
            print(f"verify: FALHOU -- comando nao encontrado: {comando[0]}", file=sys.stderr)
            return 1

        if resultado.returncode != 0:
            print(f"verify: FALHOU no passo {numero} (codigo {resultado.returncode})",
                  file=sys.stderr)
            return 1

    print(f"verify: OK -- {len(COMANDOS)} passo(s), tudo verde.")
    return 0


if __name__ == "__main__":
    # sys.exit() com o codigo de retorno: e ISTO que o Aider le para decidir
    # se continua iterando ou se pode parar.
    sys.exit(main())

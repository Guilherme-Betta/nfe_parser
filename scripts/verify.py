"""
verify.py -- confere que o projeto esta pronto para commit.

    python scripts/verify.py      (a partir da RAIZ do projeto)

Roda, em ordem, o que o CI roda (`pytest` e `ruff check`) e mais a checagem do
`ruff format`, que o projeto adotou mas o CI nao cobra. Sai com codigo 0 se
tudo passou, e diferente de 0 no PRIMEIRO comando que falhar.

Por que existe, se o CI ja roda isso: para "verde aqui" querer dizer "verde no
CI" ANTES do push. O que este script NAO consegue pegar -- e por que -- esta em
`steering/verificacao.md`.

Este arquivo e Python simples e comentado de proposito: ele e o juiz de "esta
pronto", e um juiz que o dono do projeto nao consegue ler e um juiz em quem ele
esta confiando cegamente.
"""

import subprocess
import sys

# ⚠️ USE `PY` (= sys.executable), NUNCA a string "python". `sys.executable` e o
# MESMO interpretador que esta rodando este script; a string "python" seria
# resolvida pelo PATH -- que, com a venv nao ativada, e o Python global da
# maquina, sem pytest nem ruff. O sintoma seria cruel: tudo reprovado por
# "No module named pytest", com o codigo inocente.
PY = sys.executable

# Cada comando e uma LISTA de strings, nao uma string unica: assim nao existe
# shell no meio, e argumento com espaco nao vira dois argumentos.
COMANDOS = [
    [PY, "-m", "pytest", "-q"],
    # `--no-cache` nao e opcional: o cache do ruff ja deu verde aqui e vermelho
    # no CI com o arquivo identico. Ver steering/verificacao.md.
    [PY, "-m", "ruff", "check", "--no-cache", "."],
    # So o codigo. Os blocos de Python dentro das specs antigas nao seguem o
    # formato, e reformata-los reescreveria registro historico.
    [PY, "-m", "ruff", "format", "--check", "--no-cache", "src", "tests", "scripts"],
]


def main():
    if not COMANDOS:
        # Um verify que nao verifica nada aprovaria qualquer coisa. Falha alto
        # em vez de dar um verde falso -- o modo de falha mais perigoso aqui e
        # o silencioso.
        print("verify: ERRO -- a lista COMANDOS esta vazia.", file=sys.stderr)
        return 1

    for numero, comando in enumerate(COMANDOS, start=1):
        # flush=True e obrigatorio, nao enfeite: sem ele o print do Python fica no
        # buffer enquanto o subprocesso escreve DIRETO no terminal, e o cabecalho do
        # passo aparece DEPOIS da saida dele -- justamente quando voce esta tentando
        # descobrir qual passo falhou.
        print(f"verify [{numero}/{len(COMANDOS)}]: {' '.join(comando)}", flush=True)

        try:
            # check=False e proposital e explicito: quem decide o que fazer com um
            # codigo de saida != 0 e o laco, nao uma excecao do subprocess.
            resultado = subprocess.run(comando, check=False)
        except FileNotFoundError:
            print(f"verify: FALHOU -- comando nao encontrado: {comando[0]}", file=sys.stderr)
            return 1

        if resultado.returncode != 0:
            print(
                f"verify: FALHOU no passo {numero} (codigo {resultado.returncode})", file=sys.stderr
            )
            return 1

    print(f"verify: OK -- {len(COMANDOS)} passo(s), tudo verde.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

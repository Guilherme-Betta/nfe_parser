"""
rodar_passo3.py -- roda o PASSO 3 do loop inteiro, sem ninguem no teclado.

===========================================================================
 O QUE ESTE ARQUIVO E, E POR QUE ELE EXISTE
===========================================================================

O passo 3 do kit e "o modelo local implementa ate os testes passarem". Ele foi
desenhado para custar zero de cota do Claude -- e custava mesmo. Mas ate hoje
ele era executado A MAO: alguem digitava uma invocacao do `aider` no PowerShell,
esperava, lia o resultado, digitava a proxima.

  O efeito disso e o defeito que este script conserta: o workflow existe para
  permitir JORNADAS AUTONOMAS LONGAS, e um passo que exige um humano digitando
  entre cada tarefa nunca vai ser autonomo. Quatro stories foram entregues e
  NENHUMA rodou sozinha. (Decisao do Gui, 2026-09-14.)

Este script recebe a lista de tarefas que o passo 1 produziu, invoca o Aider uma
vez por tarefa, confere o resultado com o PROPRIO oraculo (nao com a palavra do
Aider), e para na primeira que nao converge.

---------------------------------------------------------------------------
 O QUE ELE NAO FAZ, E ISSO E PROPOSITAL
---------------------------------------------------------------------------
  * NAO re-especifica uma tarefa que falhou. Re-especificar exige RACIOCINIO,
    e raciocinio e do Claude. Se o script tentasse de novo sozinho, a distincao
    "quem resolveu o problema" se perderia -- e essa distincao e o Achado M, o
    achado mais facil de perder do projeto inteiro.
  * NAO toca no repo oficial. NUNCA. O `git merge --ff-only` continua sendo um
    passo do Gui, fora de qualquer automacao.
  * NAO edita testes. O Aider recebe o modulo de teste via `--read`, que e
    somente-leitura. Se o modelo local pudesse editar o teste, ele editaria o
    teste para passar em vez de consertar o codigo.

---------------------------------------------------------------------------
 COMO SE USA
---------------------------------------------------------------------------
    python scripts/rodar_passo3.py specs/005-cancelamento/tarefas.json
    python scripts/rodar_passo3.py <manifesto> --simular        # nao invoca nada
    python scripts/rodar_passo3.py <manifesto> --a-partir-de 3  # retoma na 3

---------------------------------------------------------------------------
 O FORMATO DO MANIFESTO (`tarefas.json`), e por que e JSON e nao markdown
---------------------------------------------------------------------------
    {
      "story": "005-cancelamento-duas-passadas",
      "tarefas": [
        {
          "id": "1",
          "titulo": "aplicar evento cujo chNFe bate com nota existente",
          "alvo": "src/nfe_parser/cancelamento.py",
          "teste": "tests/test_cancelamento.py",
          "mensagem": "specs/005-cancelamento-duas-passadas/tarefas/tarefa-01.md"
        }
      ]
    }

O passo 1 escreve o `plan.md` (prosa, para humano ler) E este `tarefas.json`
(dados, para maquina ler). Sao o mesmo backlog em dois formatos, de proposito:

  ⚠️ Extrair tarefa de markdown em prosa da errado EM SILENCIO. Um titulo
  reformatado, um traco virando outro caractere, e o parser pega a tarefa
  errada -- ou nenhuma -- sem estourar. E o mesmo modo de falha do Achado L (o
  oraculo errado que reprovou codigo bom por tres tentativas) e da armadilha do
  `--test-cmd` com barra normal: erra calado, e a culpa parece ser do modelo
  local. JSON quebra ALTO quando esta malformado, que e o que se quer aqui.
"""

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# `sys.executable` e o interpretador que esta rodando ESTE script. Usar a string
# "python" seria resolve-la pelo PATH -- que, sem a venv ativada, e o Python
# global da maquina. O sintoma e cruel e conhecido: o oraculo reprova tudo com
# "No module named pytest" e a culpa parece ser do modelo local.
PY = sys.executable

# Teto do Aider, nao escolha nossa: ele para em 3 reflexoes do `--auto-test`.
# Esta aqui como documentacao do numero que aparece no registro.
REFLEXOES_DO_AIDER = 3


# ===========================================================================
#  PRE-VOO -- falhar ALTO aqui custa segundos; falhar calado custa a janela
# ===========================================================================


def _git(*args: str) -> str:
    """Roda um comando git e devolve a saida limpa. Vazio se o git falhar."""
    resultado = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    return resultado.stdout.strip() if resultado.returncode == 0 else ""


def conferir_pre_voo(raiz: Path) -> list[str]:
    """Devolve a lista de problemas encontrados. Lista vazia = pode rodar.

    Cada item desta lista corresponde a um modo de falha JA OBSERVADO no
    projeto, nao a uma precaucao teorica. Por isso nenhum deles e um aviso
    ignoravel: todos abortam.
    """
    problemas = []

    # 1. Estamos na raiz do projeto? O Aider e o pytest dependem disso.
    if not (raiz / "scripts" / "verify.py").exists():
        problemas.append(f"nao parece a raiz do projeto (sem scripts/verify.py): {raiz}")

    # 2. NUNCA na main. E a regra 3 das Regras de seguranca do kit.
    branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    if branch in ("main", "master"):
        problemas.append(f"branch e '{branch}' -- o kit NUNCA roda na branch principal")
    elif not branch:
        problemas.append("nao consegui ler a branch atual (isto e um repo git?)")

    # 3. O clone nao pode ter remote. E a contencao que permite rodar em
    #    automode: sem remote, nao existe para onde empurrar por acidente.
    if _git("remote", "-v"):
        problemas.append("este repo TEM remote -- o clone do shakedown nao pode ter")

    # 4. Working tree limpo. Sujo antes de comecar significa que o diff do
    #    modelo local vai sair misturado com outra coisa.
    #    ⚠️ Usamos `diff --numstat` e nao `status --porcelain`: as ferramentas do
    #    Claude gravam LF e o repo usa CRLF, entao o `status` acusa arquivos
    #    "modificados" que nao tem UMA linha de diferenca. Ja custou uma
    #    investigacao inteira achando que alguem tinha mexido num teste.
    if _git("diff", "--numstat") or _git("diff", "--numstat", "--cached"):
        problemas.append("working tree tem mudancas reais -- commite ou descarte antes")

    # 5. O arquivo que da lastro ao orcamento de 8k.
    settings = raiz / ".aider.model.settings.yml"
    if not settings.exists():
        problemas.append("falta .aider.model.settings.yml -- o orcamento de 8192 fica sem lastro")
    else:
        texto = settings.read_text(encoding="utf-8")
        if "num_ctx: 8192" not in texto:
            problemas.append(".aider.model.settings.yml nao fixa num_ctx: 8192")

    # 6. O pytest existe NESTE interpretador? Se nao, todo diff vai parecer
    #    errado e a culpa vai cair no modelo local.
    checagem = subprocess.run([PY, "-c", "import pytest"], capture_output=True, check=False)
    if checagem.returncode != 0:
        problemas.append(f"o interpretador {PY} nao tem pytest -- ative a .venv")

    # 7. O aider existe?
    try:
        subprocess.run(["aider", "--version"], capture_output=True, check=False)
    except FileNotFoundError:
        problemas.append("o executavel 'aider' nao esta no PATH")

    return problemas


def conferir_contexto_do_ollama() -> str | None:
    """Le `ollama ps` e devolve o CONTEXT, se conseguir.

    ⚠️ Este e o PIOR modo de falha do kit, porque e totalmente silencioso: se o
    `num_ctx` nao casou com o nome do modelo, o Ollama roda com outro contexto e
    TODO o orcamento do kit deixa de valer -- sem erro, sem log, sem sintoma.

    Devolve None quando nao da para saber (o modelo ainda nao subiu). Nao e
    motivo para abortar: so da para ler depois da primeira invocacao.
    """
    resultado = subprocess.run(["ollama", "ps"], capture_output=True, text=True, check=False)
    if resultado.returncode != 0:
        return None

    linhas = [linha for linha in resultado.stdout.splitlines() if linha.strip()]
    if len(linhas) < 2:
        return None  # so o cabecalho: nenhum modelo carregado ainda

    # ⚠️ Separamos por DOIS-OU-MAIS espacos, e nao por espaco simples.
    # Motivo, descoberto testando: varias colunas do `ollama ps` contem um espaco
    # DENTRO do valor -- "10 GB", "100% GPU", "4 minutes from now". Um split
    # simples quebra o alinhamento e faz a coluna errada ser lida: a primeira
    # versao disto leu o "10" de "10 GB" e anunciou CONTEXT=10.
    #
    # Separando por 2+ espacos, cada campo fica inteiro e casa 1-para-1 com o
    # cabecalho -- entao lemos a coluna pelo NOME dela, nao pela posicao.
    def campos(linha: str) -> list[str]:
        return [parte.strip() for parte in re.split(r"\s{2,}", linha.strip()) if parte.strip()]

    cabecalho = campos(linhas[0])
    if "CONTEXT" not in cabecalho:
        return None
    indice = cabecalho.index("CONTEXT")

    for linha in linhas[1:]:
        valores = campos(linha)
        if indice < len(valores):
            return valores[indice]
    return None


# ===========================================================================
#  A INVOCACAO
# ===========================================================================


def montar_comando(tarefa: dict) -> list[str]:
    """Monta a linha de comando do Aider para uma tarefa.

    Cada argumento aqui tem uma medicao ou um bug atras dele. Nenhum e enfeite.
    """
    # ⚠️ ARMADILHA QUE CUSTOU TRES TENTATIVAS NA MEDICAO 5.
    # O Aider executa o `--test-cmd` pelo cmd.exe, que NAO entende caminho com
    # barra normal. Com "./.venv/..." o cmd responde "'.' nao e reconhecido como
    # um comando interno" -- e o Aider le isso como TESTE FALHOU. O modelo local
    # entao gasta as tres reflexoes consertando um codigo que ja estava certo.
    teste_windows = tarefa["teste"].replace("/", "\\")
    test_cmd = f'"{PY}" -m pytest -q {teste_windows}'

    return [
        "aider",
        "--model",
        "ollama_chat/qwen2.5-coder:14b",
        # O mapa do repo custa orcamento fixo dos 8192 tokens. Quando a tarefa ja
        # recebe o arquivo alvo explicito, o mapa nao acrescenta nada -- e sao
        # ~1,0k de contexto de graça.
        "--map-tokens",
        "0",
        # `--read` = somente leitura. E ISTO que impede o modelo local de editar
        # o teste para faze-lo passar. A ordem "testes commitados antes da
        # implementacao" nao e negociavel justamente por causa disto.
        "--read",
        tarefa["teste"],
        # ⚠️ `--message-file`, NUNCA `--message`. Sob PowerShell, aspas duplas com
        # espaco dentro partem o argumento e TRUNCAM a instrucao em silencio.
        "--message-file",
        tarefa["mensagem"],
        # Estreita o oraculo ao modulo da tarefa. O `verify.py` roda a suite
        # inteira, o que aqui seria contraproducente: falha de OUTRO modulo
        # entraria na realimentacao e gastaria as reflexoes desta tarefa.
        "--test-cmd",
        test_cmd,
        # Sem isto o Aider para esperando um "y" que ninguem vai digitar -- e a
        # rodada autonoma morre parada. E aceitavel porque o raio de dano e um
        # clone descartavel sem remote.
        "--yes-always",
        tarefa["alvo"],
    ]


def rodar_tarefa(tarefa: dict, raiz: Path, pasta_log: Path) -> dict:
    """Invoca o Aider para uma tarefa e confere o resultado. Devolve o registro.

    ⭐ A conferencia e feita RODANDO O ORACULO DE NOVO, e nao lendo o codigo de
    saida do Aider. O Achado H mostrou que verde do oraculo ja aprovou arquivo
    corrompido; aqui o ponto e outro e mais basico: quem decide se a tarefa
    convergiu tem de ser o teste, nao o relato da ferramenta.
    """
    numero = tarefa["id"]
    print(f"\n{'=' * 70}\n[tarefa {numero}] {tarefa.get('titulo', '')}\n{'=' * 70}", flush=True)

    head_antes = _git("rev-parse", "HEAD")
    inicio = time.monotonic()

    comando = montar_comando(tarefa)
    print(f"  $ {' '.join(comando)}\n", flush=True)

    # capture_output=False de proposito: numa rodada autonoma longa voce quer
    # ver o Aider trabalhando no terminal. O log em arquivo vem do `tee` abaixo.
    processo = subprocess.run(comando, cwd=raiz, capture_output=True, text=True, check=False)

    log = pasta_log / f"tarefa-{numero}.log"
    log.write_text(
        (processo.stdout or "") + "\n--- stderr ---\n" + (processo.stderr or ""),
        encoding="utf-8",
    )
    print(processo.stdout or "", flush=True)

    decorrido = round(time.monotonic() - inicio, 1)
    head_depois = _git("rev-parse", "HEAD")

    # Agora o oraculo, por nossa conta.
    teste = subprocess.run(
        [PY, "-m", "pytest", "-q", tarefa["teste"]],
        cwd=raiz,
        capture_output=True,
        text=True,
        check=False,
    )
    verde = teste.returncode == 0

    commits = []
    if head_antes and head_depois and head_antes != head_depois:
        intervalo = _git("log", "--oneline", f"{head_antes}..{head_depois}")
        commits = intervalo.splitlines()

    print(
        f"\n  -> {'VERDE' if verde else 'VERMELHO'} em {decorrido}s, "
        f"{len(commits)} commit(s) do modelo local",
        flush=True,
    )
    if not verde:
        print("\n" + (teste.stdout or "")[-2000:], flush=True)

    return {
        "id": numero,
        "titulo": tarefa.get("titulo", ""),
        "alvo": tarefa["alvo"],
        "teste": tarefa["teste"],
        "invocacoes": 1,  # este script invoca UMA vez; re-invocar e decisao do Claude
        "segundos": decorrido,
        "verde": verde,
        "commits": commits,
        "log": str(log.relative_to(raiz)) if log.is_relative_to(raiz) else str(log),
        "saida_do_teste": "" if verde else (teste.stdout or "")[-4000:],
    }


# ===========================================================================
#  O REGISTRO -- a instrumentacao do Achado 11, de graca
# ===========================================================================


def acumular_registros(novos: list[dict], acumulado: Path) -> list[dict]:
    """Funde os registros desta execucao com os das execucoes anteriores.

    🔴 ISTO CONSERTA UM BUG QUE JA CUSTOU UMA MEDICAO INTEIRA. Ate a story 005,
    `escrever_registro` gravava so os registros da execucao CORRENTE. Como
    `--a-partir-de` roda um subconjunto das tarefas, cada retomada SOBRESCREVIA
    o arquivo e apagava as tarefas ja registradas.

    O estrago medido na 005: o registro final dizia "1 de 1 tarefa verde" quando
    eram 4 de 4, e "1 invocacao" quando foram 6. Ou seja, o numero que o Achado
    11 existe para preservar -- INVOCACOES, nao tarefas -- era justamente o que
    se perdia, e a tarefa que deu trabalho (3 invocacoes, uma reversao, uma
    funcao ditada) sumia do placar como se nunca tivesse acontecido.

    A fusao e por `id` de tarefa, e uma tarefa reexecutada ACUMULA em vez de
    substituir: invocacoes somam, tempo soma, commits concatenam. O `verde` e o
    da ULTIMA execucao, que e o estado em que a tarefa de fato ficou.
    """
    if not acumulado.exists():
        return novos

    try:
        anteriores = json.loads(acumulado.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        # Registro anterior ilegivel nao pode derrubar a rodada nem, pior,
        # apagar o que sobrou dele em silencio -- que e o bug original.
        print(f"AVISO: nao consegui ler {acumulado}; seguindo so com esta execucao.", flush=True)
        return novos

    por_id = {r["id"]: r for r in anteriores}
    for novo in novos:
        antigo = por_id.get(novo["id"])
        if antigo is None:
            por_id[novo["id"]] = novo
            continue
        fundido = dict(novo)
        fundido["invocacoes"] = antigo.get("invocacoes", 0) + novo["invocacoes"]
        fundido["segundos"] = round(antigo.get("segundos", 0) + novo["segundos"], 1)
        fundido["commits"] = antigo.get("commits", []) + novo["commits"]
        por_id[novo["id"]] = fundido

    # Ordena pelo id numerico quando der, para a tabela sair na ordem do backlog.
    def chave(registro: dict):
        try:
            return (0, int(registro["id"]))
        except (TypeError, ValueError):
            return (1, str(registro["id"]))

    return sorted(por_id.values(), key=chave)


def escrever_registro(registros: list[dict], manifesto: dict, destino: Path, contexto: str | None):
    """Escreve o resumo em markdown, pronto para colar no offload-log.

    ⭐ Isto existe porque a instrumentacao que o Achado 11 pediu -- contar
    INVOCACOES e nao so tarefas -- era feita a mao e por isso saia errada: na
    medicao 5 foram 6 tarefas e 9 invocacoes, e a diferenca some do registro se
    ninguem contar na hora. Aqui ela e subproduto da execucao, nao tarefa extra.

    ⚠️ O que este arquivo NAO sabe dizer: DE QUEM foi o raciocinio (o Achado M).
    Um verde depois de o Claude ditar o codigo e indistinguivel, daqui, de um
    verde que o modelo local achou sozinho. Essa coluna e preenchida a mao, pelo
    Claude, e o proprio fato de nao ser automatizavel e o motivo de ela existir.
    """
    verdes = sum(1 for r in registros if r["verde"])
    total_invocacoes = sum(r["invocacoes"] for r in registros)
    total_commits = sum(len(r["commits"]) for r in registros)
    segundos = sum(r["segundos"] for r in registros)

    # `astimezone()` sem argumento carimba a hora LOCAL com o fuso junto. O resto
    # do repo grava UTC (ver persistencia.py) porque la sao DADOS; aqui e um
    # carimbo para humano ler, e hora local e mais util para isso.
    carimbo = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")

    linhas = [
        f"# Passo 3 — registro automatico — {manifesto.get('story', '?')}",
        "",
        f"Rodado em {carimbo} por `scripts/rodar_passo3.py`.",
        "",
        f"- **Tarefas verdes:** {verdes} de {len(registros)}",
        f"- **Invocacoes do Aider:** {total_invocacoes}",
        f"- **Commits do modelo local:** {total_commits}",
        f"- **Tempo total no passo 3:** {round(segundos / 60, 1)} min",
        f"- **CONTEXT do Ollama:** {contexto or 'nao lido'}"
        + ("" if contexto == "8192" else "  ⚠️ **deveria ser 8192**"),
        "",
        "| # | Tarefa | Verde? | Invocacoes | Tempo | Commits | Quem resolveu |",
        "| - | ------ | ------ | ---------- | ----- | ------- | ------------- |",
    ]
    for r in registros:
        linhas.append(
            f"| {r['id']} | {r['titulo']} | {'✅' if r['verde'] else '❌'} | "
            f"{r['invocacoes']} | {r['segundos']}s | {len(r['commits'])} | "
            f"⏳ *preencher a mao — Achado M* |"
        )

    linhas += [
        "",
        "> ⚠️ A coluna **Quem resolveu** NAO e preenchivel por script. Marque a mao:",
        (
            "> 🤖 modelo local · 👤 Claude ditou o codigo · 🤝 misto. Sem ela, "
            '"N/N tarefas verdes" e "N/N resolvidas pelo modelo local" viram a '
            "mesma linha — e na medicao 5 nao eram (Achado M)."
        ),
    ]

    # ⭐ A EVIDENCIA BRUTA, DENTRO DA DOCUMENTACAO.
    #
    # Decisao do Gui (2026-09-14): o repo oficial passa a receber as stories com
    # historico CURADO, e nao com as mensagens que o Aider gera -- que sao
    # frequentemente a explicacao inteira despejada como titulo. O argumento
    # dele: documentacao boa vale mais do que a evidencia crua espalhada pelo
    # `git log` de um repositorio publico.
    #
    # Para que curar o historico nao APAGUE a evidencia, ela passa a ser
    # registrada aqui -- num arquivo que e commitado e lido, em vez de num
    # historico que sera squashado. Este bloco e o que torna as duas coisas
    # compativeis, em vez de um trade-off.
    linhas += [
        "",
        "---",
        "",
        "## Commits brutos do modelo local",
        "",
        "Registrados aqui porque a transferencia para o repo oficial usa historico curado.",
        "Esta e a evidencia do que o modelo local produziu, tarefa a tarefa — o `git log`",
        "do repo oficial nao a tem mais, e o clone do shakedown e descartavel.",
        "",
    ]
    for r in registros:
        linhas.append(f"**Tarefa {r['id']} — {r['titulo']}**")
        linhas.append("")
        if r["commits"]:
            linhas += [f"- `{commit}`" for commit in r["commits"]]
        else:
            linhas.append("- *(nenhum commit — o modelo local nao aplicou nenhuma edicao)*")
        linhas.append("")

    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8")


# ===========================================================================
#  MAIN
# ===========================================================================


def main() -> int:
    ap = argparse.ArgumentParser(description="Roda o passo 3 do kit sem intervencao humana.")
    ap.add_argument("manifesto", help="caminho do tarefas.json produzido pelo passo 1")
    ap.add_argument("--simular", action="store_true", help="so mostra o que faria")
    ap.add_argument("--a-partir-de", default=None, help="retoma a partir do id desta tarefa")
    args = ap.parse_args()

    raiz = Path.cwd()
    caminho_manifesto = Path(args.manifesto)
    if not caminho_manifesto.exists():
        print(f"ERRO: manifesto nao encontrado: {caminho_manifesto}", file=sys.stderr)
        return 1

    manifesto = json.loads(caminho_manifesto.read_text(encoding="utf-8"))
    tarefas = manifesto["tarefas"]

    # --- pre-voo -----------------------------------------------------------
    problemas = conferir_pre_voo(raiz)
    for tarefa in tarefas:
        for campo in ("id", "alvo", "teste", "mensagem"):
            if campo not in tarefa:
                problemas.append(f"tarefa {tarefa.get('id', '?')}: falta o campo '{campo}'")
        if "mensagem" in tarefa and not (raiz / tarefa["mensagem"]).exists():
            problemas.append(
                f"tarefa {tarefa.get('id', '?')}: mensagem nao existe: {tarefa['mensagem']}"
            )
        if "teste" in tarefa and not (raiz / tarefa["teste"]).exists():
            problemas.append(f"tarefa {tarefa.get('id', '?')}: teste nao existe: {tarefa['teste']}")

    if problemas:
        print("PRE-VOO REPROVOU. Nada foi invocado:\n", file=sys.stderr)
        for p in problemas:
            print(f"  ⛔ {p}", file=sys.stderr)
        return 1
    print(f"pre-voo: OK -- {len(tarefas)} tarefa(s) no manifesto.", flush=True)

    if args.a_partir_de is not None:
        ids = [t["id"] for t in tarefas]
        if args.a_partir_de not in ids:
            print(f"ERRO: nao existe tarefa com id '{args.a_partir_de}'", file=sys.stderr)
            return 1
        tarefas = tarefas[ids.index(args.a_partir_de) :]
        print(f"retomando a partir da tarefa {args.a_partir_de} ({len(tarefas)} restantes).")

    if args.simular:
        print("\n--simular: nenhuma invocacao sera feita.\n")
        for tarefa in tarefas:
            print(f"[tarefa {tarefa['id']}] {tarefa.get('titulo', '')}")
            print(f"  $ {' '.join(montar_comando(tarefa))}\n")
        return 0

    # --- a rodada ----------------------------------------------------------
    pasta_log = raiz / "passo3-logs" / manifesto.get("story", "story")
    pasta_log.mkdir(parents=True, exist_ok=True)

    registros = []
    interrompeu = False
    for tarefa in tarefas:
        registro = rodar_tarefa(tarefa, raiz, pasta_log)
        registros.append(registro)
        if not registro["verde"]:
            # ⛔ PARA. Nao tenta de novo, e nao segue para a proxima.
            #
            # Nao tenta de novo porque re-especificar exige raciocinio, e quem
            # raciocina e o Claude -- se o script insistisse sozinho, o registro
            # diria "3 invocacoes" sem dizer que as duas ultimas foram cegas.
            #
            # Nao segue para a proxima porque as tarefas de uma story costumam
            # depender umas das outras: seguir em cima de um modulo vermelho
            # produz uma cascata de falhas que esconde a causa real.
            print(
                f"\n⛔ PARANDO na tarefa {registro['id']}: o oraculo ficou vermelho "
                f"depois das {REFLEXOES_DO_AIDER} reflexoes do Aider.\n"
                f"   O log completo esta em {registro['log']}.\n"
                f"   ⚠️ A tentativa que falhou JA ESTA COMMITADA "
                f"({len(registro['commits'])} commit(s)): o `auto-commits` do Aider "
                f"commita a edicao mesmo com o teste vermelho.\n"
                f"   Ao re-especificar, decida se aproveita ou reverte.\n"
                f"   Proximo passo e do Claude: ler o log, re-especificar a tarefa, "
                f"e retomar com --a-partir-de {registro['id']}.",
                file=sys.stderr,
            )
            interrompeu = True
            break

    contexto = conferir_contexto_do_ollama()
    if contexto and contexto != "8192":
        print(
            f"\n⚠️ ATENCAO: `ollama ps` diz CONTEXT={contexto}, nao 8192. "
            "Todo o orcamento do kit foi calculado contra 8192 -- os numeros "
            "desta rodada nao valem para comparacao.",
            file=sys.stderr,
        )

    # ⭐ FUNDE com as execucoes anteriores ANTES de escrever. Sem isto, um
    # `--a-partir-de` apaga do registro as tarefas que ja tinham rodado.
    acumulado = pasta_log / "registro.json"
    registros = acumular_registros(registros, acumulado)

    destino = caminho_manifesto.parent / "passo3-registro.md"
    escrever_registro(registros, manifesto, destino, contexto)
    acumulado.write_text(json.dumps(registros, indent=2, ensure_ascii=False), encoding="utf-8")

    verdes = sum(1 for r in registros if r["verde"])
    print(f"\n{'=' * 70}")
    print(f"passo 3: {verdes}/{len(registros)} tarefa(s) verdes. Registro em {destino}")
    print(f"{'=' * 70}")

    return 1 if interrompeu else 0


if __name__ == "__main__":
    sys.exit(main())

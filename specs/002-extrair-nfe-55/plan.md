# Plan — 002 · Extrair uma NF-e 55 de 1 item

> **Sprint backlog: a spec fatiada em tarefas que cabem no modelo local.**
> Uma linha = uma invocacao do Aider.

## Regras de fatiamento (nao sao sugestoes)

| # | Regra | Vem de |
| - | ----- | ------ |
| 1 | Cada tarefa cabe em **~300 linhas** de codigo relevante | orcamento de 8192 tokens |
| 2 | **Um pedido, um defeito** | Fase 0: dois defeitos no mesmo pedido -> blocos SEARCH/REPLACE sobrepostos -> arquivo corrompido |
| 3 | Cada tarefa cabe em **3 tentativas** do `--auto-test` | e o teto do Aider (`Only 3 reflections allowed`) |
| 4 | **`/clear` entre tarefas** | 3 turnos ja estouram os 8k, em silencio |
| 5 | **>6k tokens no turno 1 condena o laco** | story 001: o turno 1 saiu a 7,0k e as 3 reflexoes rodaram truncadas, em silencio |

> Estourar a regra 3 nao e sinal de repetir o pedido — e sinal de que a tarefa
> era grande demais. Quebre e refaca.

## Tarefas

| # | Tarefa | Oraculo da tarefa | `edit-format` | Turno 1 | Status |
| - | ------ | ----------------- | ------------- | ------- | ------ |
| 1 | `para_centavos(texto) -> int`: exato ao centavo, **rejeita** mais de 2 casas em vez de truncar | `tests/test_para_centavos.py` (7) | `diff` | **4,5k** ✅ | ✅ **aceita** — 1 turno, 0 reflexoes |
| 2 | ~~`extrair_nota` inteira~~ | ~~`tests/test_extrator.py` (19)~~ | `diff` | **8,9k** ⛔ | ❌ **abortada** — ver abaixo |
| 2a | `extrair_nota`: so o bloco `"nota"` e o caminho de erro | `tests/test_extrator_nota.py` (12) | `diff` | | ⬜ |
| 2b | `extrair_nota`: preencher a lista `"itens"` | `tests/test_extrator_itens.py` (8) | `diff` | | ⬜ |

Todas em `src/nfe_parser/extrator.py`.

**Status:** ⬜ nao iniciada · 🔄 no modelo local · 👀 aguardando revisao · ✅ aceita

### ⭐ Por que DUAS tarefas aqui, se a story 001 foi uma so

A story 001 cabia em uma invocacao e mesmo assim mandou **7,0k no turno 1**, contra um `num_ctx` de
8192 — e as tres reflexoes seguintes rodaram com contexto **truncado em silencio** (Achado B do
`offload-log.md`). Esta story tem mais contexto obrigatorio que aquela: a spec traz a tabela da
API do `nfelib` (§4), que nao da para cortar sem devolver o modelo a adivinhacao.

Entao o fatiamento aqui nao e zelo, e aritmetica de orcamento:

- **Tarefa 1 nao precisa do `nfelib` em lugar nenhum.** E `Decimal` e nada mais — entao ela vai
  sem a spec no `--read`, so com o seu modulo de teste, e o turno 1 sai pequeno.
- **Tarefa 2 precisa do §4 inteiro**, mas ja encontra `para_centavos` pronto no arquivo — nao
  precisa raciocinar sobre dinheiro, so chamar.

E a regra 2 (um pedido, um defeito) fica satisfeita de quebra: "converter dinheiro" e "ler XML"
sao dois objetivos, nao um.

### ⭐ O oraculo tambem precisa ser fatiado — e isso obriga a fatiar os testes

Fatiar a story em duas invocacoes esbarra num problema que so aparece ao montar:
**o `--auto-test` roda o `verify` inteiro**, entao na tarefa 1 o modelo veria os 19 testes de
`extrair_nota` falhando e queimaria as 3 reflexoes consertando o que ninguem pediu.

Filtrar com `pytest -k` **nao resolve**, e o motivo e mais fundo: se os dois grupos morassem no
mesmo modulo, o `import` do topo pediria as duas funcoes e a **coleta** do modulo quebraria antes
de o filtro rodar. Depois da tarefa 1 o arquivo inteiro ficaria vermelho, e a tarefa 1 nao teria
como ficar verde por mais certa que estivesse.

**Por isso os testes moram em dois modulos**, cada um importando so o que a sua tarefa cria:

| Tarefa | Testes | Oraculo da tarefa |
| ------ | ------ | ----------------- |
| 1 — `para_centavos` | `tests/test_para_centavos.py` (7) | `python -m pytest tests/test_para_centavos.py -q` |
| 2 — `extrair_nota` | `tests/test_extrator.py` (19) | `python scripts/verify.py` (o `verify` inteiro, ja com tudo) |

> **A regra que fica: story fatiada em N tarefas = testes em N modulos.** Verificado: com so
> `para_centavos` no disco, `test_para_centavos.py` da 7 passed enquanto `test_extrator.py` ainda
> nem coleta — que e exatamente o comportamento desejado.

> ⚠️ O `verify.py` **nao aceita argumento** — o contrato do kit e "rode e olhe o codigo de
> saida". Entao o oraculo estreito da tarefa 1 entra por `--test-cmd` na linha de comando, que
> sobrescreve o do `.aider.conf.yml`. O `verify` completo volta a valer na tarefa 2 e no passo 4.

### ❌ A tarefa 2 estourou o orcamento — medido em 2026-09-12

**Turno 1: 8,9k tokens enviados, contra um `num_ctx` de 8192.** O contexto foi truncado em
silencio, como manda o Achado B. O que o modelo produziu prova que ele nao chegou a ver a tabela
da API:

| O que ele escreveu | O que existe de verdade |
| ------------------ | ----------------------- |
| `from nfelib.nfe_v4_00 import NFe` | `from nfelib.nfe.bindings.v4_0.proc_nfe_v4_00 import NfeProc` |
| `NFe.parse(xml)` | `NfeProc.from_xml(xml)` |
| `nfe.infNFe.ide.chNFe` | `inf.Id`, com o prefixo `NFe` a remover |
| `emit.endERemit` | `emit.enderEmit` |
| chaves `"data_emissao"`, `"uf_emissao"`, `"numero_item"` | as colunas do DDL, listadas no §2 da spec |

E ainda emitiu o bloco no **formato errado** (cercas ```` no lugar de `SEARCH/REPLACE`), entao
**nenhuma edicao foi aplicada** e o `--auto-test` nem chegou a rodar. Nada quebrou no repo: o
arquivo ficou como estava.

**De onde vinham os 8,9k:** o prompt do Aider em `diff` (~2,3k) + mapa do repo (1,0k) +
`spec.md` inteira (~2,5k) + `test_extrator.py` (~1,4k) + o arquivo + a mensagem.

**Os dois cortes, e por que nesta ordem:**

1. **A tabela da API saiu da spec para [`api-nfelib.md`](api-nfelib.md)** (~0,63k contra ~2,5k da
   spec inteira). Isso **nao joga informacao fora** — e a mesma tabela, num arquivo que cabe no
   `--read`. E as stories 003+ vao querer ela do mesmo jeito.
2. **`extrair_nota` virou duas tarefas**, e por consequencia `test_extrator.py` virou dois
   modulos. Pela regra ja estabelecida: story fatiada em N tarefas = testes em N modulos.

> ⭐ **A licao generalizavel:** o orcamento nao e do *codigo* a escrever, e do **contexto a
> mandar**. A tarefa 2 pedia ~45 linhas de codigo — folgadissimo nas ~300 da regra 1 — e mesmo
> assim estourou, porque o que pesa e a documentacao que a torna executavel. **A regra 1 do
> fatiamento mede a coisa errada.** O que vale e a regra 5.

### Como invocar

O modelo **le** os testes e nao os edita (`--read`). Isso nao e estilo: se ele puder editar o
teste, ele edita o teste para faze-lo passar — e o caminho mais curto para o objetivo dado.

```powershell
# de dentro de nfe_parser-shakedown, com a .venv ATIVADA

# --- tarefa 1: para_centavos ------------------------------------- FEITA (4,5k)
aider --model ollama_chat/qwen2.5-coder:14b `
      --read tests/test_para_centavos.py `
      --file src/nfe_parser/extrator.py `
      --test-cmd "python -m pytest tests/test_para_centavos.py -q" `
      --yes-always --message "..."

# --- tarefa 2a: o bloco "nota" ---------------------------------------------
# --map-tokens 0 economiza 1,0k: o mapa do repo nao ajuda numa tarefa que ja
# recebe o arquivo alvo e a referencia da API.
aider --model ollama_chat/qwen2.5-coder:14b `
      --read tests/test_extrator_nota.py `
      --read specs/002-extrair-nfe-55/api-nfelib.md `
      --file src/nfe_parser/extrator.py `
      --map-tokens 0 `
      --test-cmd "python -m pytest tests/test_extrator_nota.py -q" `
      --yes-always --message "..."

# --- tarefa 2b: a lista "itens" --------------------------------------------
aider --model ollama_chat/qwen2.5-coder:14b `
      --read tests/test_extrator_itens.py `
      --read specs/002-extrair-nfe-55/api-nfelib.md `
      --file src/nfe_parser/extrator.py `
      --map-tokens 0 `
      --test-cmd "python -m pytest tests/test_extrator_itens.py -q" `
      --yes-always --message "..."
```

⛔ **A spec.md inteira nao vai mais no `--read` de tarefa nenhuma.** Foi o que estourou o
orcamento. O que o modelo precisa esta em `api-nfelib.md` e no proprio modulo de teste.

> ⚠️ A `.venv` **precisa** estar ativada. O `verify` usa `sys.executable`, entao ele herda o
> interpretador de quem o chamou — e quem o chama e o Aider.

> ⚠️ **Medir o turno 1.** O Aider imprime os tokens enviados. Se a tarefa 2 sair acima de **6k**,
> pare e quebre de novo (por exemplo: `extrair_nota` so com o bloco `"nota"`, e os `"itens"` numa
> terceira invocacao — o que exigiria um terceiro modulo de teste, pela regra acima). Rodar assim
> mesmo desperdica as 3 reflexoes em silencio.

> ⚠️ **A fixture NAO vai no `--read` da tarefa 2.** Ela tem ~140 linhas de XML e o §4 da spec ja
> traz todos os valores que importam, medidos contra ela. Mandar as duas coisas e pagar duas vezes
> pela mesma informacao.

### Coluna `edit-format` — como preencher

| Situacao | Use |
| -------- | --- |
| escrever codigo novo; modificar no lugar; arquivo acima de ~120 linhas | **`diff`** (padrao) |
| **reorganizar** (mover/reordenar/renomear) em arquivo de ate ~120 linhas | **`whole`**, via `--edit-format whole` |
| mudanca **so de espaco em branco** | ⛔ nao delegue — `ruff format` / `ruff check --fix` |
| qualquer caso | **nunca `udiff`** |

## ⛔ Antes do primeiro `aider`, sempre

```powershell
git rev-parse --abbrev-ref HEAD    # scrum, nunca main
git status --porcelain             # vazio
python scripts/verify.py           # VERMELHO aqui -- e o esperado, ver abaixo
```

⚠️ **O pre-voo herdado da story 001 pedia `verify` VERDE, e isso e impossivel no passo 3.** O
passo 2 commita os testes **antes** da implementacao, entao quando o Aider e invocado o `verify`
esta necessariamente vermelho — e e justamente esse vermelho que o `--auto-test` usa como alvo.
Um `verify` verde aqui significaria que **nao ha teste novo**, ou seja, que o passo 2 nao foi feito.

**O pre-voo correto no passo 3 e outro:** o `verify` tem que falhar **so** pelos testes da story,
e nao por ambiente quebrado. Confira que a falha e `ModuleNotFoundError` do modulo que a tarefa vai
criar (ou assercao dos testes novos) — nao `No module named pytest`, que seria a `.venv` nao
ativada, e faria **todo** diff parecer errado com a culpa caindo no modelo local.

## ⛔ No passo 4, o lint e com `--no-cache`

```powershell
ruff check --fix --no-cache .
```

Dois motivos, os dois medidos e os dois no `steering/verificacao.md`:

1. O `ruff` classifica import conforme os arquivos que existem no disco **naquele momento**, e o
   cache dele nao invalida quando um modulo novo aparece. Como o passo 2 commita os testes **antes**
   da implementacao, esse descompasso e estrutural no kit.
2. O CI roda **Linux** e a juicey e **Windows**. Ha regra que so dispara la (`EXE001` le o bit de
   execucao, que no Windows nao existe). **Verde local nao prova CI verde** — confira o run.

## Rastro (invariante 3: `git log` e a fonte da verdade)

```bash
git log --author="Aider"  --oneline    # o que o modelo local escreveu
git log --author="Betta"  --oneline    # o que saiu do par com o Claude
```

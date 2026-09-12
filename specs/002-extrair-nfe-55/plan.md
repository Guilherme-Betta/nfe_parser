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

| # | Tarefa | Arquivos | `edit-format` | Status |
| - | ------ | -------- | ------------- | ------ |
| 1 | `para_centavos(texto) -> int`: exato ao centavo, **rejeita** mais de 2 casas em vez de truncar | `src/nfe_parser/extrator.py` (novo) · oraculo: `tests/test_para_centavos.py` | `diff` | ⬜ |
| 2 | `extrair_nota(xml_texto) -> dict`: le o `nfeProc` com `nfelib` e devolve `{"nota": ..., "itens": [...]}` | `src/nfe_parser/extrator.py` · oraculo: `verify` completo | `diff` | ⬜ |

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

### Como invocar

O modelo **le** os testes e nao os edita (`--read`). Isso nao e estilo: se ele puder editar o
teste, ele edita o teste para faze-lo passar — e o caminho mais curto para o objetivo dado.

```powershell
# de dentro de nfe_parser-shakedown, com a .venv ATIVADA

# --- tarefa 1: para_centavos ----------------------------------------------
# Sem --read na spec de proposito: para_centavos nao precisa do nfelib nem do
# §4, e a spec inteira custaria ~2,6k do orcamento de 8k a toa.
aider --model ollama_chat/qwen2.5-coder:14b `
      --read tests/test_para_centavos.py `
      --file src/nfe_parser/extrator.py `
      --test-cmd "python -m pytest tests/test_para_centavos.py -q" `
      --yes-always `
      --message "..."

# /clear entre as duas   <- regra 4

# --- tarefa 2: extrair_nota -----------------------------------------------
# Aqui a spec E obrigatoria: o §4 tem a tabela do que o nfelib devolve, que o
# modelo nao tem orcamento para descobrir sozinho.
aider --model ollama_chat/qwen2.5-coder:14b `
      --read tests/test_extrator.py `
      --read specs/002-extrair-nfe-55/spec.md `
      --file src/nfe_parser/extrator.py `
      --yes-always `
      --message "..."
```

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

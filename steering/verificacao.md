# Verificacao — o que o `verify` checa NESTE projeto, e por que

> ★ `python scripts/verify.py` e o portao de commit: nada e commitado com ele vermelho. Quem le so o
> codigo do verify ve O QUE ele roda; este arquivo registra POR QUE aquilo e suficiente — e o que
> ele deixa passar.

## O que o `verify` roda

| # | Comando | Para que |
| - | ------- | -------- |
| 1 | `{sys.executable} -m pytest -q` | a suite: o contrato das specs, transformado em assercao |
| 2 | `{sys.executable} -m ruff check --no-cache .` | o mesmo lint que o CI roda |
| 3 | `{sys.executable} -m ruff format --check --no-cache src tests scripts` | o formato adotado (ver abaixo); o CI nao cobra |

**O objetivo e "verde aqui = verde no CI".** O verify e o CI mais o formato — com uma excecao que
nenhum comando local fecha (o `EXE001`, abaixo).

> Historico: de 2026-09-08 a 2026-10-14 o verify rodava **so o pytest**. O `ruff` tinha saido
> porque o modelo local que implementava as stories nao conseguia expressar uma correcao de espaco
> em branco no formato de edicao do Aider. Sem o modelo local, o motivo deixou de existir. Ver
> `docs/historico/experimento-modelo-local/`.

**Por que `sys.executable` e nao a string `"python"`.** `"python"` seria resolvido pelo PATH. Com a
`.venv` nao ativada, isso e o Python global da juicey — que **nao tem pytest**. O verify reprovaria
tudo com "No module named pytest", e a culpa pareceria ser do codigo.

### ⛔ O lint roda com `--no-cache`, sempre

Descoberto em 2026-09-08. **O `ruff` deu verde local e vermelho no CI, com o arquivo identico.** Dois
mecanismos empilhados:

**1. A classificacao de import depende de o modulo EXISTIR no disco.** O `ruff` decide se
`nfe_parser` e "primeira parte" (bloco separado) ou "terceiro" (junto com o `pytest`) resolvendo o
import contra os arquivos. Provado:

| Situacao | `ruff check --no-cache tests/test_banco.py` |
| -------- | ------------------------------------------- |
| `src/nfe_parser/banco.py` **ausente** | `All checks passed` |
| `src/nfe_parser/banco.py` **presente** | `I001` |

Isto morde quem escreve o teste ANTES da implementacao: o lint que passa naquele momento pode
reprovar depois, **sem ninguem tocar no arquivo de teste**.

**2. O cache do `ruff` nao sabe disso.** Ele e indexado pelo arquivo analisado; um arquivo NOVO
aparecendo em outro lugar muda a resposta certa para um arquivo INALTERADO, e o cache continua
servindo a resposta velha. Provado no mesmo arquivo, no mesmo commit:

| Comando | Resultado |
| ------- | --------- |
| `ruff check tests/test_banco.py` (com cache) | `All checks passed` |
| `ruff check --no-cache tests/test_banco.py` | `Found 1 error` |

O CI nunca tem cache — se voce confiar no cache local, ele descobre por voce, tarde.

### ⛔ Lint do CI roda em Linux; o Windows nao ve tudo

Descoberto em 2026-09-12. O CI ficou **vermelho** com um erro que **nunca apareceu na maquina
local**:

```
EXE001 Shebang is present but file is not executable
 --> scripts/verify.py:1:1
```

**Por que nao aparece no Windows.** O `EXE001` le o **bit de execucao** do arquivo. Isso e metadado
de sistema de arquivos POSIX; no Windows ele nao existe, entao o `ruff` pula a regra em silencio.

| Onde | `ruff check .` |
| ---- | -------------- |
| Windows (juicey), checkout limpo | `All checks passed` |
| Linux (CI), mesmo commit | `EXE001`, exit 1 |

O `--no-cache` conserta um verde velho; aqui **nao existe comando local que revele o problema**.
O unico detector e o proprio CI.

**A regra:** neste projeto, **script `.py` nao leva shebang**. Nada e executado direto — tudo e
chamado como `python scripts/<nome>.py`. Se algum dia um arquivo precisar mesmo ser executavel,
marque o bit no git (`git update-index --chmod=+x`) **e** anote aqui, porque o lint local nunca vai
cobrar.

**Corolario para ler o CI:** um email do GitHub Actions dizendo *"N annotations"* pode ser N erros
de lint de verdade. Va no log do job antes de concluir.

### O `ruff format` e adotado desde 2026-09-13

Aplicado de uma vez no commit isolado `157ce83`, puro de formatacao, para poder ser ignorado no
`git blame`. Desde entao o layout nao se discute em revisao: o formatador decide.

⚠️ **Efeito colateral que surpreende:** o `ruff format` tambem reescreve blocos de codigo Python
**dentro de arquivos `.md`**. E por isso que o verify o restringe a `src`, `tests` e `scripts`: as
specs antigas tem blocos fora do formato, e reformata-los reescreveria registro historico.

O CI **nao** roda o `ruff format`. Com o verify cobrando, a checagem no CI seria redundante num
projeto de um dono so.

## Por que isso e suficiente aqui

Os nucleos — parser (01), classificacao (02), orcamento (04) e as agregacoes dos relatorios (05) —
sao componentes onde teste basta: entrada = XML e chamadas de funcao, saida = linhas no SQLite e
JSON. Nao ha rede no caminho testado (o LLM entra por uma funcao injetada), nao ha concorrencia.

A camada web (03) e testada pela `TestClient` do FastAPI: rotas, status, JSON, HTML renderizado e
o JSON que alimenta os graficos. **O que ela nao ve e o que o navegador faz com isso** — por isso o
passo "mexeu em tela: subir o app e olhar" do `CLAUDE.md`. Em 2026-10-15 esse passo pegou tres
defeitos que a suite aprovava: rotulos de loja/produto identicos, eixo de valores ilegivel, e o
preco no tempo com datas irregulares espacadas por igual.

## Buracos conhecidos

A pergunta honesta: **o que poderia estar quebrado e mesmo assim passar?**

| O que o verify NAO pega | Por que aceitamos, por enquanto |
| ----------------------- | ------------------------------- |
| **Comportamento sem teste.** `pytest` so verifica o que alguem escreveu | Os testes vem da spec e sao **commitados antes** da implementacao. O buraco vira "spec incompleta", que e visivel |
| **Teste fraco.** Um teste que confere pouco aprova codigo errado em silencio | Ao escrever um teste novo, conferir que ele FALHA no codigo antigo pelo motivo certo, e nao so que passa no novo |
| **Dado pessoal real numa fixture.** Nenhum comando distingue um CNPJ real de um fake | Repo publico: risco alto. Defesa = `.gitignore` (`*.xml` fora de `tests/fixtures/`) + revisao humana |
| **Regras de lint que dependem de POSIX** | O `EXE001` le o bit de execucao, que nao existe no Windows. Nao ha comando local que detecte; so o CI |
| **Python 3.14 local × 3.11 no CI** | A juicey so tem 3.14. Codigo que dependa de detalhe de 3.12+ passa aqui e quebra no CI |
| **Erros de tipo.** Sem `mypy`/`pyright` | O projeto nao adotou type checker |
| **Cobertura.** Um teste vazio passa | Sem `--cov` nem minimo exigido; a revisao e quem olha |
| **Performance.** Lote grande pode ficar lento | Nenhum criterio de aceitacao fala de tempo |
| **JavaScript.** `web/static/graficos.js` e o comportamento do HTMX nao rodam em teste nenhum | Sem navegador na suite. A pagina tem a tabela gemea de cada grafico (os numeros sao testados no HTML), e a conferencia e visual, no navegador |
| **Layout e legibilidade.** Rotulo sobreposto, eixo apertado, tema escuro | Idem: e o passo "subir o app e olhar" |
| **A imagem Docker.** O `verify` so le o `Dockerfile` e o compose (`tests/test_deploy.py`) | Montar, subir, conferir a imagem limpa e a persistencia roda no workflow `imagem.yml`, no GitHub. Na juicey o Docker Desktop nao sobe |

> ⚠️ **Um teste fraco nao falha ruidosamente — ele aprova codigo errado em silencio.** Medido na
> Fase 0: um teste de idempotencia que conferia so `COUNT(*)` teria aprovado uma implementacao que
> sobrescrevia os valores.

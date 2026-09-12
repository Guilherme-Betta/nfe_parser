# Verificacao — o que o `verify` checa NESTE projeto, e por que

> ★ Este arquivo existe porque o `scripts/verify.py` e o **juiz** de toda a
> arquitetura: o modelo local itera ate ele passar, e o diff e aceito porque
> ele passou. Quem le so o codigo do verify ve O QUE ele roda; este arquivo
> registra POR QUE aquilo e suficiente para dizer "esta bom".

## O que o `verify` roda

| # | Comando | Para que |
| - | ------- | -------- |
| 1 | `{sys.executable} -m pytest -q` | a suite. E o contrato das invariantes do §5 da spec 01 |

**So isso.** O `ruff` esteve aqui e **saiu em 2026-09-08**, na primeira story.

**Por que `sys.executable` e nao a string `"python"`.** `"python"` seria
resolvido pelo PATH. Com a `.venv` nao ativada, isso e o Python global da
juicey — que **nao tem pytest**. O oraculo reprovaria todo diff com
"No module named pytest", e a culpa pareceria ser do modelo local. Foi um
defeito real do kit, encontrado neste shakedown e corrigido na fonte.

### Por que o `ruff` saiu do oraculo (medido, nao teorizado)

A versao original deste arquivo defendia que o verify devia **espelhar o CI**
(`ruff` + `pytest`), com os testes ANTES do lint para que as 3 reflexoes do
Aider fossem gastas em corretude. **A story 001 mostrou que o argumento tinha um
buraco.**

O que aconteceu, na integra:

1. O modelo local acertou a implementacao **no primeiro turno** — 8 testes
   verdes, incluindo os tres do caminho de erro.
2. O `ruff` reprovou com **I001**: faltava uma linha em branco no bloco de
   import.
3. O modelo gastou as **tres** reflexoes tentando consertar isso, e nas tres
   emitiu blocos `SEARCH/REPLACE` com o texto **identico dos dois lados**.
   `Only 3 reflections allowed, stopping.`

**A ordem nao protegeu nada.** Ela so decide qual falha o modelo ve primeiro;
quando os testes passam de primeira, o lint herda o orcamento de reflexoes
inteiro. O raciocinio "testes antes do lint" estava certo e era irrelevante.

**E o modelo nao estava sendo teimoso — ele nao conseguia expressar o conserto.**
Uma mudanca so de espaco em branco e praticamente inexprimivel no formato
`diff`: `SEARCH` e `REPLACE` ficam com a mesma aparencia. Isso e novo em relacao
a tabela de `edit-format` da Fase 0, que so cobria reorganizacao de linhas.

**A regra que fica:** o oraculo do modelo local julga **corretude**. Estilo e do
passo 4 — `ruff check --fix` resolveu este caso em **um segundo**, contra tres
reflexoes desperdicadas.

### ⛔ Ao rodar o lint no passo 4, use `--no-cache`

Descoberto em 2026-09-08, logo depois da story 001. **O `ruff` deu verde local e vermelho no CI,
com o arquivo identico.** Dois mecanismos empilhados:

**1. A classificacao de import depende de o modulo EXISTIR no disco.** O `ruff` decide se
`nfe_parser` e "primeira parte" (bloco separado) ou "terceiro" (junto com o `pytest`) resolvendo o
import contra os arquivos. Provado:

| Situacao | `ruff check --no-cache tests/test_banco.py` |
| -------- | ------------------------------------------- |
| `src/nfe_parser/banco.py` **ausente** | `All checks passed` |
| `src/nfe_parser/banco.py` **presente** | `I001` |

**Isto morde exatamente o loop do kit.** O passo 2 escreve e commita os testes **antes** de a
implementacao existir. O lint que passa naquele momento pode reprovar depois, **sem ninguem tocar
no arquivo de teste** — foi o que aconteceu aqui.

**2. O cache do `ruff` nao sabe disso.** Ele e indexado pelo arquivo analisado; um arquivo NOVO
aparecendo em outro lugar muda a resposta certa para um arquivo INALTERADO, e o cache continua
servindo a resposta velha. Provado no mesmo arquivo, no mesmo commit:

| Comando | Resultado |
| ------- | --------- |
| `ruff check tests/test_banco.py` (com cache) | `All checks passed` |
| `ruff check --no-cache tests/test_banco.py` | `Found 1 error` |

**A regra:** no passo 4, sempre `ruff check --fix --no-cache .`. O CI nunca tem cache — se voce
confiar no cache local, ele descobre por voce, tarde.

### ⛔ Lint do CI roda em Linux; o Windows nao ve tudo

Descoberto em 2026-09-12. O CI continuou **vermelho** depois do conserto do `I001`, e a causa era
um segundo erro que **nunca apareceu na maquina local**:

```
EXE001 Shebang is present but file is not executable
 --> scripts/verify.py:1:1
```

**Por que nao aparece no Windows.** O `EXE001` le o **bit de execucao** do arquivo. Isso e metadado
de sistema de arquivos POSIX; no Windows ele nao existe, entao o `ruff` pula a regra em silencio.
Mesmo commit, mesma versao do `ruff` (0.16.7), mesmo `--no-cache`:

| Onde | `ruff check .` |
| ---- | -------------- |
| Windows (juicey), checkout limpo | `All checks passed` |
| Linux (CI), mesmo commit | `EXE001`, exit 1 |

**Esta e uma classe nova, pior que a do cache.** O `--no-cache` conserta um verde velho; aqui nao
existe comando local que revele o problema. O unico detector e o proprio CI.

**O conserto escolhido: tirar o shebang, nao marcar o bit.** Marcar (`git update-index --chmod=+x`)
tambem fecha o `EXE001`, mas exige lembrar do comando em **todo script novo** — passo manual,
invisivel no Windows, e que o modelo local **nao consegue expressar** num `SEARCH/REPLACE` (ele
edita conteudo, nao permissao). Tirar o shebang faz os dois ambientes concordarem sempre.

**A regra:** neste projeto, **script `.py` nao leva shebang**. Nada e executado direto — o kit, o
`test-cmd` do Aider e a documentacao chamam todos `python scripts/verify.py`. Se algum dia um
arquivo precisar mesmo ser executavel, marque o bit no git **e** anote aqui, porque o lint local
nunca vai cobrar.

**Corolario para ler o CI:** um email do GitHub Actions dizendo *"N annotations"* pode ser N erros
de lint de verdade. Em 2026-09-08 foram lidos como "erro + resumo"; eram **dois erros** (`EXE001` e
`I001`), e so um foi consertado. Va no log do job antes de concluir.

## Por que isso e suficiente aqui

E o nucleo `parser` e um componente onde teste basta: entrada = XML, saida =
linhas no SQLite e um JSON de contadores. Nao ha UI, nao ha rede, nao ha
concorrencia. Tudo o que a spec 01 §5 exige e verificavel com fixtures fixas.

## Buracos conhecidos

A pergunta honesta: **o que poderia estar quebrado e mesmo assim passar?**

| O que o verify NAO pega | Por que aceitamos, por enquanto |
| ----------------------- | ------------------------------- |
| **Comportamento sem teste.** `pytest` so verifica o que alguem escreveu | E o passo 2 do loop que fecha isso: os testes vem da spec e sao **commitados antes** da implementacao. O buraco vira "spec incompleta", que e visivel |
| **Dado pessoal real numa fixture.** Nenhum comando distingue um CNPJ real de um fake | Repo publico: risco alto. Defesa = `.gitignore` (`*.xml` fora de `tests/fixtures/`) + revisao humana no passo 4. **Nao delegar ao modelo local** |
| **Lint.** O `ruff` nao roda mais aqui | ⭐ **O buraco mais importante desta tabela.** Codigo pode passar no verify e reprovar no CI. Quem fecha e o **passo 4**: a revisao roda `ruff check --fix --no-cache` antes de aceitar o diff. ⚠️ O `--no-cache` nao e opcional — ver a secao acima |
| **Erros de tipo.** Sem `mypy`/`pyright` | O projeto nao adotou type checker; adicionar um agora mudaria o CI, que esta fora do escopo do shakedown |
| **Cobertura.** Um teste vazio passa | Sem `--cov` nem minimo exigido; a rubrica de qualidade do passo 4 e quem olha |
| **Python 3.14 local × 3.11 no CI** | A juicey so tem 3.14. Codigo que dependa de detalhe de 3.14 passa aqui e quebra no CI. Aceito: o shakedown mede o modelo local, nao a matriz de versoes |
| **Regras de lint que dependem de POSIX** | O `EXE001` le o bit de execucao, que nao existe no Windows. O `ruff` pula em silencio aqui e reprova no CI. Nao ha comando local que detecte; so o CI |
| **Performance.** Lote grande pode ficar lento | Fora do §5 da spec. Nenhum criterio de aceitacao fala de tempo |

> ⚠️ **Um teste fraco nao falha ruidosamente — ele aprova codigo errado em
> silencio.** Medido na Fase 0: um teste de idempotencia que conferia so
> `COUNT(*)` teria aprovado uma implementacao que sobrescrevia os valores.
> Buraco conhecido e registrado e muito melhor que buraco descoberto depois.

## Estado do portao

- [x] `python scripts/verify.py` roda e **PASSA** num checkout limpo
      *(invariante 2 do kit: o bootstrap nao termina sem isso)*
      — verde em 2026-09-08: `verify: OK -- 1 passo(s), tudo verde.` (8 testes)

# Verificacao — o que o `verify` checa NESTE projeto, e por que

> ★ Este arquivo existe porque o `scripts/verify.py` e o **juiz** de toda a
> arquitetura: o modelo local itera ate ele passar, e o diff e aceito porque
> ele passou. Quem le so o codigo do verify ve O QUE ele roda; este arquivo
> registra POR QUE aquilo e suficiente para dizer "esta bom".

## O que o `verify` roda

Em ordem, abortando no primeiro que falhar:

| # | Comando | Para que |
| - | ------- | -------- |
| 1 | `{sys.executable} -m pytest -q` | a suite. E o contrato das invariantes do §5 da spec 01 |
| 2 | `{sys.executable} -m ruff check .` | lint, `line-length = 100` |

**Por que `sys.executable` e nao a string `"python"`.** `"python"` seria
resolvido pelo PATH. Com a `.venv` nao ativada, isso e o Python global da
juicey — que **nao tem pytest**. O oraculo reprovaria todo diff com
"No module named pytest", e a culpa pareceria ser do modelo local. Foi um
defeito real do kit, encontrado neste shakedown e corrigido na fonte.

**Por que testes ANTES do lint.** O verify aborta no primeiro passo vermelho, e
o Aider so tem **3 reflexoes**. Nesta ordem, as 3 tentativas sao gastas em
corretude; na ordem inversa, uma virgula fora do lugar bloquearia o modelo de
sequer ver o resultado dos testes.

## Por que isso e suficiente aqui

O `verify` **espelha o CI** (`.github/workflows/ci.yml`, que roda `ruff check .`
e `pytest`). Essa igualdade e a propriedade que importa: um oraculo mais fraco
que o CI deixaria o modelo local produzir codigo aprovado localmente e
reprovado no CI — e a reprovacao chegaria **depois** de o diff ja ter sido
aceito no passo 4 do loop.

E o nucleo `parser` e um componente onde teste basta: entrada = XML, saida =
linhas no SQLite e um JSON de contadores. Nao ha UI, nao ha rede, nao ha
concorrencia. Tudo o que a spec 01 §5 exige e verificavel com fixtures fixas.

## Buracos conhecidos

A pergunta honesta: **o que poderia estar quebrado e mesmo assim passar?**

| O que o verify NAO pega | Por que aceitamos, por enquanto |
| ----------------------- | ------------------------------- |
| **Comportamento sem teste.** `pytest` so verifica o que alguem escreveu | E o passo 2 do loop que fecha isso: os testes vem da spec e sao **commitados antes** da implementacao. O buraco vira "spec incompleta", que e visivel |
| **Dado pessoal real numa fixture.** Nenhum comando distingue um CNPJ real de um fake | Repo publico: risco alto. Defesa = `.gitignore` (`*.xml` fora de `tests/fixtures/`) + revisao humana no passo 4. **Nao delegar ao modelo local** |
| **Erros de tipo.** Sem `mypy`/`pyright` | O projeto nao adotou type checker; adicionar um agora mudaria o CI, que esta fora do escopo do shakedown |
| **Cobertura.** Um teste vazio passa | Sem `--cov` nem minimo exigido; a rubrica de qualidade do passo 4 e quem olha |
| **Python 3.14 local × 3.11 no CI** | A juicey so tem 3.14. Codigo que dependa de detalhe de 3.14 passa aqui e quebra no CI. Aceito: o shakedown mede o modelo local, nao a matriz de versoes |
| **Performance.** Lote grande pode ficar lento | Fora do §5 da spec. Nenhum criterio de aceitacao fala de tempo |

> ⚠️ **Um teste fraco nao falha ruidosamente — ele aprova codigo errado em
> silencio.** Medido na Fase 0: um teste de idempotencia que conferia so
> `COUNT(*)` teria aprovado uma implementacao que sobrescrevia os valores.
> Buraco conhecido e registrado e muito melhor que buraco descoberto depois.

## Estado do portao

- [x] `python scripts/verify.py` roda e **PASSA** num checkout limpo
      *(invariante 2 do kit: o bootstrap nao termina sem isso)*
      — verde em 2026-09-08: `verify: OK -- 2 passo(s), tudo verde.`

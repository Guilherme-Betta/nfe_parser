# CLAUDE.md — NF-e Despesas (`nfe_parser`)

> **Este arquivo e um ROTEADOR, nao um manual.** Ele diz onde as coisas estao;
> nao repete o conteudo delas. Alvo: menos de ~200 linhas, so ponteiros.
>
> Razao: tudo aqui entra no contexto de TODA sessao. Um CLAUDE.md gordo cobra
> pedagio em cada turno, e a informacao duplicada envelhece em dois lugares ao
> mesmo tempo — o pior tipo de documentacao errada, a que parece certa.

## O que e este projeto

Ferramenta self-hosted que le XMLs de NF-e/NFC-e e mostra as despesas do
proprio dono **item a item**, com classificacao automatica e orcamento.
So despesas, so BRL, sem lancamento manual.

> ⚠️ **Repositorio publico.** Nunca commitar nota fiscal real: sem CPF, CNPJ,
> nome ou chave de verdade. So fixtures **anonimizadas** em `tests/fixtures/`.

## Onde as coisas estao

| Preciso de... | Vai em |
| ------------- | ------ |
| stack, versoes, dependencias | `steering/stack.md` |
| convencoes de nome, estilo e commit | `steering/convencoes.md` |
| o que o `verify` checa, e o que ele deixa passar | `steering/verificacao.md` |
| o contrato de cada componente (fonte da verdade) | `specs/0N_spec_*.md` (01 a 06) |
| como os nucleos 01 e 02 foram fatiados e decididos | `specs/NNN-nome/` (stories 001 a 013) |
| o porque das decisoes originais (fotos antigas) | `docs/historico/` |
| como o codigo era escrito ate 2026-10-14 | `docs/historico/experimento-modelo-local/` |

## Como o trabalho e feito

Desde 2026-10-14 o codigo e escrito com o Claude, direto. O modelo local
(Ollama + Aider) que implementou as stories 001–013 nao e mais usado.

| # | Passo |
| - | ----- |
| 1 | criterios de aceitacao **testaveis** na spec (nova, ou ajuste de uma 01–06) |
| 2 | os **testes**, a partir dos criterios — provados VERMELHOS no codigo atual, pelo motivo certo |
| 3 | a implementacao, ate o `verify` ficar verde |
| 4 | a revisao do diff |

⚠️ **Teste antes da implementacao nao e estilo, e defesa.** Teste escrito depois
tende a confirmar o que o codigo ja faz, inclusive o erro. Se uma mudanca
precisa alterar um teste existente, o commit diz por que — e a alteracao ou e so
de forma (nome, import), ou e uma mudanca de contrato declarada.

⚠️ Os cabecalhos dos testes das stories 001–013 dizem que "o modelo local recebe
este arquivo como LEITURA (`--read`)". E registro de como cada teste foi
produzido, nao o workflow atual.

## Regras que nao se negociam neste repo

1. **`verify` verde antes de todo commit.** Ele roda o mesmo que o CI, mais o
   formato.
2. **A `main` so recebe trabalho por decisao explicita do Gui.** Um merge
   publicado so se desfaz com `push --force`.
3. **Dependencia nova so com decisao do Gui** — ver `steering/stack.md`.

## Comandos

```bash
python scripts/verify.py     # pytest + ruff check + ruff format --check. 0 = tudo verde
```

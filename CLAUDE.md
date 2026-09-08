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
| convencoes de nome e estilo | `steering/convencoes.md` |
| o que o `verify` checa, e por que | `steering/verificacao.md` |
| o contrato de cada feature | `specs/NNN-nome/spec.md` |
| o backlog fatiado da feature | `specs/NNN-nome/plan.md` |

## O workflow deste projeto — loop de 4 passos

O codigo e escrito por um **modelo local** (Ollama + Aider), com o Claude no
papel de Scrum Master. Kit completo em `claude-scrum-kit/`.

| # | Passo | Quem |
| - | ----- | ---- |
| 1 | `spec.md` com criterios de aceitacao **testaveis** | Claude |
| 2 | escrever os **testes** a partir dos criterios, e **commitar** | Claude |
| 3 | implementar ate os testes passarem, em loop | **modelo local** |
| 4 | revisar o diff acumulado, que ja passa nos testes | Claude |

⚠️ **A ordem do passo 2 nao e estilo, e defesa.** Os testes sao congelados por
commit ANTES de a implementacao existir, e entram no Aider via `--read` (le,
nao edita). Se o modelo puder editar o teste, ele edita o teste para faze-lo
passar — e o caminho mais curto para o objetivo dado.

## Regras que nao se negociam neste repo

1. **O Aider nunca roda na `main`**, nunca com working tree sujo, e nunca no
   diretorio de trabalho normal — sempre em clone descartavel ou `worktree`.
2. **Tarefa que nao cabe em ~300 linhas de codigo relevante e quebrada** antes
   de ir ao modelo local. O orcamento e 8192 tokens, e nao ha alarme quando
   estoura: o Ollama trunca em silencio.
3. **`/clear` entre tarefas.** Nao e recomendacao — tres turnos ja estouram os
   8k, e o estouro nao aparece em lugar nenhum.
4. **Um pedido, um defeito.** Dois defeitos no mesmo pedido fazem o modelo
   emitir blocos sobrepostos e corromper o arquivo.

## Comandos

```bash
python scripts/verify.py     # o oraculo. 0 = tudo verde
```

# O experimento com o modelo local (setembro–outubro de 2026)

> **Foto antiga, nao atualizada.** Nada aqui e usado pelo projeto hoje. Fica como registro de como
> as stories 001–013 foram construidas.

## O que foi

As 13 primeiras stories (`specs/001-*` … `specs/013-*`) foram implementadas por um **modelo local**
(`qwen2.5-coder:14b`, via Ollama + Aider), com o Claude no papel de Scrum Master, num loop de 4
passos:

| # | Passo | Quem |
| - | ----- | ---- |
| 1 | `spec.md` com criterios de aceitacao testaveis | Claude |
| 2 | os testes, escritos a partir dos criterios e commitados ANTES da implementacao | Claude |
| 3 | a implementacao, em loop ate os testes passarem | modelo local |
| 4 | a revisao do diff acumulado | Claude |

O modelo recebia os testes por `--read`, sem poder edita-los. E por isso que os cabecalhos dos
arquivos de `tests/` dizem "o modelo local recebe este arquivo como LEITURA": isso descreve como
cada teste foi produzido, e nao o workflow atual.

## Por que acabou

Em 2026-10-14, depois de uma revisao geral do branch `scrum`, o dono do projeto deixou de usar o
modelo local. A revisao mostrou que varias escolhas de estrutura do codigo vieram das restricoes do
modelo, e nao de decisoes de design:

- a janela de **8192 tokens** obrigava a fatiar toda tarefa em ate ~300 linhas;
- o formato de edicao `diff` do Aider nao conseguia expressar uma correcao so de espaco em branco,
  e por isso o `ruff` saiu do `verify` em 2026-09-08 (a story 001 queimou as tres reflexoes do
  Aider numa linha em branco);
- o degrau do LLM foi para um modulo proprio (`classificacao_llm.py`) porque editar
  `categorizacao.py` nao cabia na janela;
- cada arquivo de teste era autocontido para caber num `--read`, e por isso a mesma fixture
  aparecia copiada em 34 arquivos.

Essas cicatrizes foram desfeitas no branch `refatoracao` (passos 3 a 7).

## O que esta nesta pasta

| Arquivo | Era |
| ------- | --- |
| `rodar_passo3.py` | o orquestrador do passo 3: lia `specs/NNN/tarefas.json` e invocava o Aider tarefa a tarefa, sem ninguem no teclado. Morava em `scripts/` |
| `aider.conf.yml` | a config do Aider (`.aider.conf.yml` na raiz). Sem o ponto no nome, de proposito: assim nenhum Aider rodado aqui a carrega |
| `aider.model.settings.yml` | o `num_ctx: 8192` repassado ao Ollama — sem ele o orcamento de 8k nao tinha lastro |

Os registros de cada story continuam onde nasceram, porque as specs os referenciam:
`specs/NNN-*/plan.md`, `tarefas.json`, `tarefas/` e `passo3-registro.md`.

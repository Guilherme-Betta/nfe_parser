# Retomada: nfe_parser

Atualizado: 2026-10-31 · `main` = 230c485 (PR #10) · verify verde (682 testes) · tag mais recente: v0.3.1 (em 7647e4e)

Serve para uma sessão nova do Claude (Claude Code no PC ou na nuvem) começar sem esta
conversa. Reescrever a cada encerramento; não empilhar marcos.

## Onde estamos

Os seis componentes das specs 01–06 estão implementados. Entre 2026-10-25 e 2026-10-31
entraram cinco PRs pequenos, todos mergeados na `main`:

| PR | Branch | O quê |
| -- | ------ | ----- |
| #6 | `filtro-loja-mesmo-nome` | seletor de loja em `/relatorios` desambigua nomes repetidos com o fim do CNPJ (spec 05 §5) |
| #7 | `notas-celular-situacao` | em `/notas` até 480 px, a situação vai para baixo da data e a coluna Modelo some (spec 03 §5) |
| #8 | `xsdata-e-classificador` | `xsdata` declarado no `pyproject.toml`; `classificador.py` → `tipo_xml.py`, `classificar_xml` → `tipo_do_xml` |
| #9 | `emit-cnpj-documentado` | `emit_cnpj` **não** é renomeada; DDL e spec 03 dizem que guarda CNPJ ou CPF |
| #10 | `vocabulario-strenum` | `vocabulario.py` com cinco `StrEnum`; regra em `steering/convencoes.md`; `test_vocabulario.py` confere enum × CHECK |

Nada em andamento. Os branches remotos desses PRs podem ser apagados.

## Próximo passo

Não há próximo passo decidido. Opções levantadas em 2026-10-31, para o Gui escolher:

1. **Auditoria de celular** (sem decisão de produto): subir o app com banco semeado, tirar
   prints headless de todas as telas em 390 px (claro e escuro) e listar o que quebra, como
   a coluna Situação quebrava. Depois o Gui escolhe o que corrigir. Como fazer: ver
   "Armadilhas e macetes" abaixo (Chromium + Playwright).
2. **Comparativo planejado × real** (roadmap da spec 04): na tela de orçamento, o gasto
   real do mês ao lado do limite, por categoria. Exige 2 ou 3 decisões de tela do Gui.
3. **Orçamento por subcategoria** (roadmap na spec 04 §1; regra atual em §2): hoje o limite só vale para
   categoria de nível 1. Exige decisão sobre o rollup mãe/filha.

Itens de roadmap maiores (README, "Fora do MVP"): comparativo planejado×real, visões
salvas, download via SEFAZ, scan de QR, terceiro nível na taxonomia.

## Ler antes de começar

- `CLAUDE.md` (roteador) e `docs/decisoes.md` (cartão da visão + log; ler antes de
  qualquer decisão de produto). As últimas linhas do log são as decisões de 2026-10-25
  e 2026-10-31.
- `steering/convencoes.md`: idioma, estilo, e a regra nova dos `StrEnum`.
- Para a opção 1: `specs/03_spec_ingestao_web_ui.md` §5 e `specs/05_spec_visualizacao.md` §5.
- Para as opções 2 e 3: `specs/04_spec_orcamento.md`.

## Pendências do Gui

- **Tag de versão** no PC (sugestão: v0.4.0 — há mudança de tela e rename de módulo).
  A nuvem não consegue empurrar tag.
- **Conferir `/notas` no celular de verdade** (PR #7 foi conferido só por print headless).
- Apagar os branches remotos já mergeados, se quiser o repo limpo.
- Escolher o próximo passo entre as opções acima.

## Modo de trabalho (dito pelo Gui)

- Gui é iniciante; explicar o porquê (ver `~/.claude/CLAUDE.md` dele, se existir).
- Nas últimas sessões escolheu **modo execução**: explicação curta do que mudou e por
  quê; parar só para decisão de produto, dependência nova e fim do trabalho. Em trabalho
  novo, perguntar o modo uma vez no começo.
- Decisões de produto pela skill `decisoes-com-mockup` (múltipla escolha, mockup ASCII);
  registrar cada uma em `docs/decisoes.md` com a coluna "Quem".
- Um branch novo por trabalho, a partir da `main`, nome em português com hífens. O Gui
  cria e mergeia o PR; a sessão entrega o texto da descrição pronto para colar. Nunca
  mergear pela API. Na nuvem: push só do branch; tag só no PC.

## Armadilhas e macetes

**Aprendidos em 2026-10-25/31:**

- **Branches paralelos conflitam em `docs/decisoes.md`**: todos acrescentam linha no fim da
  mesma tabela. Fazer um trabalho por vez, ou o segundo branch em cima do primeiro, e
  criar o PR do segundo só depois do merge do primeiro.
- **`python scripts/verify.py | tail` esconde o código de saída** (o `tail` devolve 0).
  Rodar `python scripts/verify.py > log 2>&1; echo $?` e só commitar com 0.
- **`pkill -f "uvicorn.*8011"` mata o próprio shell** (o padrão casa com a linha de comando).
  Subir com `& echo $! > pidfile` e matar pelo PID.
- **Na nuvem há Chromium + Playwright** (`require('playwright')` em Node): dá para tirar
  print headless das telas (390 px e 1280 px) e medir `scrollWidth` da tabela. Não
  substitui a conferência no aparelho, mas pegou a data quebrando em duas linhas.
- **Push recusado com 403 "Claude doesn't have GitHub access"**: não é rede; o Gui
  reconecta o GitHub em https://claude.ai/connect-github e, se faltar, instala o app
  Claude no repositório. Enquanto isso, `git format-patch origin/main..branch` gera
  patches que entram no PC com `git am`.
- Mudar a ordem das colunas num `CREATE TABLE` só para encaixar comentário é desnecessário
  e arriscado (bancos antigos têm a ordem original): comentar sem reordenar.

**Já conhecidos (da memória local do Gui; aqui para a nuvem também saber):**

- `pytest` com arquivos de `tests/` e `tests/web/` no MESMO comando dá "fixture 'cliente'
  not found", que é falso. Rodar separado, ou o verify inteiro.
- Subir o app sem LLM: NÃO definir `OLLAMA_URL` (com ela, `OLLAMA_MODELO` e `LLM_LIMIAR`
  viram obrigatórias). Simular LLM fora do ar: `OLLAMA_URL=http://127.0.0.1:9`.
- App de pé para olhar: semear banco temporário com `tests/apoio.py` via `TestClient`
  (`enviar`, `variante`, `chave(n)`, `evento`) e subir o uvicorn numa porta 801x; antes,
  conferir se não ficou um uvicorn velho na porta (serve código antigo com template novo,
  dá 500).
- Eventos são lidos pelo binding GENÉRICO do nfelib (`nfe_evento_generico`): o binding de
  cancelamento recusa a carta de correção real (`xCorrecao`).
- Migração que muda um CHECK no SQLite = reconstruir a tabela dentro da transação do
  executor; nunca `executescript` numa migração.
- Não importar pacote transitivo direto: usar o que o `pyproject.toml` declara
  (`xsdata` agora está declarado).
- Cancelamento órfão importado antes da v5 nunca foi guardado: só reimportar o XML resolve.

## Estado deixado

Nada não publicado. Nenhum servidor rodando. Branches locais da sessão na nuvem são
descartáveis (tudo está na `main`).

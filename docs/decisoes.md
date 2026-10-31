# Decisões

Registro curto de decisões de produto: uma linha por decisão, com a base. O **contrato** continua
nas specs (`specs/0N_spec_*.md`); este arquivo diz *quem decidiu, quando e com base em quê*, para
ninguém perguntar de novo o que já foi respondido.

## Cartão da visão

Os princípios que decidem coisas. Fonte: `docs/historico/report_projeto_nfe.md` (o report) e o
`CLAUDE.md`.

- **Movido por nota fiscal:** os gastos vêm dos XMLs, sem lançamento manual (report §2).
- **O diferencial é o item:** granularidade produto a produto, que a NF-e carrega (report §0).
- **Honestidade:** onde a confiabilidade é *best-effort*, o app mostra; não finge precisão (report §1).
- **A mão manda:** decisão humana nunca é sobrescrita pela automação (report §5; spec 02 §4).
- **A base funciona sem LLM:** memória → NCM → bucket; o LLM é opcional, e criar categoria fica sob revisão do Gui (report §5).
- **Arquivo com problema não derruba o lote:** é marcado e o lote segue (CF-e/SAT, report §2;
  spec 01 §6.2). Falha de gravação, ao contrário, desfaz o lote inteiro.
- **Escopo do MVP:** single-user, self-hosted, PT-BR, só despesas, só BRL (report §1–§2).
- **Validado no uso pessoal do Gui** antes de pensar em outros usuários (report §0).
- **Repositório público:** nunca dado real no repo; fixtures anonimizadas (`CLAUDE.md`).
- **Referência de produto:** orçamento inspirado no Cashew (report §6). Não há app de referência
  para as outras telas.

## Log

| Data | Decisão | Quem | Base | Confiança |
| ---- | ------- | ---- | ---- | --------- |
| 2026-10-16 | NF-e de emitente com CPF: o CPF faz o papel de "loja" na identidade por texto (opção c da spec 01 §6.3) | Gui | conversa | — |
| 2026-10-16 | O CPF vai na mesma coluna do CNPJ (`emit_cnpj` = documento do emitente: CNPJ de 14 dígitos ou CPF de 11). Os dois nunca colidem, e filtro, relatórios e rótulos passam a funcionar sem mudança. Renomear a coluna fica como limpeza opcional | Claude | técnica | alta |
| 2026-10-16 | O CPF já estava no banco dentro do `xml_raw`; a opção c não cria exposição nova | Claude | fato do código | alta |
| 2026-10-16 | Revisão: "Não Classificado" passa a ser destino manual, e o produto devolvido fica na fila sem a automação (NCM/LLM) mexer nele (opção B) | Gui | conversa | — |
| 2026-10-16 | A opção B é implementada como `origem='manual'` no bucket, sem valor novo de `origem` e sem migração. A cascata já pula `manual`; a fila passa a ser "`origem` NULL **ou** no bucket" | Claude | técnica | alta |
| 2026-10-16 | O seletor da revisão nunca vem com "Não Classificado" pré-selecionado: um "Salvar" sem escolher não devolve o produto à fila por acidente | Claude | bom senso | alta |
| 2026-10-16 | `LLM_LIMIAR` fora de 0..1 é recusado na subida do app, com mensagem (spec 02 §7.3 item 4) | Claude | convenção: configuração inválida falha cedo | alta |
| 2026-10-16 | ~~Apagar categoria manda os produtos para a fila com `origem` NULL~~ — substituída pela decisão do Gui de 2026-10-16 abaixo (rodada 02) | Claude | estado atual | média |
| 2026-10-16 | Devolver à fila fica **no próprio seletor**: "↩ Não Classificado (voltar à fila)" é a 1ª opção, só para produto fora da fila; na fila, o devolvido leva o selo "devolvido por você" | Gui | rodada 01 (`docs/mockups/rodada-01-devolver-a-fila.html`) | — |
| 2026-10-16 | Produto do LLM é revisitado: se uma âncora NCM passar a cobri-lo, **o NCM vence**, como se o produto chegasse hoje (spec 02 §7.3 item 2) | Gui | rodada 01 | — |
| 2026-10-16 | `cancelado_em` guarda a hora **do cancelamento** (`dhEvento` do XML), não a da importação (spec 01 §6.3 item 2) | Gui | rodada 01 | — |
| 2026-10-16 | Rascunhos de 01 §6 e 02 §7: o Gui **lê antes de aprovar** — continuam marcados como rascunho | Gui | rodada 01 | — |
| 2026-10-16 | Apagar **subcategoria**: os produtos sobem para a categoria-mãe na hora, mantendo quem decidiu (`manual` continua `manual`); as âncoras NCM dela passam a apontar para a mãe. Apagar categoria de nível 1 continua mandando para a fila | Gui | rodada 02 | — |
| 2026-10-16 | Carta de correção (e todo evento): o XML é **guardado**, e a tela da nota mostra a data e o texto da correção. Motivo do Gui: coerência com o `xml_raw` das notas e não perder a informação se o arquivo original sumir | Gui | rodada 02 | — |
| 2026-10-16 | LLM fora do ar ao clicar "Sugerir com o LLM": aviso na própria tela de revisão, nada gravado (antes: erro 500) | Gui | rodada 02 | — |
| 2026-10-16 | Rascunhos de 01 §6 e 02 §7 **aprovados** como contrato, com as respostas da rodada 02 | Gui | rodada 02 | — |
| 2026-10-17 | Cancelamento que chegou num lote **anterior** ao da nota (guardado em `eventos` desde a v5) é aplicado quando a nota chega; `cancelado_em` = `dhEvento` do evento guardado | Claude | spec 01 §5 ("inclusive com evento antes da nota") e §6.2 | alta |
| 2026-10-17 | A linha da nota no log continua `nova` (é uma nota nova); o `detalhe` diz que ela entrou cancelada e em que importação o cancelamento chegou | Gui | conversa (confirmou a escolha do Claude) | — |
| 2026-10-17 | O cartão "cancelamentos" do lote não conta esse caso: ele conta arquivos de cancelamento, e os contadores saem do log | Gui | conversa (confirmou a escolha do Claude) | — |
| 2026-10-17 | A linha "cancelamento órfão" da importação antiga fica como está: o log registra o desfecho daquele lote | Claude | bom senso: log é histórico | alta |
| 2026-10-17 | Banco que já tem nota `ok` com cancelamento guardado (v0.3.0) é corrigido uma vez, pela migração v6 | Claude | spec 01 §5; nota cancelada não conta como gasto | alta |
| 2026-10-17 | Órfão importado antes da v5 não foi guardado: não há o que aplicar sozinho. Reimportar o XML do evento resolve (o evento aplica em nota de lote anterior) | Claude | fato do código | alta |
| 2026-10-25 | Seletor de loja em `/relatorios`: lojas de mesmo nome ganham o fim do CNPJ (`NOME · …123456`), a mesma regra que a spec 05 §5 ja fixou para o grafico. Loja de nome unico continua so com o nome | Claude | spec 05 §5 (regra existente, estendida ao filtro) | alta |
| 2026-10-25 | Lista de notas no celular (até 480 px): a situação (válida/cancelada) vai para baixo da data, na 1ª coluna, e a coluna Modelo some; nada rola para o lado. Em tela larga, a tabela continua igual. Alternativas descartadas: esconder Modelo e Itens; virar cartões | Gui | rodada 03 (mockup ASCII na conversa) | — |

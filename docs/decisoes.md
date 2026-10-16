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
| 2026-10-16 | Apagar categoria manda os produtos dela para a fila com `origem` NULL, inclusive os que eram `manual`; a automação tenta de novo antes de sobrar para o Gui (comportamento atual, spec 02 §7.2) | Claude | estado atual | média |
| 2026-10-16 | Devolver à fila fica **no próprio seletor**: "↩ Não Classificado (voltar à fila)" é a 1ª opção, só para produto fora da fila; na fila, o devolvido leva o selo "devolvido por você" | Gui | rodada 01 (`docs/mockups/rodada-01-devolver-a-fila.html`) | — |
| 2026-10-16 | Produto do LLM é revisitado: se uma âncora NCM passar a cobri-lo, **o NCM vence**, como se o produto chegasse hoje (spec 02 §7.3 item 2) | Gui | rodada 01 | — |
| 2026-10-16 | `cancelado_em` guarda a hora **do cancelamento** (`dhEvento` do XML), não a da importação (spec 01 §6.3 item 2) | Gui | rodada 01 | — |
| 2026-10-16 | Rascunhos de 01 §6 e 02 §7: o Gui **lê antes de aprovar** — continuam marcados como rascunho | Gui | rodada 01 | — |

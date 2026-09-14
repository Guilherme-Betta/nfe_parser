# Passo 3 — registro automatico — 006-saida-json

Rodado em 2026-09-14 16:09 por `scripts/rodar_passo3.py`.

- **Tarefas verdes:** 3 de 3
- **Invocacoes do Aider:** 4
- **Commits do modelo local:** 8
- **Tempo total no passo 3:** 3.8 min
- **CONTEXT do Ollama:** 8192

| # | Tarefa | Verde? | Invocacoes | Tempo | Commits | Quem resolveu |
| - | ------ | ------ | ---------- | ----- | ------- | ------------- |
| 1 | de_centavos formata centavos como string decimal usando so aritmetica de inteiro | ✅ | 1 | 22.1s | 2 | 🤖 **modelo local**, de primeira |
| 2 | nota_para_json devolve a nota como string JSON, e None para chave inexistente | ✅ | 2 | 158.3s | 4 | 🤖 **modelo local**, na 2a tentativa — ver nota abaixo |
| 3 | a saida ganha a chave itens, ordenada por n_item e vazia quando nao ha item | ✅ | 1 | 48.3s | 2 | 🤖 **modelo local**, de primeira |

> ⚠️ A coluna **Quem resolveu** NAO e preenchivel por script. Marque a mao:
> 🤖 modelo local · 👤 Claude ditou o codigo · 🤝 misto. Sem ela, "N/N tarefas verdes" e "N/N resolvidas pelo modelo local" viram a mesma linha — e na medicao 5 nao eram (Achado M).

---

## ⚠️ Tres ressalvas que este registro automatico nao sabe registrar

**1. A tarefa 2 conta 2 invocacoes e 4 commits, mas a primeira tentativa foi REVERTIDA.**
Os commits `d31a198`, `898cfa0` e `46791d0`, listados abaixo, nao estao no codigo final. O
acumulo entre retomadas funciona como projetado (conserto de `17063b2`), mas ele soma tentativa
descartada com tentativa aproveitada. **Custo honesto da tarefa 2: 1 reversao + 1 re-especificacao.**

**2. Uma das duas falhas que pararam a tarefa 2 era do ORACULO, nao do modelo local.**
`test_o_acento_sobrevive_a_ida_e_a_volta` foi escrito com `assert "\u00e3" not in bruto` numa
string Python comum, onde a sequencia JA E o caractere -- a linha de cima exigia o acento presente
e a de baixo o proibia. **Nenhuma implementacao passaria.** O modelo local gastou as tres reflexoes
contra uma assercao insatisfazivel, e e plausivel que os remendos defensivos da outra falha tenham
nascido dai. O defeito real dele foi um so: uma conversao de data inventada que apagava
`cancelado_em`.

**3. 🔴 O "3/3 verdes" acima foi um FALSO VERDE por 3 minutos — e isso e achado do KIT, nao da story.**
O `rodar_passo3.py` roda so o modulo de teste da tarefa corrente. A tarefa 3 acrescentou a chave
`itens` a saida e quebrou `test_as_chaves_sao_exatamente_estas_e_nesta_ordem`, do modulo da tarefa
2 -- e ficou verde assim mesmo, porque aquele modulo nunca foi reexecutado. A suite completa so foi
rodar no P4, onde a falha apareceu.

> ⭐ **A story se salvou por acaso:** o modulo da tarefa 3 tinha um teste de regressao das 14 chaves
> da nota, escrito de proposito contra o risco R5 do `plan.md`. Sem ele, a quebra teria chegado ao
> P4 sem nenhum sinal no P3.
>
> O defeito de fundo era do oraculo (igualdade estrita onde a spec previa a saida crescer), mas o
> ponto que sobrevive a esta story e outro: **um passo 3 que nunca roda a suite inteira nao pode
> afirmar "N/N verdes".**

---

## Commits brutos do modelo local

Registrados aqui porque a transferencia para o repo oficial usa historico curado.
Esta e a evidencia do que o modelo local produziu, tarefa a tarefa — o `git log`
do repo oficial nao a tem mais, e o clone do shakedown e descartavel.

**Tarefa 1 — de_centavos formata centavos como string decimal usando so aritmetica de inteiro**

- `e22e9a1 feat: Adiciona função `de_centavos` para converter centavos em representação decimal`
- `191eee7 feat: adicionar módulo de serialização para NFe`

**Tarefa 2 — nota_para_json devolve a nota como string JSON, e None para chave inexistente**

- `46791d0 fix: importa módulo datetime para resolver erro F821`
- `898cfa0 fix: Corrigir ordem das chaves e tratamento de data no JSON`
- `d31a198 feat: Adiciona função `nota_para_json` para serializar notas em JSON`
- `e6cbbf5 feat: Adiciona função `nota_para_json` para serializar notas em JSON`

**Tarefa 3 — a saida ganha a chave itens, ordenada por n_item e vazia quando nao ha item**

- `1561540 fix: Corrigir ordem e chaves dos itens no JSON gerado`
- `bdaaa77 feat: incluir itens da nota na saída da função `nota_para_json``


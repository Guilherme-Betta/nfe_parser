# Revisão do seed — o que precisa da sua decisão

> 📋 O arquivo é [`src/nfe_parser/dados/taxonomia_seed.json`](../../src/nfe_parser/dados/taxonomia_seed.json).
> ⭐ Ele já passa por 8 testes de coerência estrutural: slug repetido, `parent` fantasma, âncora
> órfã, prefixo de largura impossível e bucket ausente **acendem vermelho sozinhos**.
>
> ⛔ **O que os testes NÃO julgam é o que está abaixo:** se o mapeamento está *certo*. Isso é
> produto, e é seu.

---

## 1. A taxonomia: ✅ 11 pais + 32 subs + 1 bucket — o §5 do report, mais a chamada do Gui

⛔ **Nada foi removido nem renomeado, e os `nome` são cópia literal do report.** A única categoria
acrescentada é **`Vegetais`**, e foi chamada do Gui em 15/09 — ver o §3.

O resto do que foi inventado é a **chave interna** (`slug`), e em três lugares ela não sai direto do
nome:

| Nome no report | slug | Por quê |
| -------------- | ---- | ------- |
| `Eletrônicos` (a **sub**) | `eletronicos-eletronicos` | o pai também se chama `Eletrônicos`, e slug é `UNIQUE` |
| `Mercearia (secos/enlatados)` | `mercado-mercearia` | o parêntese foi cortado da chave, não do nome |
| `Farmácia (não-medicamento)` | `saude-farmacia` | idem |

⚠️ **O slug nunca aparece na tela** — quem aparece é o `nome`. Ele só precisa ser estável, porque é
por ele que renomear uma categoria continua sendo renomear, e não criar outra.

---

## 2. 🔴 Seis subcategorias ficaram SEM âncora NCM, e não é esquecimento

`Restaurante` · `Delivery` · `Lanche` · `Cafeteria` · `Faxina` · `Lavanderia`

São **serviços**. A nota do restaurante não traz um NCM que diga "isto é um jantar" — quem
identifica é o **emitente**, não o item. ⛔ Nenhum mapa NCM alcança isso, por melhor que seja.

⭐ Quem resolve é o LLM (story 012) ou uma regra por CNPJ, que hoje não tem story. **Até lá, essas
seis caem no bucket** — e como produto no bucket é reprocessável, nada se perde.

📋 `Suplementos` também ficou sem âncora, mas por escolha: o NCM plausível (`2106`) é o mesmo de
molho, sopa e preparações em geral. ⭐ Errar para o bucket é reversível; errar para a categoria
errada é mudo.

---

## 3. ✅ As três correções que o Gui pediu em 15/09 — todas aplicadas

### 1. `Vegetais` virou categoria-pai, e `07` aponta para ela

⭐ **Proposta dele, e melhor que a minha.** `Legumes` e `Verduras` saíram de `Mercado` e viraram as
duas subcategorias de `Vegetais`, uma pai nova de **nível 1**.

⚠️ **Nível 1, e não sub-de-sub, de propósito:** três níveis quebrariam a premissa de que somar por
categoria-raiz é um pulo só de `parent_id`. A visualização (spec 05) pagaria essa conta depois.

⛔ **As exceções `0704` e `0705` foram embora também.** Eu as tinha aberto para couve e alface; se a
alocação entre Legumes e Verduras é do usuário, adivinhar metade dela é pior que não adivinhar
nenhuma. ⭐ O capítulo 07 inteiro cai em `Vegetais`, e a mão decide uma vez por produto.

📋 **Agora são 11 pais, 32 subs, 1 bucket — 44 categorias.** `Frutas` ficou em `Mercado`: `08` é
inequívoco, e não havia razão funcional para movê-la.

### 2. `2207` saiu do mapa, e o capítulo 22 foi desmontado

🔴 **A hipótese do isopropílico estava certa na química e errada no produto.** Isopropílico é
`2905.12` — capítulo 29, separável sem esforço. ⚠️ Mas o álcool de limpeza de supermercado é
**etílico hidratado** (46° ou 70° INPM), o mesmo capítulo 22 do etanol de posto. A diferença que
daria para explorar não existe no produto que se compra.

⭐ **Então a âncora `2207` foi removida**, e álcool — de limpeza ou de posto — cai no bucket. É a
regra que a spec já tinha: *errar para o bucket é reversível; errar para a categoria errada é mudo.*
📋 E custa **uma** classificação manual: a memória da 008 faz todo item futuro daquele produto
herdá-la.

⚠️ **O `22` genérico saiu junto, e isso consertou um defeito meu:** ele mandava **vinagre** (`2209`)
para `Bebidas`. No lugar entraram `2201`, `2202` e `2206` → `Bebidas`, e `2209` → `Mercearia`.

### 3. `8507` saiu — e a pergunta achou um limite do desenho

⛔ **Bateria de carro não é expressável neste mapa.** O conceito mora em `8507.10` — o degrau de
**6 dígitos** —, e as âncoras só aceitam 2, 4 ou 8, porque é isso que a busca consulta. ⭐ E os 8
dígitos não salvam: a bateria real sai como `8507.10.10` ou `.90`, e `85071000` não casa com
nenhuma.

📋 Pilha, power bank e bateria caem todos em `85` → `Eletrônicos`. Errado só para a bateria, e o erro
se paga com uma correção manual.

🔴 **Isto virou a dívida `j`**, e é a mais valiosa da lista: acrescentar o degrau de 6 dígitos é uma
linha na busca da 009, e destrava toda a curadoria futura do mapa.

---

## 3b. As três âncoras que continuam sendo chamada sua, e você já aprovou

| Prefixo | Vai para | A ressalva |
| ------- | -------- | ---------- |
| `34011100` | **Higiene** | sabonete de toucador; sem ela cairia em `Limpeza` pelo `34` |
| `30` | **Saúde** (o pai) | só `3004` → Medicamentos e `3005` → Farmácia descem; o resto fica genérico |
| `16`, `20`, `21` | **Mercearia** | atum enlatado vai para Mercearia, não para `Carnes e peixes` |

### ⭐ O que fazer com uma que você não gostar depois

📋 Não precisa de story nova nem de código: é **uma linha no JSON**, e rodar o carregador de novo.
⚠️ A única coisa que o arquivo **não** consegue fazer é *remover* um prefixo já carregado num banco —
isso é a 011.

---

## 4. O que já está provado, e ⛔ não precisa da sua revisão

| | |
| - | - |
| A taxonomia bate com o §5 do report | ✅ teste |
| Carregar duas vezes não duplica, e o `id` não muda | ✅ teste |
| Toda âncora aponta para categoria que existe | ✅ teste |
| Existe exatamente um bucket, e o slug é `uncategorized` | ✅ teste |
| ⭐ **Crescer o mapa NCM TIRA do bucket um produto que já tinha caído lá** | ✅ teste |

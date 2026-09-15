# Revisão do seed — o que precisa da sua decisão

> 📋 O arquivo é [`src/nfe_parser/dados/taxonomia_seed.json`](../../src/nfe_parser/dados/taxonomia_seed.json).
> ⭐ Ele já passa por 8 testes de coerência estrutural: slug repetido, `parent` fantasma, âncora
> órfã, prefixo de largura impossível e bucket ausente **acendem vermelho sozinhos**.
>
> ⛔ **O que os testes NÃO julgam é o que está abaixo:** se o mapeamento está *certo*. Isso é
> produto, e é seu.

---

## 1. A taxonomia: ✅ 10 pais + 32 subs + 1 bucket, exatamente como o §5 do report

⛔ **Nada foi acrescentado, removido ou renomeado.** Os `nome` são cópia literal do report. O que foi
inventado é só a **chave interna** (`slug`), e em três lugares ela não sai direto do nome:

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

## 3. 🛑 As seis âncoras que eu quero que você olhe

São 54 âncoras no total. Destas, **48 eu não tenho dúvida**. Estas seis são chamada sua:

| # | Prefixo | Mandei para | A dúvida |
| - | ------- | ----------- | -------- |
| 1 | `07` | **Legumes** | O capítulo 07 é hortaliça em geral — cobre `Verduras` **e** `Legumes`. Mandei o capítulo inteiro para Legumes e abri exceção só para `0704` (couve, brócolis) e `0705` (alface) → Verduras. ⚠️ Tomate e batata caem certo; couve-flor, provavelmente errado |
| 2 | `2207` | **Combustível** | Álcool etílico. No varejo é quase sempre etanol de posto — bebida destilada é `2208`. ⚠️ Se você comprar álcool de limpeza, vai para Combustível |
| 3 | `8507` | **Mecânico** | Acumuladores. `8507.10` é bateria de carro, mas o mesmo prefixo pega pilha e power bank, que seriam `Eletrônicos > Acessórios` |
| 4 | `34011100` | **Higiene** | Sabonete de toucador. É a única âncora de 8 dígitos do arquivo; sem ela, sabonete cairia em `Limpeza` pelo `34` |
| 5 | `30` | **Saúde** (o pai) | Deixei o capítulo farmacêutico no nível 1, e só `3004` → Medicamentos e `3005` → Farmácia. ⚠️ O resto do capítulo fica no genérico de propósito |
| 6 | `16`, `20`, `21` | **Mercearia** | Preparações de carne, conservas e preparações diversas. Enlatado de atum vai para Mercearia, não para `Carnes e peixes` |

### ⭐ O que fazer com uma que você não gostar

📋 Não precisa de story nova nem de código: é **uma linha no JSON**. Trocar o `categoria` de um
prefixo, ou acrescentar um prefixo mais específico, e rodar o carregador de novo. ⚠️ A única coisa
que o arquivo **não** consegue fazer é *remover* um prefixo já carregado num banco — isso é a 011.

---

## 4. O que já está provado, e ⛔ não precisa da sua revisão

| | |
| - | - |
| A taxonomia bate com o §5 do report | ✅ teste |
| Carregar duas vezes não duplica, e o `id` não muda | ✅ teste |
| Toda âncora aponta para categoria que existe | ✅ teste |
| Existe exatamente um bucket, e o slug é `uncategorized` | ✅ teste |
| ⭐ **Crescer o mapa NCM TIRA do bucket um produto que já tinha caído lá** | ✅ teste |

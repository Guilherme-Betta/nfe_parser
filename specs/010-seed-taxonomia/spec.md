# Spec — story 010: o seed da taxonomia

> Implementa o §4 de `specs/02_spec_classificacao.md` na parte que diz *"Seed carregado por script:
> `categorias` (taxonomia + bucket) e `ncm_ancora` (mapa curado)"*.
>
> ⚠️ **A story 009 depende deste seed para existir.** O `_categoria_do_bucket` dela levanta
> `LookupError` quando não há linha `is_bucket = 1`, e a mensagem daquele erro aponta para esta
> story pelo número. ⭐ A 010 é o que faz o passo 4 da cascata parar de ser teórico.

---

## 1. O que a story entrega

Um módulo novo, `src/nfe_parser/seed.py`, com **duas funções que o loop escreve**:

| Função | O que faz |
| ------ | --------- |
| `carregar_categorias(conexao, categorias)` | grava a árvore de categorias, idempotente, e confere o invariante do bucket |
| `carregar_ncm_ancora(conexao, ancoras)` | grava o mapa prefixo→categoria, idempotente, resolvendo o slug |

E **os dados**, num arquivo versionado: `src/nfe_parser/dados/taxonomia_seed.json`.

### 🔴 A story é meio dado, meio código — e o loop só serve para a metade de código

⛔ **Os dados NÃO vão na mensagem para o modelo local.** 43 linhas de categoria mais o mapa NCM
estourariam o turno 1 sozinhos, e curadoria de NCM não é trabalho que se delegue a um modelo de 14b
sem oráculo que a julgue. ⭐ O arquivo de dados é escrito **fora do loop** e revisado pelo Gui.

⚠️ **O que o modelo recebe é uma lista de dicionários por parâmetro.** Ele nunca vê o arquivo, nunca
abre arquivo, e nunca sabe que existe um. Ver a **D3**.

---

## 2. As decisões de desenho que o recorte não tomou

### D1 — o `slug` é DADO explícito, ⛔ não é calculado a partir do nome

Havia duas saídas para os nomes com acento, parêntese e barra (`Mercearia (secos/enlatados)`,
`Farmácia (não-medicamento)`): escrever uma função de slug, ou escrever o slug à mão no arquivo de
dados. **Escolhido: à mão, no dado.**

🔴 **O argumento que decide não é o custo, é a identidade.** O `slug` é a chave estável — é por ele
que o carregador reconhece a linha que já existe, e é dele que depende o `id` não mudar. Se o slug
fosse calculado do nome, **renomear uma categoria mudaria o slug**, e o carregador inseriria uma
categoria NOVA em vez de renomear a antiga: os produtos continuariam apontando para a linha velha, e
a taxonomia teria duas. ⛔ Isso quebraria de frente o requisito da 011 — *"renomear → mantém
vínculos (id estável)"*.

⭐ E há uma prova de que a regra calculada não fecharia sozinha: o bucket se chama
**"Não Classificado"** e o slug dele é **`uncategorized`**, fixado pela spec de produto. Nenhuma
função de slug produz um do outro. A exceção existiria de qualquer jeito.

⚠️ **O custo é real e fica anotado:** nada no código impede um slug digitado errado. Quem protege é
o teste de sanidade do dado (§7), que roda sobre o arquivo real.

### D2 — o slug do filho começa pelo slug do pai

`mercado-frutas`, `bebidas-cafe`, `saude-medicamentos`. Regra única, sem exceção.

🔴 **O que ela resolve:** `Eletrônicos` é pai **e filho de si mesmo** no seed. Com slug simples, as
duas linhas gerariam `eletronicos` e o `UNIQUE` recusaria a segunda — e a recusa viria como
`sqlite3.IntegrityError` no meio do carregamento, sem dizer qual linha. Com a regra, o pai é
`eletronicos` e o filho é `eletronicos-eletronicos`. ⚠️ Feio, e **correto**: o `nome` das duas
continua sendo exatamente o que o Gui escreveu no report; só a chave interna difere.

⭐ Preferi a regra uniforme a um slug especial só para esse caso. Exceção que vale para uma linha é
exceção que ninguém lembra na segunda vez.

### D3 — o carregador RECEBE os dados; ⛔ não os lê do disco

`carregar_categorias(conexao, categorias)` recebe uma lista de dicionários. Quem abre o arquivo é
outra função, `carregar_seed_padrao`, escrita fora do loop (§7).

⭐ **Três motivos, e o terceiro é o que decide:**

1. O oráculo fica barato: a fixture passa 4 categorias, não 43.
2. A mensagem para o modelo local encolhe — ele não precisa saber onde o arquivo mora, nem que
   formato tem. Depois do **Achado X**, cada 3 bytes cortados valem ~1 token.
3. 🔴 **Separa o que pode falhar por motivos diferentes.** "O JSON está no lugar certo e é válido" e
   "o UPSERT é idempotente" são dois defeitos distintos; juntos numa função, um teste vermelho não
   diria qual dos dois quebrou.

### D4 — UPSERT por chave natural: ⛔ nunca apaga, e o `id` nunca muda

`ON CONFLICT(slug) DO UPDATE` para `categorias`, `ON CONFLICT(prefixo) DO UPDATE` para
`ncm_ancora`.

📋 **Idempotência é o contrato central da story:** rodar duas vezes não pode duplicar nem recusar.
As três saídas possíveis, e por que as outras duas foram descartadas:

| Saída | Por que não |
| ----- | ----------- |
| `DELETE` + `INSERT` | ⛔ muda o `id`. Todo `produtos.categoria_id` apontaria para o nada, e a FK recusaria antes disso |
| `INSERT OR IGNORE` | insere uma vez e **nunca mais atualiza**. Corrigir um nome errado no dado não teria efeito nenhum, em silêncio |
| **`UPSERT`** | ✅ insere na primeira vez, atualiza `nome`/`parent_id` depois, e o `id` sobrevive |

### D5 — ⛔ o seed NÃO apaga o que sumiu do arquivo de dados

Tirar uma categoria do JSON **não** a apaga do banco. ⚠️ Apagar categoria é a **011**, e lá tem
regra própria: *"apagar categoria com histórico → produtos vão pro bucket"*. Um carregador de seed
que apagasse em silêncio ou romperia a FK, ou deixaria produtos órfãos.

⚠️ **Pelo mesmo motivo, o `parent_id` só é ESCRITO, nunca limpo.** Se uma categoria perder o `parent`
no arquivo, o banco fica com o pai antigo. Isso é *mover subcategoria*, e também é a 011.

### D6 — a 010 ⛔ NÃO acrescenta migração; é carregador, não esquema

`categorias` e `ncm_ancora` existem desde a v1, e o banco continua em `user_version = 2`.

🔴 **E isso contraria a letra da spec 02, que diz "seed carregado por script de migração".** A letra
está errada e o motivo é concreto: **migração roda uma vez e nunca mais.** Mas a **D3 da 009** diz
que o produto no bucket é reprocessável exatamente para que *crescer o mapa NCM e rodar a cascata de
novo* o resgate. Um seed que só pudesse rodar na criação do banco tornaria esse resgate impossível —
o mapa NCM nunca mais cresceria em banco nenhum que já existisse.

⭐ **É por isto que "idempotente" está no título da entrega, e não é enfeite:** a story existe para
que o seed possa rodar de novo.

### D7 — prefixo NCM só pode ter 2, 4 ou 8 dígitos, e prefixo fora disso LEVANTA

🔴 **Não é regra inventada; é consequência mecânica do código da 009.** O
`buscar_categoria_por_ncm` consulta exatamente `ncm[:8]`, `ncm[:4]` e `ncm[:2]`. Um prefixo de 5 ou
6 dígitos gravado em `ncm_ancora` **nunca casaria com nada** — ficaria no banco, visível, parecendo
mapeamento, sem jamais classificar um produto. ⛔ Dado morto e mudo é pior que erro.

⚠️ `ValueError`, e não `LookupError`: o argumento está malformado; não é coisa que falte no banco.

### D8 — o invariante do bucket é conferido no BANCO, depois de gravar

Ao fim de `carregar_categorias`: `SELECT COUNT(*) FROM categorias WHERE is_bucket = 1` tem de dar
exatamente **1**.

⭐ **Por que no banco e não na lista recebida:** a lista pode estar certa e o banco errado — dois
seeds carregados em sequência, cada um com o seu bucket, produzem dois. É o estado do banco que a
009 vai consultar, então é o estado do banco que precisa valer.

⚠️ **Conferir DEPOIS de gravar parece errado e não é**, porque nenhuma função daqui commita (D9):
quem abriu a transação recebe a exceção com a gravação ainda por confirmar, e desfaz. ⭐ Conferir
antes exigiria simular o resultado do UPSERT em Python — reimplementar o banco para prever o banco.

🔴 **O que este invariante protege:** `_categoria_do_bucket` faz `SELECT ... WHERE is_bucket = 1`
seguido de `fetchone()`. Com dois buckets ele devolve **um qualquer dos dois**, sem erro e sem
sintoma, e metade dos produtos não classificados iria para um bucket e metade para o outro. Com
zero, a cascata inteira morre no passo 4.

### D9 — ⛔ nenhuma função daqui chama `commit()`

Mesma regra de `produtos.py` e `categorizacao.py`, e pelo mesmo motivo: a dívida de `persistir_nota`
commitar por conta própria vence na 013, e não se paga uma dívida abrindo outra igual ao lado.

⭐ Aqui a regra ainda ganha uma razão a mais: o seed inteiro — categorias e âncoras — deve entrar ou
não entrar **junto**. Quem controla isso é o chamador, e só consegue se ninguém commitar no meio.

---

## 3. 🔴 O risco desta story: o defeito silencioso é o modo normal de falha

⚠️ Nas stories anteriores o defeito aparecia como exceção ou resultado errado. Aqui, **os três modos
de falha mais prováveis são mudos** — o carregador "funciona", o banco enche, e o erro só aparece
meses depois num relatório:

| # | Falha muda | Quem a pega |
| - | ---------- | ----------- |
| 1 | `parent_id` fica NULL porque o slug do pai não existe | C1.5 — `LookupError` nomeando os dois slugs |
| 2 | dois buckets, e o passo 4 da cascata se divide entre eles | C1.7 — a D8 |
| 3 | prefixo NCM de largura impossível, que nunca casa | C2.5 — a D7 |

⭐ **É por isso que as três guardas estão no código e não só no teste do dado.** Guarda em teste
protege o arquivo que existe hoje; guarda no carregador protege todo arquivo que venha depois.

---

## 4. Os critérios de aceite congelados

### C1 — `carregar_categorias(conexao, categorias) -> None`

Cada item é um dicionário com `slug` e `nome` obrigatórios, e `parent` (slug do pai) e `is_bucket`
opcionais.

| # | Critério |
| - | -------- |
| C1.1 | banco vazio + 4 categorias → as 4 linhas existem, com `nome` e `is_bucket` certos |
| C1.2 | `parent` resolvido: a sub tem `parent_id` igual ao `id` do pai |
| C1.3 | 🔴 **idempotência**: rodar duas vezes seguidas deixa a mesma contagem de linhas |
| C1.4 | 🔴 **`id` estável**: depois da segunda rodada, o `id` de cada slug é o mesmo de antes |
| C1.5 | `parent` que não existe em lugar nenhum → `LookupError` citando o slug do filho e o do pai |
| C1.6 | `nome` mudado no dado → a segunda rodada **atualiza** o nome, mantendo o `id` |
| C1.7 | 🔴 zero buckets, ou dois → `ValueError` |

⚠️ **A ordem da lista não importa.** O filho pode vir antes do pai: são duas passadas, e a segunda
só roda depois de a primeira ter inserido todo mundo.

### C2 — `carregar_ncm_ancora(conexao, ancoras) -> None`

Cada item é um dicionário com `prefixo` e `categoria` (o **slug**, ⛔ não o id).

| # | Critério |
| - | -------- |
| C2.1 | prefixos novos → as linhas existem com o `categoria_id` do slug certo |
| C2.2 | 🔴 **idempotência**: rodar duas vezes deixa a mesma contagem |
| C2.3 | mesmo prefixo apontando para outro slug → a segunda rodada **reaponta** |
| C2.4 | slug inexistente → `LookupError` citando o prefixo e o slug |
| C2.5 | 🔴 prefixo de largura diferente de 2, 4 ou 8 → `ValueError` |

⚠️ **C2.4 é mais valioso do que parece.** Sem ele, o `SELECT id ... WHERE slug = ?` devolveria
`None`, o `INSERT` bateria no `NOT NULL` da coluna, e o erro sairia como *"NOT NULL constraint
failed: ncm_ancora.categoria_id"* — que não diz **qual** prefixo nem **qual** slug, num arquivo de
dezenas de linhas.

---

## 5. ⚠️ O que os oráculos semeiam, e o que ⛔ não semeiam

Os testes do loop usam categorias **inventadas e mínimas** (4 linhas), ⛔ nunca o arquivo real.
⭐ Um oráculo que dependesse do seed de verdade ficaria vermelho toda vez que o Gui renomeasse uma
categoria — o teste passaria a medir o dado, não o código.

📋 O arquivo real tem teste próprio, e ele é de **outra natureza** — ver §7.

---

## 6. O que esta story NÃO entrega

- ⛔ **Nenhuma lógica de classificação.** A cascata é a 009 e já existe.
- ⛔ **Nenhuma migração de esquema** (D6).
- ⛔ **Apagar, renomear-com-regra ou mover categoria** — é a 011 (D5).
- ⛔ **Nenhuma varredura** que classifique os produtos já gravados depois de o mapa crescer. É a
  dívida **h**, e vence na 013 junto com o chamador real.
- ⛔ **Nenhuma cobertura de NCM para serviço.** Ver a ressalva do §8.

---

## 7. Contratos acrescentados FORA do loop

> 📋 Escritos por Claude no P4, pelo mesmo critério da 009: entram aqui, com a marca de que entraram
> depois, e valem-se por mutação como qualquer outro.

### C3 — `carregar_seed(conexao, dados)` e `carregar_seed_padrao(conexao)`

A cola: `carregar_seed` chama as duas funções do loop na ordem certa (categorias **antes** das
âncoras, porque a âncora resolve slug); `carregar_seed_padrao` lê
`src/nfe_parser/dados/taxonomia_seed.json` e chama `carregar_seed`.

### C4 — o teste de sanidade do arquivo real

⭐ **É um teste sobre o DADO, não sobre o código**, e por isso mora em módulo próprio:

- os slugs são únicos (⚠️ a D1 aceitou que o slug é digitado à mão; é este teste que paga a conta);
- todo `parent` citado existe na lista;
- todo `categoria` do mapa NCM existe na lista;
- exatamente uma linha com `is_bucket`, e o slug dela é `uncategorized`;
- todo prefixo tem 2, 4 ou 8 dígitos **e só dígitos**;
- ⭐ **o teste que fecha a D3 da 009**: semear de verdade, classificar um produto cujo NCM o mapa
  não alcança, provar que ele caiu no bucket, acrescentar a âncora que o alcança, rodar de novo, e
  provar que ele **saiu**.

### C5 — `pyproject.toml` declara o JSON como dado do pacote

⚠️ `[tool.setuptools.packages.find]` só recolhe `.py`. Sem
`[tool.setuptools.package-data]`, o `taxonomia_seed.json` existiria no repositório e sumiria na
instalação — e o defeito **não apareceria na suíte**, porque o venv está em modo editável e lê o
arquivo direto da árvore. 🔴 Falha que só aparece em produção é exatamente o tipo que este projeto
não pode se dar.

---

## 8. ⚠️ O que ficou ANOTADO e não virou código

- **Seis subcategorias são inalcançáveis por NCM**, por natureza: `Restaurante`, `Delivery`,
  `Lanche`, `Cafeteria`, `Faxina` e `Lavanderia`. São **serviços** — a NFC-e não traz NCM útil, e
  quem os identifica é o **emitente**, não o item. ⛔ Não é lacuna do mapa; é limite do método.
  Resolve-se com a 012 (LLM) ou com regra por CNPJ, que não tem story.
- **`Suplementos` ficou sem âncora de propósito.** O NCM plausível (`2106`) é o mesmo das
  preparações alimentícias em geral, e mapeá-lo mandaria molho e sopa para Suplementos. ⭐ Errar
  para o bucket é reversível; errar para a categoria errada é mudo.
- **O carregador não valida que o prefixo só tem dígitos** — só a largura (D7). A largura tem
  consequência mecânica provada; "só dígitos" é qualidade do dado, e por isso foi para o C4.
- **`Verduras` × `Legumes` é a fronteira mais discutível do mapa**, e o capítulo 07 cobre as duas.
  Está na lista de revisão do Gui.

### 🔴 O limite de 6 dígitos — achado pela revisão do Gui, e é o mais sério da story

⛔ **"Bateria de carro" NÃO é expressável neste mapa**, e a razão é estrutural.

O NCM tem 8 dígitos e uma hierarquia de quatro degraus: capítulo (2), posição (4), **subposição (6)**
e item (8). ⚠️ A D7 só admite **2, 4 ou 8**, porque é isso que a 009 consulta — e o conceito
"acumulador de chumbo para arranque de motor" mora exatamente em `8507.10`, o degrau de **6** que
não existe aqui.

⭐ **E mapear os 8 dígitos não resolve:** a bateria real sai com `8507.10.10` ou `8507.10.90`, e um
prefixo `85071000` não casa com nenhum dos dois — `ncm[:8]` é comparação exata, não prefixo.

📋 **Resolução desta story:** a âncora `8507` foi **removida**. Pilha, power bank e bateria de carro
caem todos em `85` → `Eletrônicos`. ⭐ Errado só para a bateria, e o erro custa **uma** classificação
manual: a memória da 008 faz todo item futuro daquele produto herdá-la.

⛔ **Acrescentar o degrau de 6 NÃO foi feito aqui**, e não por preguiça: mudar
`buscar_categoria_por_ncm` é lógica de classificação, que o §6 diz que esta story não entrega — e
invalidaria as medições da 009. ⚠️ É a **dívida j**, e vale mais que as outras porque toda a
curadoria futura do mapa esbarra nela.

### ⚠️ Dois limites que a leitura do código inteiro achou no P4, e a cobertura de 100% não via

1. **`parent` com string vazia é tratado como "sem pai", em silêncio.** O `if pai_slug:` é um teste
   de verdade, não de presença — e o teste do dado repete o mesmo `if`, então não o pegaria. ⭐ Não
   virou guarda porque `""` não é valor que o arquivo produza naturalmente; fica anotado como o
   próximo lugar onde um slug errado passaria batido.
2. 🔴 **A D5 vale para `ncm_ancora` também, e a spec só falava de `categorias`.** Tirar um prefixo
   do arquivo de dados **não** o apaga do banco: um mapeamento errado que já foi carregado pode ser
   *reapontado*, nunca *removido*, editando o JSON. ⚠️ Não é defeito — é a mesma decisão de nunca
   apagar —, mas é consequência que não estava escrita. Remover prefixo é trabalho de quem for dono
   da edição de taxonomia, a **011**.

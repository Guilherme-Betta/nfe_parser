# Spec — 004 · Lote `.zip`, dedup e o que nao derruba o lote

> **Passo 1 do loop. Escrito pelo Claude, dentro da janela da medicao 5.**
>
> ⚠️ **A invariante que governa este arquivo:** *criterio que nao vira assercao nao terminou
> de ser especificado.* Se voce nao consegue imaginar o teste que prova um criterio, o criterio
> ainda e prosa — reescreva ate conseguir.
>
> 🔒 **Os 5 criterios abaixo foram pre-registrados** em `plan/protocolo-medicao-5.md` §2 do
> `AI_Scrum_Workflow` e **aprovados pelo Gui em 2026-09-13, fora da janela medida**. Esta spec
> pode **detalhar** cada um ate virar assercao. Nao pode **trocar** nenhum, nao pode **somar um
> sexto**, nao pode **soltar** nenhum. Escopo que se move durante a medicao contamina a medicao.

**Deriva de** [`specs/01_spec_parser_modelo.md`](../01_spec_parser_modelo.md) §2 (o DDL) e §5
(ingestao em lote). Quarta das 6 stories do nucleo `parser`.

**Continua as stories 001, 002 e 003.** A 001 entregou o esquema (`banco.py`); a 002 e a 003
entregaram a leitura de uma NF-e/NFC-e isolada (`extrator.py`). Ate aqui **nada foi escrito no
banco**: o `extrair_nota` devolve um `dict` e o `dict` morre na memoria. Esta story fecha essa
lacuna e so ela.

⛔ **Esta e a story mais gorda das seis, e isso e proposital.** Ela carrega um pre-requisito que
nenhuma story nomeia — *persistir* —, porque o fatiamento de 2026-09-08 tratou "dedup idempotente"
como a unidade, e dedup pressupoe insercao.

---

## 1. User story

Como dono do app, quero **jogar o `.zip` que baixei do portal da SEFAZ inteiro no importador** e
saber que, se um arquivo la dentro estiver quebrado, **o resto entra mesmo assim** — e que rodar o
mesmo `.zip` duas vezes **nao duplica meus gastos**.

---

## 2. Escopo — os tres modulos novos

| Modulo | Funcao publica | Entrega |
| ------ | -------------- | ------- |
| `src/nfe_parser/persistencia.py` | `persistir_nota(conexao, extraido, importacao_id=None) -> str` | criterios **1** e **2** |
| `src/nfe_parser/classificador.py` | `classificar_xml(xml_texto) -> str` | criterio **3** |
| `src/nfe_parser/importador.py` | `importar(conexao, caminho, origem=None) -> int` | criterios **4** e **5** |

⛔ **Nem uma linha muda em `banco.py` ou `extrator.py`.** O DDL da 001 e o `extrair_nota` da
002/003 sao usados como estao. Se algo neles parecer errado durante a story, isso vai para a §10 do
protocolo — **anotado, nao consertado**.

Toda funcao publica nova sai **anotada** (`-> str`, `-> int`), como a story 003 fixou.

---

## 3. Os 5 criterios, virados em assercao

### C1 — Persistir

`persistir_nota(conexao, extraido, importacao_id=None) -> str` recebe **exatamente o `dict` que
`extrair_nota` devolve** — `{"nota": {...}, "itens": [...]}` — e grava.

| Assercao | Detalhe |
| -------- | ------- |
| C1.1 | Depois de persistir `nfe_55_1item.xml`, `SELECT COUNT(*) FROM notas` == **1** e `FROM itens` == **1** |
| C1.2 | Com `nfe_55_3itens.xml`, `notas` == 1 e `itens` == **3**, com `n_item` **1, 2, 3** |
| C1.3 | `notas.valor_total` e `itens.valor_linha` sao **`int`** (centavos), iguais ao que o `dict` trazia |
| C1.4 | `itens.quantidade` == `"1.5000"` e `itens.valor_unitario` == `"5.3600000000"` — **string decimal exata**, byte a byte igual ao XML. Nao passar por `float` nem `Decimal` |
| C1.5 | Toda coluna `NOT NULL` do DDL sai preenchida: `chave`, `modelo`, `dh_emi`, `valor_total`, `xml_raw`, `criado_em` na `notas`; `nota_chave`, `n_item`, `descricao`, `quantidade`, `valor_linha`, `criado_em` na `itens` |
| C1.6 | `criado_em` e um ISO 8601 que `datetime.fromisoformat` le sem erro. ⛔ **Nao congele o relogio**, nao compare com literal |
| C1.7 | `notas.status` sai `'ok'` (o `DEFAULT` do DDL; nao mande a coluna no `INSERT`) |
| C1.8 | `gtin` sai `NULL` quando o XML dizia `SEM GTIN` — o `extrair_nota` ja resolveu isso, a persistencia so **nao pode desfazer** |
| C1.9 | `importacao_id` chega em `notas.importacao_id`; com o default `None`, a coluna sai `NULL` |
| C1.10 | Devolve a **string `"nova"`** |

### C2 — Dedup idempotente por `chave`

| Assercao | Detalhe |
| -------- | ------- |
| C2.1 | Persistir o **mesmo** `extraido` duas vezes devolve `"nova"` e depois **`"duplicada"`** |
| C2.2 | Depois da segunda, `COUNT(*)` de `notas` e de `itens` **nao muda** |
| C2.3 | 🔒 **O banco fica identico.** `SELECT * FROM notas` e `SELECT * FROM itens` (ordenados) devolvem **as mesmas tuplas** antes e depois — inclusive `criado_em`. Isso prova que a segunda passagem **nao sobrescreveu**, e nao so que nao contou duas vezes |
| C2.4 | Duas notas de **chaves diferentes** convivem: `COUNT(*)` == 2 |
| C2.5 | Nenhuma excecao sobe do caminho duplicado — nem `IntegrityError` |

⚠️ **C2.3 e o criterio que separa dedup de `INSERT OR REPLACE`.** Um `REPLACE` passa em C2.1 e
C2.2 e **reprova** em C2.3, porque reescreve `criado_em`. O teste existir e o que impede a
implementacao preguicosa.

### C3 — Roteamento por raiz + `ide/mod`

`classificar_xml(xml_texto) -> str` devolve **uma de quatro strings**, e **nunca levanta**:

| Entrada | Devolve |
| ------- | ------- |
| Raiz `nfeProc`, `ide/mod` == `55` ou `65` | `"nfe"` |
| Raiz `CFe` (CF-e/SAT, modelo 59) | `"nao_suportado_sat"` |
| Raiz `procEventoNFe` | `"evento"` |
| XML corrompido, string vazia, ou raiz desconhecida | `"invalida"` |

| Assercao | Detalhe |
| -------- | ------- |
| C3.1 | As tres fixtures existentes (`nfe_55_1item`, `nfe_55_3itens`, `nfe_65_1item`) → `"nfe"` |
| C3.2 | `<CFe>...</CFe>` minimo → `"nao_suportado_sat"` |
| C3.3 | `<procEventoNFe>...</procEventoNFe>` minimo → `"evento"` |
| C3.4 | `"<nfeProc><quebrado"` → `"invalida"`; `""` → `"invalida"`; `"<qualquerCoisa/>"` → `"invalida"` |
| C3.5 | `nfeProc` com `mod` fora de 55/65 → `"invalida"` |
| C3.6 | ⭐ **O classificador le a raiz com `xml.etree.ElementTree`, nao com o `nfelib`.** Ele precisa responder sobre XML que o `nfelib` recusa — usar `NfeProc.from_xml` aqui seria pedir ao parser estrito que classifique justamente o que ele nao consegue abrir |
| C3.7 | Namespace nao atrapalha: a raiz e comparada **sem** o `{http://...}` na frente |

### C4 — Nenhum arquivo derruba o lote

`importar(conexao, caminho, origem=None) -> int` devolve o `importacoes.id` e **nunca levanta** por
causa do conteudo de um arquivo.

| Assercao | Detalhe |
| -------- | ------- |
| C4.1 | 🔒 Um `.zip` com **um arquivo bom e um corrompido** termina com: a nota boa em `notas`, **duas** linhas em `importacao_arquivos` (`'nova'` e `'invalida'`), e **nenhuma excecao** |
| C4.2 | Cria **uma** linha em `importacoes`, com `origem` e `iniciado_em` preenchidos, e `finalizado_em` preenchido ao fim |
| C4.3 | Cada arquivo vira **uma** linha em `importacao_arquivos`, com `arquivo` (o nome dentro do zip), `arquivo_hash` (**SHA-256 hex dos bytes**) e `chave` (a chave quando conhecida, `NULL` quando nao) |
| C4.4 | Mapa `classificar_xml` → `importacao_arquivos.resultado`: `"nfe"` persistida nova → `'nova'`; `"nfe"` ja existente → `'duplicada'`; `"nao_suportado_sat"` → `'nao_suportado_sat'`; `"evento"` → `'cancelamento_orfao'`; `"invalida"` **ou** `ValueError` vindo do `extrair_nota` → `'invalida'` |
| C4.5 | O mesmo `.zip` importado **duas vezes** deixa `notas` com a mesma contagem, e a segunda importacao registra `'duplicada'` |
| C4.6 | `detalhe` traz a mensagem do erro quando `resultado` == `'invalida'`, e `NULL` quando deu certo |
| C4.7 | Membros do `.zip` que **nao** terminam em `.xml` (maiuscula/minuscula indiferente) e entradas de diretorio sao **ignorados**: nao viram linha, nao entram na contagem |

### C5 — `.zip` e `.xml` avulso pelo mesmo caminho de codigo

| Assercao | Detalhe |
| -------- | ------- |
| C5.1 | `importar(conexao, caminho_de_um_xml)` persiste a nota e cria **uma** linha em `importacao_arquivos`, com `arquivo` == o nome do arquivo |
| C5.2 | O sufixo decide, sem adivinhacao de conteudo: `.zip` → abre com `zipfile`; qualquer outro → trata como XML unico |
| C5.3 | ⭐ Os dois caminhos convergem numa **unica** funcao interna por arquivo — `.zip` e `.xml` nao podem ter duas copias da logica de roteamento. Provado por C5.4 |
| C5.4 | O mesmo XML, importado avulso e dentro de um `.zip`, produz `resultado` e `arquivo_hash` **iguais** |
| C5.5 | `caminho` aceita `str` e `pathlib.Path` |

### C6 — Contadores da importacao

> Nao e um sexto criterio pre-registrado: e a §2 do DDL da story 001, que **ja criou as colunas**.
> Sem isso a linha de `importacoes` nasce com zeros permanentes, e o criterio 4 registra o lote num
> lugar so pela metade.

| Assercao | Detalhe |
| -------- | ------- |
| C6.1 | `total_arquivos` == numero de linhas em `importacao_arquivos` daquela importacao |
| C6.2 | `notas_novas`, `duplicadas`, `invalidas`, `nao_suportadas` batem com a contagem por `resultado` |
| C6.3 | `cancelamentos_aplicados` fica **0** nesta story — a 004 classifica evento, nao aplica |

---

## 4. Fora de escopo — e nao negocie durante a medicao

| Fora | Onde mora |
| ---- | --------- |
| Aplicar cancelamento, `tpEvento=110111` | story **005**. Aqui o evento e **classificado**, nao aplicado |
| JSON de `ResultadoImportacao` e funcoes de leitura | story **006** |
| Web / UI, performance, concorrencia | specs 03 e 05 |
| Qualquer refactor do que as stories 002 e 003 entregaram | — |

---

## 5. Tres decisoes que esta spec tomou ao detalhar

Registradas porque **detalhar tambem e decidir**, e uma sessao futura precisa saber o que foi
medido e o que foi escolhido.

**(a) `"evento"` → `resultado='cancelamento_orfao'`.** O `CHECK` do DDL so aceita seis valores, e
nenhum diz "evento visto, nao aplicado". Dos seis, `cancelamento_orfao` e o unico que descreve *um
evento que nao alterou nota nenhuma* — que e literalmente o que acontece na 004, ja que ela nao
aplica nada. O `detalhe` registra a verdade em texto. ⚠️ **A story 005 vai refinar isso**, e o
refinamento e esperado, nao e conserto de bug.

**(b) O `.zip` de teste e montado em `tmp_path`, nunca commitado.** O `nfe_parser` e repositorio
publico e a checagem de privacidade procura exatamente por `.zip` entrando no repo. Os testes
montam o zip a partir das fixtures XML que **ja existem**. Se um `.zip` aparecer no diff, algo saiu
errado — nao e falso positivo.

**(c) Os XML de CF-e, de evento e o corrompido sao strings inline no teste, nao fixtures novas.** O
roteamento de C3 decide pela **raiz**, entao um `<CFe/>` minimo basta; um CF-e completo seria uma
fixture grande para provar o mesmo. Menos arquivo commitado, menos contexto no `--read` do passo 3.

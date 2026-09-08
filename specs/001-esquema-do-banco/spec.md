# Spec — 001 · Esquema do banco

> **Passo 1 do loop. Escrito pelo Claude.**
>
> ⚠️ **A invariante que governa este arquivo:** *criterio que nao vira assercao
> nao terminou de ser especificado.* Se voce nao consegue imaginar o teste que
> prova um criterio, o criterio ainda e prosa — reescreva ate conseguir.
>
> Isso foi medido, nao inventado: na Fase 0 a spec dizia "nao use float; 1.005
> teria que virar 101". Nenhum teste cobriu. O modelo usou `int(Decimal(x)*100)`,
> que TRUNCA (1.005 -> 100), e passou. A spec estava certa e inutil.

**Deriva de** [`specs/01_spec_parser_modelo.md`](../01_spec_parser_modelo.md) §2 (o DDL).
Esta e a primeira das 6 stories do nucleo `parser`. Backlog completo no
`offload-log.md` do `AI_Scrum_Workflow`.

## 1. User story

Como dono do app, quero que o banco **se crie sozinho e sobreviva a
reprocessamento**, para que rodar a importacao de novo nao corrompa nem duplique
nada, e para que as stories seguintes tenham onde escrever.

## 2. Escopo — o que esta feature faz

- Modulo novo `src/nfe_parser/banco.py`.
- `abrir_banco(caminho) -> sqlite3.Connection`: abre (criando se nao existir),
  **liga as foreign keys** e aplica o esquema.
- `criar_esquema(conexao) -> None`: executa o DDL do §2 da spec 01, **como esta
  escrito la** — as 4 tabelas e os 4 indices, todos com `IF NOT EXISTS`.

## 3. Fronteiras — o que ela NAO faz

- **Nao le XML.** Nenhum import de `nfelib` aqui.
- **Nao insere dado nenhum.** Escrita e das stories 002+.
- **Nao faz migracao de esquema** (nada de `ALTER TABLE`, versao de schema,
  `PRAGMA user_version`). O DDL e idempotente; isso basta para o MVP.
- **Nao decide o caminho do arquivo** a partir de variavel de ambiente. O
  caminho e argumento; quem le o `.env` e a borda, nao o nucleo.
- **Nao cria classe, ORM, nem camada de repositorio.** Duas funcoes.

## 4. Criterios de aceitacao (TESTAVEIS)

Cada linha vira pelo menos uma assercao no passo 2.

| # | Criterio | Vira que assercao |
| - | -------- | ----------------- |
| 1 | Abrir num caminho inexistente **cria o arquivo** | `caminho.exists()` depois da chamada |
| 2 | As **4 tabelas** existem | `sqlite_master` contem `importacoes`, `notas`, `itens`, `importacao_arquivos` |
| 3 | Os **4 indices** existem | `sqlite_master` contem `idx_notas_dh_emi`, `idx_itens_nota`, `idx_itens_ncm`, `idx_itens_gtin` |
| 4 | Abrir **duas vezes** nao quebra e **nao apaga dado** | insere 1 nota, fecha, reabre, a nota continua la e ha exatamente 1 |
| 5 | **Foreign keys ligadas** | inserir item cuja `nota_chave` nao existe levanta `IntegrityError` |
| 6 | `notas.status` so aceita `ok`/`cancelada` | inserir `status='duplicada'` levanta `IntegrityError` |
| 7 | `itens` e unico por `(nota_chave, n_item)` | inserir o mesmo par duas vezes levanta `IntegrityError` |

> ⚠️ **O criterio 5 e o que mais engana.** No SQLite, `PRAGMA foreign_keys` vem
> **DESLIGADO por padrao, por conexao** — nao e propriedade do arquivo. Um banco
> com todos os `REFERENCES` escritos corretamente aceita item orfao em silencio
> se ninguem ligar o pragma. Nada no DDL denuncia isso; so um teste denuncia.
> E a story 005 (cancelamento orfao) depende diretamente disso funcionar.

## 5. Casos de borda e caminho de erro

⚠️ **Item 1 da rubrica de qualidade:** o `verify` precisa cobrir o caminho de
erro, nao so o feliz. Tem que existir pelo menos um teste que espera excecao ou
entrada invalida.

| Entrada | Comportamento esperado |
| ------- | ---------------------- |
| caminho num diretorio que nao existe | erro do `sqlite3` propaga (nao engolir, nao criar diretorio) |
| item com `nota_chave` inexistente | `sqlite3.IntegrityError` (criterio 5) |
| `notas.status = 'duplicada'` | `sqlite3.IntegrityError` — `duplicada` e desfecho de *importacao*, nao estado de nota |
| mesmo `(nota_chave, n_item)` duas vezes | `sqlite3.IntegrityError` (criterio 7) |
| banco ja existente e populado | reabrir preserva tudo (criterio 4) |

## 6. Tamanho — cabe no orcamento?

- [x] O codigo relevante para esta feature cabe em **~300 linhas**?

DDL do §2 = ~45 linhas, mais duas funcoes curtas. Estimativa: **~70 linhas**.
Folgado dentro dos 300.

# NF-e Despesas — Documento Central do Projeto

> 📜 **Foto histórica de 2026-09-04 — não é mais atualizada.** O "doc vivo" abaixo parou nesta data:
> estado, pendências e próximos passos estão desatualizados. O estado atual está nas specs (`specs/`)
> e no `git log`. ⚠️ Quem cita **este** arquivo: o `specs/02-recorte-em-stories.md` e a story 010.
> As specs 01–06 citam o [`report_projeto_nfe.md`](report_projeto_nfe.md), que numera as seções de outro jeito.
> Única edição desde então: removido o caminho local da máquina na seção 7.

> **Doc único e vivo.** Substitui e consolida os três anteriores: `report_projeto_nfe.md` (design), `report_handoff_nfe.md` (handoff) e `report_sessao_nfe.md` (sessão).
> Atualizado: **2026-09-04**.
> ⚠️ Repo **público**. Nada de dado pessoal (CPF, nome, CNPJ, paths de usuário, IPs) no código ou em fixtures.
> As **specs por componente** (no repo, `specs/01`…`06`) são o **contrato de build**; este doc é o *porquê*, o estado e as pontas soltas — não duplica o interior das specs.

---

## 0. Do que se trata

Ferramenta para **visualizar despesas a partir de notas fiscais eletrônicas** (XML), com categorização automática (NCM + LLM opcional) e orçamento inspirado no Cashew. Projeto **público no GitHub**, mas o **MVP é validado no uso pessoal do Gui** primeiro.

**Motivação:** o portal/app da Nota Fiscal Paulista é ruim; o fluxo atual (NFe-visualizador → export zip de XMLs → olhar manual) é trabalhoso e não dá visão de gasto. **Diferencial:** a **granularidade de item** (produto a produto) que a NF-e carrega e nenhuma ferramenta pronta explora bem.

**Princípio de honestidade:** onde a confiabilidade é *best-effort* (ex.: casar produto entre lojas por texto), o app **mostra isso**, não finge precisão.

## 1. Estado atual (2026-09-04)

- **Fase de papel encerrada.** As **6 specs por componente estão prontas e aprovadas**.
- **Repositório oficial criado e publicado:** `github.com/Guilherme-Betta/nfe_parser` (público, **GPL-3.0**), scaffold Python/FastAPI no ar, baseline em `main` propagada pra `fable` e `scrum`.
- **Próximo:** sair do papel pro **build** (código), começando pela fatia de fundação.

## 2. Escopo

### É (MVP)
- **Movido por nota fiscal** — gastos vêm dos XMLs, sem entrada manual.
- **NF-e (55) + NFC-e (65)** (mesmo schema; o dia-a-dia de mercado/farmácia costuma ser 65).
- **CF-e/SAT:** schema diferente → marcado **"não suportado ainda"** (não quebra o lote; sinaliza).
- **Single-user**, **só despesas** (saídas), **só BRL**. UI/docs em **PT-BR**.

### NÃO é (roadmap)
Entrada manual / app de finanças abrangente · receitas · multiusuário · EN · QR scan no app · download via SEFAZ/certificado · CF-e/SAT · regras por regex na classificação · backend LLM configurável (OpenAI-compatible) · budget por subcategoria/metas/recorrência/carteiras · comparativo planejado×real · front JS/React · Postgres.

## 3. Decisões travadas

**Arquitetura & stack**
- **API-first:** lógica (parsing, classificação, budgets, queries) num núcleo que fala **JSON, não HTML**; a UI é cliente. Evolução barata pra React troca só a camada de cima. Armadilha a evitar: frameworks que grudam lógica e UI.
- Stack fixada: **Python · FastAPI + Jinja2/HTMX · SQLite · Docker**. Parsing com **nfelib**. Libs menores a critério da implementação.
- **App shell** (spec de ingestão/UI) é dono da **migração versionada** (`schema_version`) + **seed** + **config só por env** + orquestração parser→classificação. **LLM não roda no import** (opt-in à parte).

**Dados & parsing**
- **Grão duplo:** `notas` (cabeçalho) + `itens` (uma linha por produto, com NCM/GTIN/qtd/valor).
- Dinheiro em **centavos (int)**; `quantidade`/`valor_unitario` como **string decimal exata**; `chave`/`emit_cnpj`/`ncm`/`gtin` como **TEXT** (zero à esquerda).
- XML bruto guardado em `notas`; inválidas/não-parseáveis vão no log `importacao_arquivos`, não em `notas`. `notas.status` só `ok|cancelada`.
- **Dedup idempotente por chave**; **cancelamento em duas passadas** (ordem no zip não importa).

**Classificação (núcleo diferenciador)**
- **Por produto** — identidade: **GTIN** quando existe, senão `xProd` normalizado **+ CNPJ da loja**. Cross-loja por texto é *best-effort*, sinalizado (`identidade_origem`).
- Cascata: **memória (humano) → NCM âncora → LLM opt-in → bucket** (`slug=uncategorized`, rótulo "Não Classificado"). `manual` nunca é sobrescrito.
- Mapa **NCM→categoria curado** no MVP; resolve o nível mais específico que o prefixo justifica.
- Taxonomia **2 níveis + tags livres** (tags **manuais** no MVP); editável pela UI (criar/renomear/mover/apagar). Apagar categoria com histórico → despesas vão pro bucket.
- **LLM opt-in**, só **Ollama**, `OLLAMA_URL` por env desde o dia 1, **atrás de harness de eval**. Base determinística roda **sem GPU**.

**Orçamento**
- Teto **por categoria nível-1 / mês** (centavos). **Realizado com rollup** subcategoria→mãe (exclui canceladas; bucket fica à parte). **Saldo do mês (limite/gasto/saldo) no MVP**; comparativo multi-período é roadmap.

**Visualização**
- Agregações read-only: gasto por mês/categoria/loja, top produtos, **preço no tempo**. Filtros compostos, com o **mesmo rollup** do orçamento (pra não divergir).
- **Tipo de gráfico = default sensato por análise, trocável** pelo usuário — **não fixo**. Fora só combinações que mentem sobre o dado (série/ranking em pizza). Gráfico no navegador (lib JS leve, sem React).

**Deploy**
- **Docker + `docker-compose` + imagem oficial no GHCR** (release/tag); volume nomeado pro SQLite; Ollama do `juicey` via `host.docker.internal`. **Rede do servidor (Tailscale/Funnel/TLS/domínio) fica FORA da imagem** — é infra do host. CI (GitHub Actions) roda lint+testes a cada push.

**Licença & idioma**
- **GPL-3.0** (fator decisivo: possível reúso de código do Cashew). PT-BR no MVP, EN no roadmap.

## 4. Componentes & specs (todas ✅ aprovadas)

Ordem de build (`specs/NN_...` no repo):

1. **parser + modelo de dados** — zip/xml → detecta tipo → persiste em SQLite; relatório JSON.
2. **classificação** — identidade + cascata + taxonomia editável + harness de eval do LLM.
3. **ingestão-web / UI** — shell FastAPI + migração/seed/config + pipeline de import + API JSON + UI (upload, revisar, taxonomia).
4. **orçamento** — teto por categoria/mês + realizado com rollup + página `/orcamento`.
5. **visualização** — agregações + filtros + gráficos (default trocável) + página `/relatorios`.
6. **deploy** — Dockerfile + compose + imagem GHCR + CI.

## 5. Taxonomia inicial (SEED — o Gui edita agora e depois na UI)

Regra: apagar/mover categoria com despesas → vão pro bucket "Não Classificado" (`uncategorized`).

- **Mercado**: Frutas · Verduras · Legumes · Carnes e peixes · Laticínios · Padaria · Mercearia (secos/enlatados) · Congelados
- **Bebidas**: Cerveja · Vinho · Destilados · Café · Chá
- **Limpeza**: Faxina · Lavanderia · Louça
- **Cuidado pessoal**: Cabelo · Pele
- **Saúde**: Higiene · Medicamentos · Farmácia (não-medicamento) · Suplementos
- **Restaurante e delivery**: Restaurante · Delivery · Lanche · Cafeteria
- **Eletrônicos**: Eletrônicos · Acessórios
- **Vestuário**
- **Automóvel**: Borracharia · Combustível · Mecânico
- **Outros**: Petshop

Nota: **Café** entrou como subcategoria (caso real, NCM 0901); se virar consumo grande, promover a categoria (chamada do Gui).

## 6. Qualidade (é público)

- **Testes desde o início** com **fixtures anonimizadas** (55, 65, cancelada, sem GTIN, multi-item…). Resolve teste **e** privacidade.
- **Anonimização:** utilitário dev a construir (troca CPF/nome/CNPJ por fake).
- **CI (GitHub Actions):** lint+testes a cada push. **Aceitar contribuições:** sim (CONTRIBUTING, issues).

## 7. Repositório

- **GitHub (público):** https://github.com/Guilherme-Betta/nfe_parser — licença **GPL-3.0**.
- **Scaffold:** `.gitignore` (proteção anti-dado-pessoal + ignore do Aider), `.env.example`, `pyproject.toml`, `README.md`, `CONTRIBUTING.md`, `src/nfe_parser/`, `tests/` (smoke + README de fixtures), `.github/workflows/ci.yml`, `LICENSE`, `specs/01…06`.
- **Branches:** `main` (baseline/fonte da verdade), `fable` (trabalho do Fable), `scrum` — todas alinhadas por fast-forward.

## 8. Assumptions ativas (não vetadas)

- Normalização de `xProd` conservadora (minúsculas/sem acento/pontuação fora; não mexe em números/unidades).
- `itens` ganha `produto_id` (migração aditiva).
- NCM âncora resolve categoria-base; subcategoria fina/tags ficam pro LLM/humano.
- Orçamento calcula só o realizado que precisa; analytics gerais são da visualização — **mesmo rollup** nas duas.

## 9. Pendências / abertos

- **Mapa NCM→categoria curado** — construir na fase de build (dados do Claude + revisão do Gui).
- **Fixture multi-item real** — validar o parser com uma nota de mercado (só validamos notas de 1 item até agora).
- **Utilitário de anonimização** — pré-requisito das fixtures.
- **Bar de aprovação do LLM** — o Gui decide após ver as métricas do eval.
- **Seed final** — o Gui pode ainda tirar/renomear/adicionar categorias.
- **Papel do Aider vs Fable** no build (ver §11).

## 10. Unknowns (honestos)

- ⚠️ **Captura na fonte (frente separada, anterior ao app):** compras de supermercado/farmácia do Gui **não vêm no XML** (o "XML vazio"). Provável: são 65/SAT e o NFe-visualizador exporta vazio/só PDF/não captura. **Não é problema do app** — investigar o que o NFe-visualizador exporta pra nota de mercado e se a NF Paulista dá o XML por outro caminho. O app já nasce lendo 55+65 pra engolir tudo quando a captura funcionar.
- **Qualidade real** da classificação por LLM local PT-BR no teto de 12 GB VRAM (`juicey`) — precisa eval, não presumir.
- Comportamento do NFe-visualizador ao exportar 65/SAT.

## 11. Frentes adjacentes

- **Aider** entrou no fluxo de coding (artefatos `.aider*` ignorados no repo). Encaixe exato — junto do Fable, no lugar dele, qual modelo — **ainda não fechado**.
- Projeto **separado** `AI_Scrum_Workflow` (repo `AI-Scrum-Workflow`): kit de "scrum offload" com LLM local; teve housekeeping/commit numa sessão, mas **não foi discutido a fundo** e não faz parte deste projeto.

## 12. Próximos passos

1. **Build da fundação** no branch `fable`: parser → classificação → ingestão/UI (já importa um zip, classifica pela base e mostra as notas). Destrava os unknowns (multi-item, `nfelib`, LLM).
2. Definir **Aider vs Fable** como ferramenta de build.
3. Depois: **orçamento → visualização → deploy**.
4. Em paralelo (frente separada): investigar a **captura de 65/SAT na fonte**.

## Referências

- Repo: https://github.com/Guilherme-Betta/nfe_parser · Specs: `specs/01…06`.
- Este doc **substitui** `report_projeto_nfe.md`, `report_handoff_nfe.md` e `report_sessao_nfe.md`.

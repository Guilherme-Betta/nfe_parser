# Contribuindo

Obrigado pelo interesse! Este projeto e guiado por **specs** — cada componente tem um contrato em `specs/` (numeradas `01`→`06` na ordem de build). Antes de implementar ou revisar, leia a spec do componente.

## Ambiente

```bash
pip install -e ".[dev]"
pytest        # testes
ruff check .  # lint
```

## Regras

- **Nada de dado pessoal** no repositorio. `.xml`/`.zip`/`.db` reais sao ignorados; fixtures so **anonimizadas** em `tests/fixtures/`.
- Cada componente e **API-first** (nucleo fala JSON; UI e cliente).
- Dinheiro em **centavos (int)**; `quantidade`/`valor_unitario` como string decimal exata.
- PR so entra com **CI verde** (lint + testes).
- Mudou o comportamento? Atualize a spec do componente junto.

## Idioma

UI e docs em PT-BR no MVP (EN no roadmap). Codigo e commits podem misturar PT/EN.

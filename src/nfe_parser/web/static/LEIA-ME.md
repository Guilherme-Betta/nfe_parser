# Arquivos JavaScript de terceiros — copiados, sem CDN

Decisao do Gui (2026-10-15): o app e self-hosted e tem de funcionar sem internet, entao as
bibliotecas de front ficam aqui, com a versao fixada. Atualizar = trocar o arquivo e esta tabela.

| Arquivo | Pacote | Versao | Licenca | Integridade (SRI) |
| ------- | ------ | ------ | ------- | ----------------- |
| `htmx.min.js` | `htmx.org` (`dist/htmx.min.js`) | 2.0.4 | 0BSD — `htmx.LICENSE.txt` | `sha384-HGfztofotfshcF7+8n44JQL2oJmowVChPTg48S+jvZoztPfvwD79OC/LTtG6dMp+` |
| `chart.umd.js` | `chart.js` (`dist/chart.umd.js`) | 4.4.1 | MIT — `chart.LICENSE.md` | `sha384-dug+JxfBvklEQdJ4AYuBBAIScUz0bVN73xpy273gcAwHjb3qI0fXmuYNaNfdyYJG` |

O `.gitattributes` marca `*.js` daqui como `-text`: o git nao converte quebra de linha, e o hash
continua valido no checkout de qualquer sistema.

Para conferir um arquivo: `openssl dgst -sha384 -binary <arquivo> | openssl base64 -A`.

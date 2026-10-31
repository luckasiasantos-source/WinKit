# WinKit

Prepara um pendrive **Ventoy** para que qualquer ISO **original** do Windows 11 (e futuramente 10) instale já com:

- conta local, sem conta Microsoft, idioma/teclado/fuso definidos
- drivers do seu PC
- seus aplicativos instalados automaticamente (offline ou via winget)
- as pastas de configuração dos seus aplicativos restauradas no lugar certo
- bloatware removido e ajustes de privacidade, visual e energia aplicados

**A ISO nunca é modificada.** Tudo fica numa pasta `WinKit\` do pendrive.

> Estado: **planejamento concluído, implementação não iniciada.** Veja `docs/STATUS.md`.

## Documentação

| Documento | Para quê |
|---|---|
| [`docs/PLANO.md`](docs/PLANO.md) | O que o produto é, como funciona e em que ordem será construído |
| [`docs/ARQUITETURA.md`](docs/ARQUITETURA.md) | Arquitetura, regras do código e registro de decisões |
| [`docs/STATUS.md`](docs/STATUS.md) | O que já está implementado |
| [`docs/DIVIDAS_TECNICAS.md`](docs/DIVIDAS_TECNICAS.md) | O que está provisório ou incompleto |
| [`docs/INCIDENTES.md`](docs/INCIDENTES.md) | O que deu errado e como foi resolvido |
| [`docs/CHANGELOG.md`](docs/CHANGELOG.md) | Mapa de todas as mudanças |
| [`CLAUDE.md`](CLAUDE.md) | Regras obrigatórias para quem mexe no código |

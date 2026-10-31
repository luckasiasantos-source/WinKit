<div align="center">

<img src="docs/imagens/studio-apps.png" alt="WinKit Studio" width="820">

# WinKit

**Instale o Windows já do seu jeito — drivers, apps, configurações e privacidade — a partir de um pendrive Ventoy, sem modificar a ISO.**

[![CI](https://github.com/luckasiasantos-source/Iso-Modify-Win11/actions/workflows/ci.yml/badge.svg)](https://github.com/luckasiasantos-source/Iso-Modify-Win11/actions/workflows/ci.yml)
![Python 3.12](https://img.shields.io/badge/python-3.12-blue)
![Windows 11](https://img.shields.io/badge/Windows-11-0078D4)
[![Licença: Apache 2.0](https://img.shields.io/badge/licen%C3%A7a-Apache%202.0-green)](LICENSE)
![100% vibe-codado](https://img.shields.io/badge/100%25-vibe--codado-red)
![Pré-alpha](https://img.shields.io/badge/est%C3%A1gio-pr%C3%A9--alpha-orange)

</div>

> [!CAUTION]
> **Pré-alpha, 100% vibe-codado, projeto pessoal. Use por sua conta e risco.**
> O WinKit foi feito para uso próprio, como um teste, e não como um produto lançado. Quem usar será, na prática, um testador.
> Todo o código do WinKit foi escrito por inteligência artificial, sem auditoria humana completa, e ainda **não foi validado numa instalação real do Windows**. Ele mexe em partes sensíveis do sistema (instalação, registro, drivers, contas, arquivos) e pode ter erros ou falhas de segurança que causem perda de dados ou um Windows inutilizável.
> **Toda a responsabilidade é de quem baixa e usa.** O autor não se responsabiliza por nenhum dano, perda ou falha de segurança. Teste primeiro numa máquina virtual, faça backup antes e [relate os erros que encontrar](https://github.com/luckasiasantos-source/Iso-Modify-Win11/issues). Veja a seção [Aviso](#aviso).

> **English summary.** WinKit prepares a [Ventoy](https://www.ventoy.net) USB drive so that any *unmodified* Windows 11 ISO installs unattended with a local account, your drivers, your apps (offline installers or winget), your app settings restored to the right folders, bloatware removed and privacy/UI tweaks applied. Everything lives in a `WinKit\` folder on the USB drive; the ISO is never touched. The UI is in Brazilian Portuguese. **Pre-alpha personal project, 100% vibe-coded (AI-written, not fully human-reviewed, not yet validated on real hardware). Use entirely at your own risk; the author accepts no liability.**

---

## Por que existe

Reinstalar o Windows é rápido; deixar ele do seu jeito é que demora: caçar drivers, baixar e instalar app por app, reconfigurar cada um, remover o que veio de brinde, desligar telemetria, arrumar a barra de tarefas…

O WinKit faz isso de uma vez. Você monta uma **receita** no seu PC atual, e o pendrive Ventoy instala o Windows já pronto, com a mesma ISO original que você baixou da Microsoft.

## O que ele faz

| | |
|---|---|
| 🔌 **Ventoy, sem tocar na ISO** | Usa o plugin `auto_install` do Ventoy. Troque a ISO por uma versão nova e tudo continua funcionando. Um pendrive serve a várias ISOs. |
| 👤 **Conta local** | Sem conta Microsoft, sem telas de rede e privacidade. Idioma, teclado ABNT2, fuso e edição definidos na receita. |
| 💽 **Disco nunca criptografado sozinho** | Por padrão o Windows não liga a criptografia automática do dispositivo — nem depois de entrar com conta Microsoft. |
| 🧩 **Drivers do seu PC** | Exporta os drivers de terceiros (rede primeiro) e instala com `pnputil` antes do primeiro login. |
| 📦 **Seus aplicativos** | Lê os apps instalados no seu PC; você marca os que quer. Instala offline (instaladores baixados com `winget download`) ou pelo winget online. Fecha os apps abertos pelo instalador e desliga a inicialização automática. |
| 🗂️ **Configurações dos apps** | Escolha pastas e arquivos de configuração (Discord, VS Code, OBS, saves de jogos…). São copiados para o pendrive com cópia de sombra (mesmo com o app aberto) e restaurados no lugar certo **antes** de você abrir o app no Windows novo. |
| 🧹 **Apps pré-instalados** | Remove o que você escolher (lista em níveis de risco) e impede que voltem com as atualizações. |
| 🎛️ **Ajustes** | Privacidade (telemetria mínima, ID de anúncios, Bing no Iniciar, Copilot, Recall…), aparência (tema escuro, barra à esquerda, menu de contexto clássico…), energia. Aplicados ao perfil padrão: a conta já nasce configurada. |
| 🔄 **Windows Update** | Opcional, no final, pela API oficial. |
| 🪟 **Primeiro login do seu jeito** | Silencioso (só um aviso no fim), com contagem regressiva ou interativo — e itens marcados como "perguntar" para decidir na hora. |
| 🧾 **Resumo e logs** | Resumo em HTML na área de trabalho e logs gravados de volta no pendrive. |

<div align="center">
<img src="docs/imagens/agente-inicio.png" alt="Janela do primeiro login" width="420">
<img src="docs/imagens/agente-progresso.png" alt="Progresso" width="420">
</div>

## Como funciona

```
 Seu PC atual                 Pendrive Ventoy                         Windows novo
┌──────────────┐   grava    ┌────────────────────────────┐   boot   ┌───────────────────────────┐
│ WinKit Studio│ ─────────► │ ISOs originais (intactas)  │ ───────► │ instalação automatizada    │
│  receita     │            │ ventoy/ventoy.json + XML   │          │ Fase 1 (antes do login):   │
│  apps        │            │ WinKit/                    │          │  drivers, bloatware,       │
│  drivers     │            │   receita, instaladores,   │          │  ajustes, apps, backups    │
│  backups     │            │   drivers, backups, Agente │          │ Fase 2 (depois do login):  │
└──────────────┘            └────────────────────────────┘          │  apps por usuário, winget, │
                                                                     │  Windows Update, resumo    │
                                                                     └───────────────────────────┘
```

1. O **Studio** (ou a linha de comando) lê o seu PC e grava a receita e todo o conteúdo na pasta `WinKit\` do pendrive.
2. O Ventoy injeta um `autounattend.xml` na instalação. Você só escolhe o disco: o WinKit **nunca** particiona nem formata nada sozinho.
3. Durante a instalação, um pequeno script encontra o pendrive e prepara o **Agente**.
4. O Agente faz quase tudo antes da tela de login. O que precisa do seu usuário ou da internet acontece logo depois, em segundo plano ou com janela, como você escolher.

## Começando

### Requisitos

- Windows 10 ou 11 no PC onde você monta o pendrive (o Studio pede administrador).
- Um pendrive com o [Ventoy](https://www.ventoy.net) instalado e uma ISO original do Windows 11.

### Usar

1. Baixe o `WinKit-…-windows-x64.zip` na página de [**Releases**](https://github.com/luckasiasantos-source/Iso-Modify-Win11/releases) e extraia. Não precisa compilar nada. Os executáveis não são assinados: se o SmartScreen avisar, clique em "Mais informações" → "Executar assim mesmo".
2. Abra `winkit-studio\winkit-studio.exe`.
3. Siga a barra lateral: **Pendrive → Windows e conta → Aplicativos → Configurações dos apps → Drivers → Apps pré-instalados → Ajustes → Energia → Primeiro login → Revisar e construir**.
4. Dê boot pelo Ventoy, escolha a ISO e o modelo `winkit-…`.

<div align="center">
<img src="docs/imagens/studio-conta.png" alt="Windows e conta" width="420">
<img src="docs/imagens/studio-conta-escuro.png" alt="Tema escuro" width="420">
</div>

### Linha de comando

Tudo que o Studio faz também existe na CLI (rode como administrador):

```powershell
winkit pendrive listar
winkit receita nova --pendrive E: --usuario Samuel --nome-pc MEU-PC
winkit coletar apps --pendrive E:
winkit apps marcar discord 7zip vscode --pendrive E:
winkit apps baixar --pendrive E:
winkit coletar backups --pendrive E: --adicionar-recomendados
winkit backup capturar --pendrive E:
winkit coletar drivers --pendrive E:
winkit plano --pendrive E:
winkit construir --pendrive E:
winkit validar --pendrive E:
```

## Estado do projeto

**Pré-alpha.** A versão 1 está implementada e testada automaticamente: 569 testes em Linux e Windows, com executáveis gerados e testados no CI. A validação em máquina virtual e em PC real segue os roteiros de [`docs/validacao/`](docs/validacao/). Veja [`docs/STATUS.md`](docs/STATUS.md).

> ⚠️ Use primeiro numa máquina virtual ([`docs/validacao/AMBIENTE_VM.md`](docs/validacao/AMBIENTE_VM.md)). Valores de registro e nomes de pacotes do Windows mudam entre versões.

## Compilar a partir do código

```powershell
git clone https://github.com/luckasiasantos-source/Iso-Modify-Win11
cd Iso-Modify-Win11
uv sync                     # Python 3.12 e dependências
uv run pytest               # testes
powershell -ExecutionPolicy Bypass -File packaging\build.ps1   # gera dist\WinKit-<versão>
```

## Arquitetura

O código é Python 3.12 + PySide6, em camadas com regras verificadas automaticamente:

| Camada | O que tem |
|---|---|
| `core/` | Lógica pura (receita, planejador de fases, moldes de caminho, XML, Ventoy, manifesto), testável sem Windows |
| `platform/` | Tudo que toca o Windows (registro, PowerShell, robocopy, VSS, pnputil, winget, Appx), atrás de interfaces com versões falsas para testes |
| `collector/`, `builder/`, `agent/` | Casos de uso: coletar do PC atual, montar o pendrive, configurar o Windows novo |
| `ui/`, `studio/`, `agent/ui/` | Interface no estilo macOS (tema claro/escuro) |
| `data/` | Catálogos versionados: apps conhecidos, ajustes (com fonte e "desfazer"), bloatware, edições |

Documentação completa:

- [`docs/PLANO.md`](docs/PLANO.md): o produto e o desenho
- [`docs/ARQUITETURA.md`](docs/ARQUITETURA.md): camadas, regras do código e registro de decisões
- [`docs/STATUS.md`](docs/STATUS.md), [`docs/DIVIDAS_TECNICAS.md`](docs/DIVIDAS_TECNICAS.md), [`docs/INCIDENTES.md`](docs/INCIDENTES.md), [`docs/CHANGELOG.md`](docs/CHANGELOG.md)

## Contribuir

Contribuições são bem-vindas, principalmente:

- entradas no catálogo de apps (`src/winkit/data/app_catalog.yaml`): pastas de configuração e parâmetros silenciosos;
- ajustes e bloatware validados em versões novas do Windows;
- relatos de teste em VM ou PC real, seguindo os roteiros de `docs/validacao/`.

Antes de abrir um PR, leia o [`CONTRIBUTING.md`](CONTRIBUTING.md) e rode `scripts/check.sh`.

## Aviso

**Versão pré-alpha de um projeto pessoal.** O WinKit foi feito para uso próprio, como um teste, e não como um produto lançado. Ele está aberto para quem quiser usar, mas quem usa é, na prática, um testador (beta tester), com todos os poréns disso: pode faltar recurso, mudar sem aviso e não há suporte garantido.

**O WinKit é 100% vibe-codado.** Todo o código, os testes e a documentação foram escritos por inteligência artificial, sem auditoria humana completa. Os testes automáticos passam, mas eles não substituem uma instalação real, que ainda não foi feita.

Ao baixar, compilar ou usar o WinKit, você concorda que:

- **o uso é inteiramente por sua conta e risco**;
- **toda a responsabilidade é sua**, de quem baixou e usou: por perda de dados, por um Windows que não inicia, por falhas de segurança, por qualquer dano ao seu computador ou a terceiros;
- o autor e os contribuidores **não se responsabilizam por nada**, conforme as seções 7 (sem garantias) e 8 (limitação de responsabilidade) da [licença](LICENSE) e o arquivo [`NOTICE`](NOTICE);
- cabe a você testar (de preferência numa máquina virtual), conferir se funciona e fazer backup antes.

Encontrou um erro ou uma falha de segurança? [Abra uma issue](https://github.com/luckasiasantos-source/Iso-Modify-Win11/issues).

O WinKit automatiza a instalação de um Windows que você tem direito de usar. Ele não ativa o Windows nem contorna licenciamento: as chaves usadas só selecionam a edição no instalador.

## Licença

[Apache License 2.0](LICENSE). Leia também o [`NOTICE`](NOTICE).

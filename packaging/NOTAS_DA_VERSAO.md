**Português** · [English](#english) · [Español](#español)

> [!CAUTION]
> **Pré-alpha, 100% vibe-codado, projeto pessoal. Use por sua conta e risco.**
> O WinKit foi feito para uso próprio, como um teste, e não como um produto lançado. Quem usar esta versão é, na prática, um testador (beta tester): pode faltar recurso, mudar sem aviso e não há suporte garantido.
> Todo o código foi escrito por inteligência artificial, sem auditoria humana completa, e esta versão **ainda não foi validada numa instalação real do Windows**. Pode ter erros e falhas de segurança que causem perda de dados ou um Windows inutilizável. **Toda a responsabilidade é de quem baixa e usa**; o autor não se responsabiliza por nenhum dano (seções 7 e 8 da licença Apache 2.0 e arquivo `NOTICE`). Teste primeiro numa máquina virtual e faça backup antes.

## Novidades desta versão

Esta é a **versão 3 completa** (marcos M19 a M26). Tudo o que veio de novo desde a 0.9.0:

- **Mais rápido, nítido em 4K, logo novo** e janela com a moldura no tema do aplicativo.
- **Modo em etapas** (Voltar, Pular, Avançar) junto com a barra lateral, começando pela etapa **Começar**: qual Windows (11, 10, 8.1 ou 7; 32 ou 64 bits) e como ele chega ao PC.
- **Ventoy e Rufus** baixados do site oficial, conferidos e abertos para você gravar; o WinKit mostra o que o Rufus configurou.
- **Baixar o Windows** oficial da Microsoft, com velocidade, tempo restante, pausa e retomada.
- **Backup do PC para outro disco** (HD, SSD ou pendrive), conferido arquivo a arquivo e sem apagar nada; **trazer de volta** à mão ou na instalação; etapa **Antes de formatar** (backup, BitLocker com a chave exportada, ativação).
- **ISO personalizada**: uma cópia com edições, drivers, atualizações e sem apps de fábrica; **autossuficiente** com o WinKit inteiro dentro. A original nunca é modificada.
- **O WinKit grava o pendrive** sozinho (UEFI, BIOS ou os dois), apagando só o pendrive que você confirmar digitando a letra.
- **Windows 7 e 8.1** em modo limitado, com o 7 "SP2" (Convenience Rollup) na ISO personalizada.
- Comandos novos na linha de comando: `iso`, `pendrive gravar`, `backup-pc` e `ferramenta`.

**Ainda não validado em instalação real.** As hipóteses H1 a H51 (lista em `docs/STATUS.md`) dependem do comportamento do Windows, do Ventoy e do Rufus e só serão confirmadas com os roteiros de `docs/validacao/` (M2 a M25). O que ficou provisório está em `docs/DIVIDAS_TECNICAS.md`.

## Como usar

1. Baixe o `WinKit-…-windows-x64.zip` abaixo e extraia numa pasta.
2. Abra `winkit-studio\winkit-studio.exe` (ele pede administrador).
3. Siga a barra lateral e, no fim, clique em **Construir pendrive**.
4. Dê boot pelo Ventoy, escolha a ISO original do Windows 11 e o modelo `winkit-…`.

Os executáveis **não são assinados**, então o Windows SmartScreen pode avisar ("Mais informações" → "Executar assim mesmo"). Para conferir o download, compare o SHA-256 do `.zip` com o arquivo `.sha256`:

```powershell
Get-FileHash .\WinKit-*-windows-x64.zip -Algorithm SHA256
```

Requisitos: Windows 10 ou 11 (64 bits) no PC onde você monta o pendrive; pendrive com o [Ventoy](https://www.ventoy.net) e uma ISO original do Windows 11. Encontrou um erro? [Abra uma issue](https://github.com/luckasiasantos-source/WinKit/issues).

---

## English

> [!CAUTION]
> **Pre-alpha, 100% vibe-coded, personal project. Use at your own risk.** WinKit was made for the author's own use as an experiment; anyone using this version is, in practice, a tester. All code was written by AI without a full human review, and this version **has not yet been validated on a real Windows install**. It may have bugs and security flaws that cause data loss or an unusable Windows. **All responsibility lies with whoever downloads and uses it**; the author accepts no liability (sections 7 and 8 of the Apache 2.0 license and the `NOTICE` file). Test it in a virtual machine first and back up beforehand.

**New in this version:** this is the **complete version 3** (milestones M19–M26): faster, sharp on 4K, new logo and themed window; **step-by-step mode** starting with **Get started** (Windows 11, 10, 8.1 or 7; 32/64-bit; how it gets to the PC); **Ventoy and Rufus** downloaded from the official site and opened for you; **download Windows** from Microsoft with pause and resume; **PC backup to another disk**, checked and never deleting, with restore by hand or during setup and a **Before formatting** checklist (BitLocker key export); **custom ISO** (a copy; self-contained with WinKit inside; the original is never modified); **WinKit writes the USB drive** (only the drive you confirm by typing its letter); **Windows 7 and 8.1** in limited mode; new CLI commands `iso`, `pendrive gravar`, `backup-pc`, `ferramenta`. **Not yet validated on a real install:** hypotheses H1–H51 are listed in `docs/STATUS.md`.

**How to use:** download `WinKit-…-windows-x64.zip` below, extract it, open `winkit-studio\winkit-studio.exe` (it asks for administrator), follow the sidebar and click **Build USB drive** at the end. Boot from Ventoy, choose the original Windows 11 ISO and the `winkit-…` template. The executables are not signed: if SmartScreen warns you, click "More info" → "Run anyway". Check the download against the `.sha256` file.

---

## Español

> [!CAUTION]
> **Pre-alfa, 100% hecho con vibe coding, proyecto personal. Úsalo bajo tu propio riesgo.** WinKit se hizo para uso propio, como una prueba; quien use esta versión es, en la práctica, un probador. Todo el código lo escribió IA sin auditoría humana completa, y esta versión **aún no se validó en una instalación real de Windows**. Puede tener errores y fallas de seguridad que causen pérdida de datos o un Windows inutilizable. **Toda la responsabilidad es de quien lo descarga y lo usa**; el autor no se responsabiliza por nada (secciones 7 y 8 de la licencia Apache 2.0 y archivo `NOTICE`). Pruébalo primero en una máquina virtual y haz una copia de seguridad antes.

**Novedades de esta versión:** es la **versión 3 completa** (hitos M19–M26): más rápido, nítido en 4K, logo nuevo y ventana con el tema; **modo por pasos** que empieza con **Empezar** (Windows 11, 10, 8.1 o 7; 32/64 bits; cómo llega al PC); **Ventoy y Rufus** descargados del sitio oficial y abiertos para ti; **descargar Windows** de Microsoft con pausa y reanudación; **backup del PC a otro disco**, verificado y sin borrar nada, con restauración a mano o en la instalación y la lista **Antes de formatear** (exportar la clave de BitLocker); **ISO personalizada** (una copia; autosuficiente con WinKit dentro; la original nunca se modifica); **WinKit graba la memoria USB** (solo la que confirmas escribiendo su letra); **Windows 7 y 8.1** en modo limitado; comandos nuevos `iso`, `pendrive gravar`, `backup-pc`, `ferramenta`. **Aún no validado en una instalación real:** las hipótesis H1–H51 están en `docs/STATUS.md`.

**Cómo usarlo:** descarga `WinKit-…-windows-x64.zip` abajo, descomprímelo, abre `winkit-studio\winkit-studio.exe` (pide permisos de administrador), sigue la barra lateral y haz clic en **Preparar memoria USB** al final. Arranca desde Ventoy, elige la ISO original de Windows 11 y la plantilla `winkit-…`. Los ejecutables no están firmados: si SmartScreen avisa, haz clic en "Más información" → "Ejecutar de todas formas". Compara la descarga con el archivo `.sha256`.

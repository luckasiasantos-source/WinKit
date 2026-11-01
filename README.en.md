<div align="center">

<img src="docs/imagens/en/studio-pendrive.png" alt="WinKit Studio" width="820">

<img src="docs/imagens/logo.png" alt="WinKit logo" width="112">

# WinKit

[Português](README.md) · **English** · [Español](README.es.md)

**Install Windows already the way you like it — drivers, apps, settings and privacy — from a Ventoy USB drive (or one made by Rufus or Microsoft), without modifying the original ISO. Or apply the same recipe to the Windows you already have.**

[![CI](https://github.com/luckasiasantos-source/WinKit/actions/workflows/ci.yml/badge.svg)](https://github.com/luckasiasantos-source/WinKit/actions/workflows/ci.yml)
![Python 3.12](https://img.shields.io/badge/python-3.12-blue)
![Windows 11](https://img.shields.io/badge/Windows-11-0078D4)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)
![100% vibe-coded](https://img.shields.io/badge/100%25-vibe--coded-red)
![Pre-alpha](https://img.shields.io/badge/stage-pre--alpha-orange)

</div>

> [!CAUTION]
> **Pre-alpha, 100% vibe-coded, personal project. Use at your own risk.**
> WinKit was made for the author's own use, as an experiment, not as a released product. Anyone who uses it is, in practice, a tester.
> All of WinKit's code was written by artificial intelligence, without a full human review, and it **has not yet been validated on a real Windows install**. It touches sensitive parts of the system (setup, registry, drivers, accounts, files) and may have bugs or security flaws that cause data loss or an unusable Windows.
> **All responsibility lies with whoever downloads and uses it.** The author accepts no liability for any damage, loss or security flaw. Test it in a virtual machine first, back up beforehand and [report the bugs you find](https://github.com/luckasiasantos-source/WinKit/issues). See the [Warning](#warning) section.

---

## Why it exists

Reinstalling Windows is quick; making it your own is what takes time: hunting for drivers, downloading and installing app after app, setting each one up again, removing the extras, turning off telemetry, fixing the taskbar…

WinKit does it all at once. You build a **recipe** on your current PC, and the Ventoy USB drive installs Windows already set up, from the same original ISO you downloaded from Microsoft.

## What it does

| | |
|---|---|
| 🔌 **Ventoy, ISO untouched** | Uses Ventoy's `auto_install` plugin. Swap the ISO for a newer one and everything keeps working. One USB drive serves several ISOs. |
| 👤 **Local account** | No Microsoft account, no network and privacy screens. Language, keyboard, time zone and edition come from your current PC and can be changed in the recipe. |
| 💽 **Disk never encrypted by itself** | By default Windows does not turn on automatic device encryption — not even after you sign in with a Microsoft account. |
| 🧩 **Your PC's drivers** | Exports third-party drivers (network first) and installs them with `pnputil` before the first sign-in. |
| 📦 **Your apps** | Reads the apps installed on your PC; you pick the ones you want. Installs offline (installers downloaded with `winget download`) or through winget online. Closes apps opened by the installer and turns off auto-start. |
| 🗂️ **App settings** | Choose settings folders and files (Discord, VS Code, OBS, game saves…). They are copied to the USB drive with a shadow copy (even with the app open) and restored to the right place **before** you open the app on the new Windows. |
| 🧹 **Preinstalled apps** | Removes what you choose (list with risk levels) and keeps them from coming back with updates. |
| 🎛️ **Tweaks** | Privacy (minimum telemetry, advertising ID, Bing in Start, Copilot, Recall…), appearance (dark theme, left taskbar, classic context menu…), power. Applied to the default profile: your account is born already set up. |
| 🔄 **Windows Update** | Optional, at the end, through the official API. |
| 🪟 **First sign-in your way** | Silent (just a notice at the end), with a countdown or interactive — and items marked "ask" to decide at that moment. |
| 🧾 **Summary and logs** | HTML summary on the desktop and logs written back to the USB drive. |
| 🌎 **Three languages** | Portuguese, English and Spanish in Studio, on the command line and at first sign-in. Automatic from the Windows language or chosen in Preferences. |

### New in version 2

| | |
|---|---|
| 💡 **Suggestions of what to take** | WinKit looks at this PC and suggests the programs you use most, recommended settings, game saves and large folders on C:, always saying why. Nothing is added until you click "Add", and the analysis runs only on this PC. |
| 🖥️ **Apply to this PC** | The same recipe on an already installed Windows, without reinstalling: a preview of what changes, a restore point first and only the steps that are safe on a running system. |
| 💾 **Regular USB drive** | Besides Ventoy, it works with a USB drive made by Rufus or by Microsoft's Media Creation Tool. |
| 📶 **Network and system** | Wi-Fi networks connected before sign-in, Windows features (WSL, Sandbox, .NET 3.5…), missing drivers from Windows Update, secure DNS and ad blocking in `hosts`, network drives, maintenance tasks and environment variables. |
| 🎨 **Personalization** | Quick profiles (Gamer, Maximum privacy, Office, Developer), fonts, default apps, wallpaper and colors, browsers with extensions and search engine, and the Start menu and taskbar pins. |
| 🗃️ **Accounts, folders and games** | Extra accounts (administrator or standard), Documents and Downloads on another disk (found by serial number even if the letter changes), and Steam and Epic games on another disk showing up installed, without downloading again. |
| 📋 **Templates and shareable recipes** | Start from a ready template or import someone else's recipe, always with a preview. Exports never include your account, password, Wi-Fi or personal paths. |
| ⬆️ **Always-fresh installers** | "Check for updates" replaces old installers on the USB drive without redoing the recipe; the old version is only removed after the new one is in place. |
| 🕰️ **Windows 7 and 8.1** | In limited mode, 32 and 64-bit: unattended setup, drivers, programs with their own installer, settings, Wi-Fi and power, with a warning that they no longer get security fixes. Windows 7 "SP2" (Convenience Rollup) can go inside the custom ISO. |
| 🔥 **WinKit writes the USB drive** | No Ventoy or Rufus needed: pick the USB drive and the PC type (UEFI, BIOS or both) and confirm by typing its letter. Only USB drives are listed; internal disks and external HDDs never are. |
| 💿 **Custom ISO** | A **copy** of the ISO with the editions you want, this PC's drivers (so the installer sees the SSD), updates and without the checked preinstalled apps. It can be **self-contained**: all of WinKit goes inside and the ISO installs everything by itself. The original is never modified. |
| 🗄️ **Backup to another disk** | Copies your files to an HDD, SSD or USB drive before formatting, showing the disk type and the measured time; every file is checked and nothing is deleted. Later it brings them back by adding to what exists, by hand or during setup. The **Before formatting** step checks the backup, BitLocker (and exports the key) and activation. |
| 🔍 **Comparison with the old PC** | At the end of the install, the summary shows missing apps, devices without a driver and features that were not turned on. |

<div align="center">
<img src="docs/imagens/en/studio-templates.png" alt="Templates" width="820">
</div>

## How it works

```
 Your current PC              Ventoy USB drive                        New Windows
┌──────────────┐  writes   ┌────────────────────────────┐   boot   ┌───────────────────────────┐
│ WinKit Studio│ ────────► │ Original ISOs (untouched)  │ ───────► │ unattended setup           │
│  recipe      │           │ ventoy/ventoy.json + XML   │          │ Phase 1 (before sign-in):  │
│  apps        │           │ WinKit/                    │          │  drivers, bloatware,       │
│  drivers     │           │   recipe, installers,      │          │  tweaks, apps, backups     │
│  backups     │           │   drivers, backups, Agent  │          │ Phase 2 (after sign-in):   │
└──────────────┘           └────────────────────────────┘          │  per-user apps, winget,    │
                                                                    │  Windows Update, summary   │
                                                                    └───────────────────────────┘
```

1. **Studio** (or the command line) reads your PC and writes the recipe and all the content to the `WinKit\` folder of the USB drive.
2. Ventoy injects an `autounattend.xml` into the setup. You only choose the disk: WinKit **never** partitions or formats anything by itself.
3. During setup, a small script finds the USB drive and prepares the **Agent**.
4. The Agent does almost everything before the sign-in screen. What needs your user or the internet happens right after, in the background or with a window, as you choose.

## Getting started

### Requirements

- Windows 10 or 11 on the PC where you prepare the USB drive (Studio asks for administrator rights).
- A USB drive with [Ventoy](https://www.ventoy.net) installed and an original Windows 11 ISO.

### Use

1. Download `WinKit-…-windows-x64.zip` from the [**Releases**](https://github.com/luckasiasantos-source/WinKit/releases) page and extract it. Nothing to compile. The executables are not signed: if SmartScreen warns you, click "More info" → "Run anyway".
2. Open `winkit-studio\winkit-studio.exe`.
3. In the first step, **Get started**, choose Windows (11, 10, 8.1 or 7) and how it gets to the PC: **Ventoy** or **Rufus** (WinKit downloads it from the official site and opens it for you to write the USB drive) or Microsoft's tool. No ISO? The **Download Windows** step gets the official one from Microsoft, with pause and resume. Then go on with **Next** (or **Skip**) in the bottom bar, or click any section in the sidebar. The **Preferences** button changes language and theme.
4. Boot from Ventoy, choose the ISO and the `winkit-…` template. With a Rufus or Microsoft USB drive, just boot from it (see [`docs/RUFUS.md`](docs/RUFUS.md), in Portuguese).
5. To use the recipe on the Windows you already have, open **Apply to this PC** (Finish group): WinKit shows a preview and creates a restore point first.

### Command line

Everything Studio does is also available on the CLI (run as administrator). Command names are in Portuguese and also accept English aliases; use `--idioma en-US` for English messages:

```powershell
winkit --idioma en-US drive list
winkit recipe new --pendrive E: --usuario Sam --nome-pc MY-PC
winkit collect apps --pendrive E:
winkit apps select discord 7zip vscode --pendrive E:
winkit apps download --pendrive E:
winkit collect backups --pendrive E: --adicionar-recomendados
winkit backup capture --pendrive E:
winkit collect drivers --pendrive E:
winkit suggestions list --pendrive E:
winkit recipe template gamer --aplicar --pendrive E:
winkit dns set cloudflare --pendrive E:
winkit plan --pendrive E:
winkit build --pendrive E:
winkit validate --pendrive E:
winkit apply --pendrive E: --simular    # preview of "Apply to this PC"
```

## Project status

**Pre-alpha.** Versions 1 and 2 are implemented and automatically tested (over 700 tests on Linux and Windows, with executables built and smoke-tested in CI). The v2 plan is in [`docs/PLANO_V2.md`](docs/PLANO_V2.md) (in Portuguese); what is still provisional is in [`docs/DIVIDAS_TECNICAS.md`](docs/DIVIDAS_TECNICAS.md). Validation in a virtual machine and on a real PC follows the scripts in [`docs/validacao/`](docs/validacao/).

> ⚠️ Use it in a virtual machine first. Windows registry values and package names change between versions.

## Building from source

```powershell
git clone https://github.com/luckasiasantos-source/WinKit
cd WinKit
uv sync                     # Python 3.12 and dependencies
uv run pytest               # tests
powershell -ExecutionPolicy Bypass -File packaging\build.ps1   # creates dist\WinKit-<version>
```

## Architecture

Python 3.12 + PySide6, in layers whose rules are checked automatically:

| Layer | Contents |
|---|---|
| `core/` | Pure logic (recipe, phase planner, path templates, XML, Ventoy, manifest), testable without Windows |
| `platform/` | Everything that touches Windows (registry, PowerShell, robocopy, VSS, pnputil, winget, Appx), behind interfaces with fakes for tests |
| `collector/`, `builder/`, `agent/` | Use cases: collect from the current PC, build the USB drive, set up the new Windows |
| `ui/`, `studio/`, `agent/ui/` | macOS-style interface (light/dark theme) |
| `i18n/`, `data/` | Texts in three languages; versioned catalogs (known apps, tweaks with source and undo, bloatware, editions, Windows features, DNS and blocklists, quick profiles, game saves, recipe templates) |

The project documentation (`docs/`) is written in Portuguese; [`docs/ESTRUTURA.md`](docs/ESTRUTURA.md) has the project tree with what each code file does.

## Contributing

Contributions are welcome, especially:

- app catalog entries (`src/winkit/data/app_catalog.yaml`): settings folders and silent parameters;
- tweaks and bloatware validated on new Windows versions;
- corrections to the English and Spanish texts (`src/winkit/i18n/messages/`, `src/winkit/data/i18n_*.yaml`);
- test reports from a VM or real PC.

Before opening a PR, read [`CONTRIBUTING.md`](CONTRIBUTING.md) and run `scripts/check.sh`.

## Warning

**Pre-alpha version of a personal project.** WinKit was made for the author's own use, as an experiment, not as a released product. It is open to anyone who wants to use it, but whoever uses it is, in practice, a tester (beta tester), with all that this implies: features may be missing, things may change without notice and there is no guaranteed support.

**WinKit is 100% vibe-coded.** All the code, tests, documentation and the English and Spanish translations were written by artificial intelligence, without a full human review. The automated tests pass, but they do not replace a real install, which has not been done yet. "Apply to this PC" changes the Windows you use every day: use the preview and check the restore point first.

By downloading, building or using WinKit, you agree that:

- **you use it entirely at your own risk**;
- **all responsibility is yours**, whoever downloaded and used it: for data loss, for a Windows that does not boot, for security flaws, for any damage to your computer or to third parties;
- the author and contributors **are not liable for anything**, under sections 7 (disclaimer of warranty) and 8 (limitation of liability) of the [license](LICENSE) and the [`NOTICE`](NOTICE) file;
- it is up to you to test it (preferably in a virtual machine), check that it works and back up beforehand.

Found a bug or a security flaw? [Open an issue](https://github.com/luckasiasantos-source/WinKit/issues).

WinKit automates the installation of a Windows copy you are entitled to use. It does not activate Windows or bypass licensing: the keys it uses only select the edition in the installer.

## License

[Apache License 2.0](LICENSE). Also read the [`NOTICE`](NOTICE).

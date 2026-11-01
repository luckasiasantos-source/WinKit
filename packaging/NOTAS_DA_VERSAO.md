**Português** · [English](#english) · [Español](#español)

> [!CAUTION]
> **Pré-alpha, 100% vibe-codado, projeto pessoal. Use por sua conta e risco.**
> O WinKit foi feito para uso próprio, como um teste, e não como um produto lançado. Quem usar esta versão é, na prática, um testador (beta tester): pode faltar recurso, mudar sem aviso e não há suporte garantido.
> Todo o código foi escrito por inteligência artificial, sem auditoria humana completa, e esta versão **ainda não foi validada numa instalação real do Windows**. Pode ter erros e falhas de segurança que causem perda de dados ou um Windows inutilizável. **Toda a responsabilidade é de quem baixa e usa**; o autor não se responsabiliza por nenhum dano (seções 7 e 8 da licença Apache 2.0 e arquivo `NOTICE`). Teste primeiro numa máquina virtual e faça backup antes.

## Novidades desta versão

Primeira versão da v3 (M19), com correções que você sente no uso:

- **Mais rápido:** a janela abre na hora, com uma tela de abertura; a lista de pendrives e o espaço usado carregam em segundo plano, sem travar a janela.
- **Nítido em 4K:** ícones e logo desenhados na escala real da tela (150%, 250%…).
- **Janela mais bonita:** logo novo; barra de título, contorno e cantos no tema do aplicativo (Windows 11); barra de rolagem fina.
- **Testes numa VM:** scripts para criar uma VM Hyper-V de testes, com pontos de restauração (`scripts/vm`).

A versão 2 completa (0.9.0) trouxe sugestões do que levar, "Aplicar neste PC", pendrive do Rufus/Microsoft, Wi-Fi, recursos do Windows, DNS, personalização, contas, pastas e jogos em outro disco, modelos e a comparação com o PC antigo. **Ainda não validado em instalação real:** as hipóteses estão em `docs/STATUS.md`.

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

**New in this version:** first v3 release (M19): **faster** (the window opens right away with a splash screen; USB drives and used space load in the background), **sharp on 4K** screens (icons and logo drawn at the real screen scale), **nicer window** (new logo; title bar, border and corners follow the app theme on Windows 11; thin scroll bar) and **VM test scripts** (Hyper-V). Version 0.9.0 completed v2. **Not yet validated on a real install:** see the hypotheses in `docs/STATUS.md`.

**How to use:** download `WinKit-…-windows-x64.zip` below, extract it, open `winkit-studio\winkit-studio.exe` (it asks for administrator), follow the sidebar and click **Build USB drive** at the end. Boot from Ventoy, choose the original Windows 11 ISO and the `winkit-…` template. The executables are not signed: if SmartScreen warns you, click "More info" → "Run anyway". Check the download against the `.sha256` file.

---

## Español

> [!CAUTION]
> **Pre-alfa, 100% hecho con vibe coding, proyecto personal. Úsalo bajo tu propio riesgo.** WinKit se hizo para uso propio, como una prueba; quien use esta versión es, en la práctica, un probador. Todo el código lo escribió IA sin auditoría humana completa, y esta versión **aún no se validó en una instalación real de Windows**. Puede tener errores y fallas de seguridad que causen pérdida de datos o un Windows inutilizable. **Toda la responsabilidad es de quien lo descarga y lo usa**; el autor no se responsabiliza por nada (secciones 7 y 8 de la licencia Apache 2.0 y archivo `NOTICE`). Pruébalo primero en una máquina virtual y haz una copia de seguridad antes.

**Novedades de esta versión:** primera versión de la v3 (M19): **más rápido** (la ventana abre al instante con una pantalla de inicio; las memorias USB y el espacio usado cargan en segundo plano), **nítido en 4K** (iconos y logo dibujados a la escala real de la pantalla), **ventana más bonita** (logo nuevo; barra de título, borde y esquinas según el tema de la aplicación en Windows 11; barra de desplazamiento fina) y **scripts de VM de prueba** (Hyper-V). La 0.9.0 completó la v2. **Aún no validado en una instalación real:** ver las hipótesis en `docs/STATUS.md`.

**Cómo usarlo:** descarga `WinKit-…-windows-x64.zip` abajo, descomprímelo, abre `winkit-studio\winkit-studio.exe` (pide permisos de administrador), sigue la barra lateral y haz clic en **Preparar memoria USB** al final. Arranca desde Ventoy, elige la ISO original de Windows 11 y la plantilla `winkit-…`. Los ejecutables no están firmados: si SmartScreen avisa, haz clic en "Más información" → "Ejecutar de todas formas". Compara la descarga con el archivo `.sha256`.

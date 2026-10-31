**Português** · [English](#english) · [Español](#español)

> [!CAUTION]
> **Pré-alpha, 100% vibe-codado, projeto pessoal. Use por sua conta e risco.**
> O WinKit foi feito para uso próprio, como um teste, e não como um produto lançado. Quem usar esta versão é, na prática, um testador (beta tester): pode faltar recurso, mudar sem aviso e não há suporte garantido.
> Todo o código foi escrito por inteligência artificial, sem auditoria humana completa, e esta versão **ainda não foi validada numa instalação real do Windows**. Pode ter erros e falhas de segurança que causem perda de dados ou um Windows inutilizável. **Toda a responsabilidade é de quem baixa e usa**; o autor não se responsabiliza por nenhum dano (seções 7 e 8 da licença Apache 2.0 e arquivo `NOTICE`). Teste primeiro numa máquina virtual e faça backup antes.

## Novidades desta versão

Esta é a **versão 2 completa** (marcos M11 a M18). Tudo o que veio de novo desde a 0.1.0:

- **Sugestões do que levar:** o WinKit olha este PC e sugere os programas que você mais usa, configurações recomendadas, saves de jogos e pastas grandes no C:, sempre dizendo por quê.
- **Aplicar neste PC:** a mesma receita num Windows já instalado, com prévia e ponto de restauração.
- **Pendrive comum:** além do Ventoy, o pendrive do Rufus ou da Ferramenta de Criação de Mídia.
- **Rede e sistema:** Wi-Fi, recursos do Windows (WSL, Sandbox, .NET 3.5…), drivers que faltam, DNS seguro e bloqueios no `hosts`, unidades de rede, manutenção e variáveis de ambiente.
- **Personalização:** perfis rápidos, fontes, apps padrão, aparência, navegadores e Iniciar/barra.
- **Contas, pastas e jogos:** contas extras, pastas do usuário em outro disco e jogos da Steam/Epic sem baixar de novo.
- **Modelos e receitas compartilháveis**, **atualização dos instaladores do pendrive** e **comparação com o PC antigo** no resumo final.
- O aplicativo em **português, inglês e espanhol**.

**Ainda não validado em instalação real.** As hipóteses H1 a H35 (lista em `docs/STATUS.md`) dependem do comportamento do Windows e do Ventoy e só serão confirmadas com os roteiros de `docs/validacao/` (M2 a M17). O que ficou provisório está em `docs/DIVIDAS_TECNICAS.md`.

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

**New in this version:** this is the **complete version 2** (milestones M11–M18): suggestions of what to take, Apply to this PC (preview and restore point), Rufus and Media Creation Tool USB drives, Wi-Fi, Windows features, missing drivers, secure DNS and `hosts` blocking, network drives, maintenance, environment variables, quick profiles, fonts, default apps, appearance, browsers, Start/taskbar, extra accounts, user folders and games on another disk, templates and shareable recipes, updating the installers on the USB drive, a comparison with the old PC in the final summary, and the app in Portuguese, English and Spanish. **Not yet validated on a real install:** hypotheses H1–H35 (listed in `docs/STATUS.md`) depend on how Windows and Ventoy behave and will only be confirmed with the scripts in `docs/validacao/`.

**How to use:** download `WinKit-…-windows-x64.zip` below, extract it, open `winkit-studio\winkit-studio.exe` (it asks for administrator), follow the sidebar and click **Build USB drive** at the end. Boot from Ventoy, choose the original Windows 11 ISO and the `winkit-…` template. The executables are not signed: if SmartScreen warns you, click "More info" → "Run anyway". Check the download against the `.sha256` file.

---

## Español

> [!CAUTION]
> **Pre-alfa, 100% hecho con vibe coding, proyecto personal. Úsalo bajo tu propio riesgo.** WinKit se hizo para uso propio, como una prueba; quien use esta versión es, en la práctica, un probador. Todo el código lo escribió IA sin auditoría humana completa, y esta versión **aún no se validó en una instalación real de Windows**. Puede tener errores y fallas de seguridad que causen pérdida de datos o un Windows inutilizable. **Toda la responsabilidad es de quien lo descarga y lo usa**; el autor no se responsabiliza por nada (secciones 7 y 8 de la licencia Apache 2.0 y archivo `NOTICE`). Pruébalo primero en una máquina virtual y haz una copia de seguridad antes.

**Novedades de esta versión:** es la **versión 2 completa** (hitos M11–M18): sugerencias de qué llevar, Aplicar en este PC (vista previa y punto de restauración), memorias USB de Rufus y de la Herramienta de creación de medios, Wi-Fi, características de Windows, controladores que faltan, DNS seguro y bloqueo en `hosts`, unidades de red, mantenimiento, variables de entorno, perfiles rápidos, fuentes, aplicaciones predeterminadas, apariencia, navegadores, Inicio/barra, cuentas adicionales, carpetas del usuario y juegos en otro disco, plantillas y recetas compartibles, actualización de los instaladores de la memoria USB, comparación con el PC antiguo en el resumen final y la aplicación en portugués, inglés y español. **Aún no validado en una instalación real:** las hipótesis H1–H35 (lista en `docs/STATUS.md`) dependen del comportamiento de Windows y Ventoy y solo se confirmarán con los guiones de `docs/validacao/`.

**Cómo usarlo:** descarga `WinKit-…-windows-x64.zip` abajo, descomprímelo, abre `winkit-studio\winkit-studio.exe` (pide permisos de administrador), sigue la barra lateral y haz clic en **Preparar memoria USB** al final. Arranca desde Ventoy, elige la ISO original de Windows 11 y la plantilla `winkit-…`. Los ejecutables no están firmados: si SmartScreen avisa, haz clic en "Más información" → "Ejecutar de todas formas". Compara la descarga con el archivo `.sha256`.

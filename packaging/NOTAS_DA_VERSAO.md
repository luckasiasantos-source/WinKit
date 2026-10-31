**Português** · [English](#english) · [Español](#español)

> [!CAUTION]
> **Pré-alpha, 100% vibe-codado, projeto pessoal. Use por sua conta e risco.**
> O WinKit foi feito para uso próprio, como um teste, e não como um produto lançado. Quem usar esta versão é, na prática, um testador (beta tester): pode faltar recurso, mudar sem aviso e não há suporte garantido.
> Todo o código foi escrito por inteligência artificial, sem auditoria humana completa, e esta versão **ainda não foi validada numa instalação real do Windows**. Pode ter erros e falhas de segurança que causem perda de dados ou um Windows inutilizável. **Toda a responsabilidade é de quem baixa e usa**; o autor não se responsabiliza por nenhum dano (seções 7 e 8 da licença Apache 2.0 e arquivo `NOTICE`). Teste primeiro numa máquina virtual e faça backup antes.

## Novidades desta versão

- **Pastas do usuário em outro disco:** Documentos, Downloads e as outras pastas num outro disco; a próxima formatação do C: não apaga nada e o Windows novo já aponta para lá. Discos achados pelo número de série, mesmo se a letra mudar.
- **Jogos sem baixar de novo:** bibliotecas da Steam e jogos da Epic em outro disco aparecem instalados.
- **Contas extras:** outras contas locais (administrador ou padrão), com a senha trocada no primeiro acesso.

Versões anteriores: perfis rápidos, fontes, apps padrão, aparência, navegadores e Iniciar/barra (0.6.0); Wi-Fi, recursos do Windows, drivers que faltam, DNS e bloqueios, unidades de rede, manutenção e variáveis de ambiente (0.5.0); pendrive do Rufus ou da Microsoft, "Aplicar neste PC" com prévia e ponto de restauração, e o aplicativo em português, inglês e espanhol.

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

**New in this version:** **user folders on another disk** (Documents, Downloads and the others stay on a data disk; the next C: format erases nothing and the new Windows already points there; disks found by serial number even if the letter changes); **games without downloading again** (Steam libraries and Epic games on another disk show up installed); **extra accounts** (administrator or standard, password changed at first sign-in). Version 0.6.0 added quick profiles, fonts, default apps, appearance, browsers and Start/taskbar; 0.5.0 added Wi-Fi, Windows features, missing drivers, DNS, network drives, maintenance and environment variables.

**How to use:** download `WinKit-…-windows-x64.zip` below, extract it, open `winkit-studio\winkit-studio.exe` (it asks for administrator), follow the sidebar and click **Build USB drive** at the end. Boot from Ventoy, choose the original Windows 11 ISO and the `winkit-…` template. The executables are not signed: if SmartScreen warns you, click "More info" → "Run anyway". Check the download against the `.sha256` file.

---

## Español

> [!CAUTION]
> **Pre-alfa, 100% hecho con vibe coding, proyecto personal. Úsalo bajo tu propio riesgo.** WinKit se hizo para uso propio, como una prueba; quien use esta versión es, en la práctica, un probador. Todo el código lo escribió IA sin auditoría humana completa, y esta versión **aún no se validó en una instalación real de Windows**. Puede tener errores y fallas de seguridad que causen pérdida de datos o un Windows inutilizable. **Toda la responsabilidad es de quien lo descarga y lo usa**; el autor no se responsabiliza por nada (secciones 7 y 8 de la licencia Apache 2.0 y archivo `NOTICE`). Pruébalo primero en una máquina virtual y haz una copia de seguridad antes.

**Novedades de esta versión:** **carpetas del usuario en otro disco** (Documentos, Descargas y las demás quedan en un disco de datos; el próximo formateo de C: no borra nada y el Windows nuevo ya apunta allí; discos encontrados por número de serie aunque cambie la letra); **juegos sin volver a descargar** (bibliotecas de Steam y juegos de Epic en otro disco aparecen instalados); **cuentas adicionales** (administrador o estándar, contraseña cambiada en el primer acceso). La 0.6.0 agregó perfiles rápidos, fuentes, aplicaciones predeterminadas, apariencia, navegadores e Inicio/barra; la 0.5.0, Wi-Fi, características de Windows, controladores que faltan, DNS, unidades de red, mantenimiento y variables de entorno.

**Cómo usarlo:** descarga `WinKit-…-windows-x64.zip` abajo, descomprímelo, abre `winkit-studio\winkit-studio.exe` (pide permisos de administrador), sigue la barra lateral y haz clic en **Preparar memoria USB** al final. Arranca desde Ventoy, elige la ISO original de Windows 11 y la plantilla `winkit-…`. Los ejecutables no están firmados: si SmartScreen avisa, haz clic en "Más información" → "Ejecutar de todas formas". Compara la descarga con el archivo `.sha256`.

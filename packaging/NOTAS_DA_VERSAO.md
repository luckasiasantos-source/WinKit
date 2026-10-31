**Português** · [English](#english) · [Español](#español)

> [!CAUTION]
> **Pré-alpha, 100% vibe-codado, projeto pessoal. Use por sua conta e risco.**
> O WinKit foi feito para uso próprio, como um teste, e não como um produto lançado. Quem usar esta versão é, na prática, um testador (beta tester): pode faltar recurso, mudar sem aviso e não há suporte garantido.
> Todo o código foi escrito por inteligência artificial, sem auditoria humana completa, e esta versão **ainda não foi validada numa instalação real do Windows**. Pode ter erros e falhas de segurança que causem perda de dados ou um Windows inutilizável. **Toda a responsabilidade é de quem baixa e usa**; o autor não se responsabiliza por nenhum dano (seções 7 e 8 da licença Apache 2.0 e arquivo `NOTICE`). Teste primeiro numa máquina virtual e faça backup antes.

## Novidades desta versão

- **Wi-Fi já conectado:** as redes salvas neste PC conectam no Windows novo antes do primeiro login (com opção de levar sem a senha). A senha nunca vai para os logs, mas fica legível no pendrive: guarde-o bem.
- **Recursos do Windows:** WSL, Área Restrita, Hyper-V, .NET 3.5, OpenSSH e outros ligados na instalação. O .NET 3.5 instala sem internet, pela ISO original montada só para leitura.
- **Dispositivos sem driver:** no fim, o WinKit procura no Windows Update só os drivers que faltaram e mostra no resumo o que sobrou.
- **DNS e bloqueios:** Cloudflare, Quad9, Google, AdGuard ou NextDNS, com DNS criptografado no Windows 11, e bloqueio opcional de anúncios e rastreadores pelo arquivo `hosts` (dá para desfazer).
- **Unidades de rede** do PC antigo reaparecem no novo.
- **Manutenção:** apps atualizados pelo winget toda semana, Sensor de Armazenamento e otimização do disco.
- **Variáveis de ambiente e PATH:** leve `JAVA_HOME`, `GOPATH` e pastas do PATH; nada que já exista é sobrescrito sem você pedir.

Versões anteriores: pendrive do Rufus ou da Microsoft, "Aplicar neste PC" com prévia e ponto de restauração, e o aplicativo em português, inglês e espanhol.

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

**New in this version:** saved **Wi-Fi** networks connect on the new Windows before the first sign-in (optionally without the password; passwords never go to logs but are readable on the USB drive); **Windows features** such as WSL, Sandbox, Hyper-V, .NET 3.5 (installed offline from the original ISO mounted read-only) and OpenSSH; **devices without drivers** are looked up on Windows Update and listed in the summary; **DNS and blocking** (Cloudflare, Quad9, Google, AdGuard, NextDNS, encrypted DNS on Windows 11, optional ad and tracker blocking in `hosts`, undoable); **network drives**; **maintenance** (weekly winget updates, Storage Sense, disk optimization); **environment variables and PATH** (never overwritten without asking). Earlier versions added Rufus/Microsoft USB drives, **Apply to this PC** with preview and restore point, and Portuguese, English and Spanish.

**How to use:** download `WinKit-…-windows-x64.zip` below, extract it, open `winkit-studio\winkit-studio.exe` (it asks for administrator), follow the sidebar and click **Build USB drive** at the end. Boot from Ventoy, choose the original Windows 11 ISO and the `winkit-…` template. The executables are not signed: if SmartScreen warns you, click "More info" → "Run anyway". Check the download against the `.sha256` file.

---

## Español

> [!CAUTION]
> **Pre-alfa, 100% hecho con vibe coding, proyecto personal. Úsalo bajo tu propio riesgo.** WinKit se hizo para uso propio, como una prueba; quien use esta versión es, en la práctica, un probador. Todo el código lo escribió IA sin auditoría humana completa, y esta versión **aún no se validó en una instalación real de Windows**. Puede tener errores y fallas de seguridad que causen pérdida de datos o un Windows inutilizable. **Toda la responsabilidad es de quien lo descarga y lo usa**; el autor no se responsabiliza por nada (secciones 7 y 8 de la licencia Apache 2.0 y archivo `NOTICE`). Pruébalo primero en una máquina virtual y haz una copia de seguridad antes.

**Novedades de esta versión:** las redes **Wi-Fi** guardadas se conectan en el Windows nuevo antes del primer inicio de sesión (opcionalmente sin la contraseña; nunca va a los registros, pero queda legible en la memoria USB); **características de Windows** como WSL, Sandbox, Hyper-V, .NET 3.5 (instalado sin internet desde la ISO original montada solo para lectura) y OpenSSH; los **dispositivos sin controlador** se buscan en Windows Update y se listan en el resumen; **DNS y bloqueos** (Cloudflare, Quad9, Google, AdGuard, NextDNS, DNS cifrado en Windows 11, bloqueo opcional de anuncios y rastreadores en `hosts`, reversible); **unidades de red**; **mantenimiento** (actualización semanal con winget, Sensor de almacenamiento, optimización del disco); **variables de entorno y PATH** (nunca se sobrescriben sin pedirlo). Las versiones anteriores agregaron memorias USB de Rufus/Microsoft, **Aplicar en este PC** con vista previa y punto de restauración, y portugués, inglés y español.

**Cómo usarlo:** descarga `WinKit-…-windows-x64.zip` abajo, descomprímelo, abre `winkit-studio\winkit-studio.exe` (pide permisos de administrador), sigue la barra lateral y haz clic en **Preparar memoria USB** al final. Arranca desde Ventoy, elige la ISO original de Windows 11 y la plantilla `winkit-…`. Los ejecutables no están firmados: si SmartScreen avisa, haz clic en "Más información" → "Ejecutar de todas formas". Compara la descarga con el archivo `.sha256`.

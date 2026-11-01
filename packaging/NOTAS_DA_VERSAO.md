**Português** · [English](#english) · [Español](#español)

> [!CAUTION]
> **Pré-alpha, 100% vibe-codado, projeto pessoal. Use por sua conta e risco.**
> O WinKit foi feito para uso próprio, como um teste, e não como um produto lançado. Quem usar esta versão é, na prática, um testador (beta tester): pode faltar recurso, mudar sem aviso e não há suporte garantido.
> Todo o código foi escrito por inteligência artificial, sem auditoria humana completa, e esta versão **ainda não foi validada numa instalação real do Windows**. Pode ter erros e falhas de segurança que causem perda de dados ou um Windows inutilizável. **Toda a responsabilidade é de quem baixa e usa**; o autor não se responsabiliza por nenhum dano (seções 7 e 8 da licença Apache 2.0 e arquivo `NOTICE`). Teste primeiro numa máquina virtual e faça backup antes.

## Novidades desta versão

- **Backup do PC para outro disco:** escolha um HD, SSD ou pendrive (o WinKit mostra o tipo e mede a velocidade), as pastas a levar e veja o tempo previsto. Cada arquivo é conferido, arquivos abertos são copiados pela cópia de sombra, dá para pausar e continuar, e nada é apagado. Opcional: compactar em .zip.
- **Trazer de volta:** "Restaurar aqui" num PC qualquer, ou automático na instalação; sempre soma ao que existe, sem trocar nada.
- **Antes de formatar:** confere o backup, o BitLocker (com botão para exportar a chave de recuperação) e a ativação do Windows, e só então diz "Pode formatar".

- **Baixar o Windows:** nova etapa que baixa a ISO oficial da Microsoft (Windows 11 ou 10, 32 ou 64 bits no 10, no idioma escolhido), com porcentagem, velocidade e tempo restante; dá para pausar e continuar depois, até fechando o WinKit. No fim, a ISO é conferida e pode ir direto para o pendrive Ventoy ou para o Rufus.

- **Modo em etapas:** botões Voltar, Pular e Avançar na parte de baixo, com "Etapa n de N"; a barra lateral continua para ir direto a qualquer seção. A revisão lista o que você pulou.
- **Etapa Começar:** escolha o Windows (11 ou 10, 32 ou 64 bits no 10) e como ele chega ao PC. Para **Ventoy** e **Rufus**, o WinKit baixa o programa do site oficial, confere e abre para você gravar o pendrive; o Rufus já abre com a ISO.
- **Opções do Rufus:** o WinKit mostra o que o Rufus tinha configurado no pendrive (sem TPM, conta local…) e se a receita também faz.
- Da 0.10.0: Studio mais rápido, nítido em 4K, logo novo e moldura da janela no tema.

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

**New in this version:** **PC backup to another disk** (disk type and measured speed, every file checked, shadow copy for open files, pause/resume, optional .zip, never deletes; bring it back by hand or during setup, always adding); **Before formatting** checklist (backup, BitLocker with recovery key export, activation); **Download Windows** step (official ISO from Microsoft, with progress, speed, time left, pause and resume; then copy to the Ventoy drive or open in Rufus); **step-by-step mode** (Back, Skip and Next at the bottom, "Step n of N"; the sidebar still works and the review lists skipped steps); a **Get started** step to choose Windows (11 or 10) and how it gets to the PC; for **Ventoy** and **Rufus**, WinKit downloads the program from the official site, verifies it and opens it for you; WinKit shows the options **Rufus** had set on the USB drive. From 0.10.0: faster, sharp on 4K, new logo and themed window frame. **Not yet validated on a real install:** see the hypotheses in `docs/STATUS.md`.

**How to use:** download `WinKit-…-windows-x64.zip` below, extract it, open `winkit-studio\winkit-studio.exe` (it asks for administrator), follow the sidebar and click **Build USB drive** at the end. Boot from Ventoy, choose the original Windows 11 ISO and the `winkit-…` template. The executables are not signed: if SmartScreen warns you, click "More info" → "Run anyway". Check the download against the `.sha256` file.

---

## Español

> [!CAUTION]
> **Pre-alfa, 100% hecho con vibe coding, proyecto personal. Úsalo bajo tu propio riesgo.** WinKit se hizo para uso propio, como una prueba; quien use esta versión es, en la práctica, un probador. Todo el código lo escribió IA sin auditoría humana completa, y esta versión **aún no se validó en una instalación real de Windows**. Puede tener errores y fallas de seguridad que causen pérdida de datos o un Windows inutilizable. **Toda la responsabilidad es de quien lo descarga y lo usa**; el autor no se responsabiliza por nada (secciones 7 y 8 de la licencia Apache 2.0 y archivo `NOTICE`). Pruébalo primero en una máquina virtual y haz una copia de seguridad antes.

**Novedades de esta versión:** **backup del PC a otro disco** (tipo de disco y velocidad medida, cada archivo verificado, instantánea para archivos abiertos, pausa/reanudación, .zip opcional, nunca borra; traerlo de vuelta a mano o en la instalación, siempre sumando); lista **Antes de formatear** (backup, BitLocker con exportación de la clave, activación); paso **Descargar Windows** (ISO oficial de Microsoft, con progreso, velocidad, tiempo restante, pausa y reanudación; luego copiar a la memoria Ventoy o abrir en Rufus); **modo por pasos** (Atrás, Omitir y Siguiente abajo, "Paso n de N"; la barra lateral sigue y la revisión lista lo omitido); un paso **Empezar** para elegir Windows (11 o 10) y cómo llega al PC; para **Ventoy** y **Rufus**, WinKit descarga el programa del sitio oficial, lo verifica y lo abre; WinKit muestra las opciones que **Rufus** había configurado. De la 0.10.0: más rápido, nítido en 4K, logo nuevo y marco de ventana con el tema. **Aún no validado en una instalación real:** ver las hipótesis en `docs/STATUS.md`.

**Cómo usarlo:** descarga `WinKit-…-windows-x64.zip` abajo, descomprímelo, abre `winkit-studio\winkit-studio.exe` (pide permisos de administrador), sigue la barra lateral y haz clic en **Preparar memoria USB** al final. Arranca desde Ventoy, elige la ISO original de Windows 11 y la plantilla `winkit-…`. Los ejecutables no están firmados: si SmartScreen avisa, haz clic en "Más información" → "Ejecutar de todas formas". Compara la descarga con el archivo `.sha256`.

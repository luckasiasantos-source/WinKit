# Preparar a máquina virtual de teste (Hyper-V)

Este ambiente serve para **todos** os roteiros de validação (M2, M3, ...). Ele imita o pendrive
Ventoy com um disco virtual, então você não precisa formatar o pendrive de verdade nem
reinstalar o seu PC.

> Requisitos: Windows 10/11 **Pro** (o Hyper-V não existe no Home), virtualização ligada na BIOS,
> ~60 GB livres. Alternativa sem Hyper-V: VirtualBox — os passos equivalentes estão no fim.

## 1. Ligar o Hyper-V (uma vez)

PowerShell como administrador:

```powershell
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All
```

Reinicie o PC.

## 2. Criar o "pendrive" virtual (disco Ventoy)

PowerShell como administrador:

```powershell
New-VHD -Path C:\VMs\ventoy.vhdx -SizeBytes 40GB -Dynamic
Mount-VHD -Path C:\VMs\ventoy.vhdx
```

1. Abra o **Ventoy2Disk.exe** (baixe em https://www.ventoy.net).
2. Menu **Opção → Mostrar todos os dispositivos** (o disco virtual não é USB).
3. Menu **Opção → Estilo de partição → GPT**.
4. Menu **Opção → Suporte a Secure Boot**: **desmarcado** (mais simples para a VM).
5. Escolha o disco de ~40 GB (confira o tamanho! não escolha o seu disco real) e clique em **Instalar**.
6. A partição "Ventoy" do disco virtual recebe uma letra (ex.: `V:`). Copie a ISO do Windows 11 para ela.

## 3. Criar a VM

```powershell
New-VM -Name WinKitTeste -Generation 2 -MemoryStartupBytes 4GB -NewVHDPath C:\VMs\windows.vhdx -NewVHDSizeBytes 64GB
Set-VMFirmware -VMName WinKitTeste -EnableSecureBoot Off
Set-VMProcessor -VMName WinKitTeste -Count 2
```

## 4. A cada teste

1. Com o disco virtual montado (`Mount-VHD -Path C:\VMs\ventoy.vhdx`), rode os comandos do WinKit apontando para a letra dele (ex.: `--pendrive V:`).
2. Desmonte: `Dismount-VHD -Path C:\VMs\ventoy.vhdx`.
3. Ligue o "pendrive" na VM como primeiro disco de boot:

```powershell
Add-VMHardDiskDrive -VMName WinKitTeste -Path C:\VMs\ventoy.vhdx
$d = Get-VMHardDiskDrive -VMName WinKitTeste | Where-Object Path -like '*ventoy.vhdx'
Set-VMFirmware -VMName WinKitTeste -FirstBootDevice $d
```

4. Inicie a VM e conecte-se a ela (Gerenciador do Hyper-V → Conectar).
5. Para repetir do zero: desligue a VM, apague e recrie `windows.vhdx`:

```powershell
Remove-VMHardDiskDrive -VMName WinKitTeste -ControllerType SCSI -ControllerNumber 0 -ControllerLocation 0
Remove-Item C:\VMs\windows.vhdx
New-VHD -Path C:\VMs\windows.vhdx -SizeBytes 64GB -Dynamic
Add-VMHardDiskDrive -VMName WinKitTeste -Path C:\VMs\windows.vhdx
```

6. Ao terminar, para ler os logs: desligue a VM, `Mount-VHD -Path C:\VMs\ventoy.vhdx` e abra `V:\WinKit\Logs\`.

> Um disco virtual não pode estar montado no seu PC e ligado na VM ao mesmo tempo. Sempre desmonte antes de ligar a VM.

## Alternativa: VirtualBox

1. Crie o `ventoy.vhd` pelo Gerenciamento de Disco (Ação → Criar VHD), anexe, instale o Ventoy como acima.
2. Na VM do VirtualBox (EFI ligado), adicione o `ventoy.vhd` como disco SATA porta 0 e um disco novo de 64 GB como porta 1.

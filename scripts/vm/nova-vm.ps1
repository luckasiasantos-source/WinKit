# Cria uma VM Hyper-V para testar o WinKit (V3-04). Rode no PowerShell como administrador.
# Uso: .\nova-vm.ps1 -Iso D:\Win11-winkit.iso [-Nome WinKit-Teste] [-Geracao 2] [-MemoriaGB 4] [-DiscoGB 64]
# Geração 2 = UEFI com TPM e Secure Boot (Windows 11 e 10). Geração 1 = BIOS (Windows 7 e 8.1).
param(
    [Parameter(Mandatory = $true)][string]$Iso,
    [string]$Nome = "WinKit-Teste",
    [ValidateSet(1, 2)][int]$Geracao = 2,
    [int]$MemoriaGB = 4,
    [int]$DiscoGB = 64,
    [string]$Switch = "Default Switch",
    [string]$Pasta = "$env:PUBLIC\Documents\Hyper-V\WinKit"
)
$ErrorActionPreference = 'Stop'
if (-not (Get-Command New-VM -ErrorAction SilentlyContinue)) {
    throw "Hyper-V não está ligado. Recursos do Windows → Hyper-V, reinicie e tente de novo."
}
if (Get-VM -Name $Nome -ErrorAction SilentlyContinue) { throw "Já existe uma VM chamada $Nome." }
New-Item -ItemType Directory -Force $Pasta | Out-Null
$vhd = Join-Path $Pasta "$Nome.vhdx"
New-VM -Name $Nome -Generation $Geracao -MemoryStartupBytes ($MemoriaGB * 1GB) `
    -NewVHDPath $vhd -NewVHDSizeBytes ($DiscoGB * 1GB) -SwitchName $Switch | Out-Null
Set-VMProcessor -VMName $Nome -Count 2
Set-VM -VMName $Nome -CheckpointType Standard -AutomaticCheckpointsEnabled $false
if ($Geracao -eq 2) {
    $dvd = Add-VMDvdDrive -VMName $Nome -Path $Iso -Passthru
    Set-VMFirmware -VMName $Nome -FirstBootDevice $dvd -EnableSecureBoot On -SecureBootTemplate MicrosoftWindows
    Set-VMKeyProtector -VMName $Nome -NewLocalKeyProtector
    Enable-VMTPM -VMName $Nome
} else {
    Set-VMDvdDrive -VMName $Nome -Path $Iso
}
Checkpoint-VM -Name $Nome -SnapshotName "vazia"
Write-Host "VM $Nome criada (geração $Geracao), com o ponto 'vazia'. Para iniciar: Start-VM $Nome; vmconnect localhost $Nome"

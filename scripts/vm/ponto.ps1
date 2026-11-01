# Pontos de restauração (checkpoints) da VM de teste (V3-04). Rode como administrador.
# Uso: .\ponto.ps1 -Acao listar|criar|voltar [-Ponto nome] [-Nome WinKit-Teste]
param(
    [ValidateSet("listar", "criar", "voltar")][string]$Acao = "listar",
    [string]$Ponto = "",
    [string]$Nome = "WinKit-Teste"
)
$ErrorActionPreference = 'Stop'
switch ($Acao) {
    "listar" { Get-VMSnapshot -VMName $Nome | Select-Object Name, CreationTime | Format-Table -AutoSize }
    "criar" {
        if (-not $Ponto) { $Ponto = Get-Date -Format "yyyy-MM-dd_HH-mm" }
        Checkpoint-VM -Name $Nome -SnapshotName $Ponto
        Write-Host "Ponto '$Ponto' criado."
    }
    "voltar" {
        if (-not $Ponto) { throw "Diga o ponto: -Ponto vazia (veja -Acao listar)." }
        Stop-VM -Name $Nome -TurnOff -Force -ErrorAction SilentlyContinue
        Restore-VMSnapshot -VMName $Nome -Name $Ponto -Confirm:$false
        Write-Host "VM de volta ao ponto '$Ponto'."
    }
}

# Copia os logs e o estado do WinKit de dentro da VM para uma pasta do PC (V3-04).
# Usa o PowerShell Direct do Hyper-V: pede a senha da conta criada na VM. Rode como administrador.
# Uso: .\coletar-logs.ps1 [-Nome WinKit-Teste] [-Destino C:\WinKit-testes\logs]
param(
    [string]$Nome = "WinKit-Teste",
    [string]$Destino = "C:\WinKit-testes\logs"
)
$ErrorActionPreference = 'Stop'
$cred = Get-Credential -Message "Conta da VM (a criada pelo WinKit)"
$s = New-PSSession -VMName $Nome -Credential $cred
try {
    $alvo = Join-Path $Destino (Get-Date -Format "yyyy-MM-dd_HH-mm")
    New-Item -ItemType Directory -Force $alvo | Out-Null
    Copy-Item -FromSession $s -Path "C:\ProgramData\WinKit" -Destination $alvo -Recurse -ErrorAction SilentlyContinue
    $resumos = Invoke-Command -Session $s { Get-ChildItem "C:\Users\*\Desktop\*WinKit*.html" -ErrorAction SilentlyContinue | ForEach-Object FullName }
    foreach ($r in $resumos) { Copy-Item -FromSession $s -Path $r -Destination $alvo }
    Write-Host "Logs copiados para $alvo"
} finally {
    Remove-PSSession $s
}

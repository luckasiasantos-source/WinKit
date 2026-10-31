# Teste de fumaça com os executáveis já empacotados (CI e release).
# Uso (na raiz do repositório, depois do build.ps1): pwsh -File packaging\smoke.ps1
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$pkg = Get-ChildItem dist -Directory -Filter 'WinKit-*' | Select-Object -First 1
$cli = Join-Path $pkg.FullName 'winkit\winkit.exe'
$agent = Join-Path $pkg.FullName 'winkit-agent'
$tmp = if ($env:RUNNER_TEMP) { $env:RUNNER_TEMP } else { $env:TEMP }
$root = Join-Path $tmp 'pendrive'
New-Item -ItemType Directory -Force $root | Out-Null
& $cli --version
& $cli receita nova --raiz $root --usuario Samuel --nome-pc PC-CI
if ($LASTEXITCODE -ne 0) { throw "receita nova falhou" }
& $cli construir --raiz $root --agente $agent
if ($LASTEXITCODE -ne 0) { throw "construir falhou" }
& $cli validar --raiz $root
if ($LASTEXITCODE -ne 0) { throw "validar falhou" }
if (-not (Test-Path (Join-Path $root 'WinKit\Agent\winkit-agent\winkit-agent.exe'))) { throw "Agente não copiado" }
if (-not (Test-Path (Join-Path $root 'WinKit\Agent\bootstrap.ps1'))) { throw "bootstrap ausente" }
$p = Start-Process -FilePath (Join-Path $agent 'winkit-agent.exe') -ArgumentList 'summary' -Wait -PassThru
if ($p.ExitCode -ne 1) { throw "Agente não iniciou corretamente (código $($p.ExitCode))" }
$studio = Join-Path $pkg.FullName 'winkit-studio\winkit-studio.exe'
$env:QT_QPA_PLATFORM = 'offscreen'
$s = Start-Process -FilePath $studio -ArgumentList '--teste-fumaca' -Wait -PassThru
if ($s.ExitCode -ne 0) { throw "Studio não abriu (código $($s.ExitCode))" }
Write-Host "Fumaça OK"

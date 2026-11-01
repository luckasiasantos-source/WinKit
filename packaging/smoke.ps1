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
# v2 (M14–M17): os comandos novos com --raiz, sem tocar no runner
function Invoke-Cli([string[]]$CliArgs) {
    & $cli @CliArgs --raiz $root | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "winkit $($CliArgs -join ' ') falhou (código $LASTEXITCODE)" }
}
Invoke-Cli receita, modelo
Invoke-Cli receita, modelo, gamer, --aplicar
Invoke-Cli perfil-rapido, aplicar, privacy_max, --simular
Invoke-Cli perfil-rapido, aplicar, office
Invoke-Cli recursos, marcar, wsl
Invoke-Cli dns, definir, cloudflare
Invoke-Cli dns, mostrar
Invoke-Cli unidades, listar
Invoke-Cli manutencao, mostrar
Invoke-Cli variaveis, listar
Invoke-Cli fontes, listar
Invoke-Cli associacoes, listar
Invoke-Cli aparencia, listar
Invoke-Cli navegador, listar
Invoke-Cli pastas, mostrar
Invoke-Cli jogos, listar
Invoke-Cli contas, adicionar, Ana, --admin
Invoke-Cli sugestoes, listar, --json
$shared = Join-Path $tmp 'smoke.winkit.json'
Invoke-Cli receita, exportar, $shared
if ((Get-Content $shared -Raw) -match 'Samuel|PC-CI') { throw "exportação levou dados pessoais" }
Invoke-Cli receita, importar, $shared
Invoke-Cli plano
# v3 (M22): só mede o disco e mostra o tempo previsto, sem copiar nada
& $cli backup-pc fazer --destino $env:SystemDrive --pasta $env:TEMP --simular | Out-Null
if ($LASTEXITCODE -ne 0) { throw "backup-pc --simular falhou (código $LASTEXITCODE)" }
& $cli construir --raiz $root --agente $agent
if ($LASTEXITCODE -ne 0) { throw "construir falhou" }
& $cli validar --raiz $root
if ($LASTEXITCODE -ne 0) { throw "validar falhou" }
if (-not (Test-Path (Join-Path $root 'WinKit\Agent\winkit-agent\winkit-agent.exe'))) { throw "Agente não copiado" }
if (-not (Test-Path (Join-Path $root 'WinKit\Agent\bootstrap.ps1'))) { throw "bootstrap ausente" }
# M12: modo "aplicar neste PC" só em simulação (não muda nada no runner)
& $cli aplicar --raiz $root --simular
if ($LASTEXITCODE -ne 0) { throw "aplicar --simular falhou" }
$live = Start-Process -FilePath (Join-Path $agent 'winkit-agent.exe') -ArgumentList 'apply', '--root', $root, '--simular' -Wait -PassThru
if ($live.ExitCode -ne 0) { throw "Agente apply --simular falhou (código $($live.ExitCode))" }
$p = Start-Process -FilePath (Join-Path $agent 'winkit-agent.exe') -ArgumentList 'summary' -Wait -PassThru
if ($p.ExitCode -ne 1) { throw "Agente não iniciou corretamente (código $($p.ExitCode))" }
$studio = Join-Path $pkg.FullName 'winkit-studio\winkit-studio.exe'
$env:QT_QPA_PLATFORM = 'offscreen'
$s = Start-Process -FilePath $studio -ArgumentList '--teste-fumaca' -Wait -PassThru
if ($s.ExitCode -ne 0) { throw "Studio não abriu (código $($s.ExitCode))" }
Write-Host "Fumaça OK"

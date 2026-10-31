# Gera o pacote do WinKit no Windows: dist\WinKit-<versão>\{winkit, winkit-agent}
# Uso (na raiz do repositório): powershell -ExecutionPolicy Bypass -File packaging\build.ps1
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
uv sync --locked --group package
$env:QT_QPA_PLATFORM = 'offscreen'
uv run python packaging\make_icon.py
uv run pyinstaller packaging\winkit-agent.spec --noconfirm --distpath dist\build --workpath build\agent
uv run pyinstaller packaging\winkit.spec --noconfirm --distpath dist\build --workpath build\cli
uv run pyinstaller packaging\winkit-studio.spec --noconfirm --distpath dist\build --workpath build\studio
$version = (uv run python -c "import winkit; print(winkit.__version__)").Trim()
$out = "dist\WinKit-$version"
if (Test-Path $out) { Remove-Item $out -Recurse -Force }
New-Item -ItemType Directory -Path $out | Out-Null
Move-Item dist\build\winkit $out
Move-Item dist\build\winkit-agent $out
Move-Item dist\build\winkit-studio $out
Copy-Item packaging\LEIA-ME.txt $out
Write-Host "Pacote pronto: $out"

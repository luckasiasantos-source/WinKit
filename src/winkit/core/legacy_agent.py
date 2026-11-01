"""Agente legado para Windows 7 e 8.1 (V3-14, D-050): um script PowerShell 2.0 gerado da receita.

O Agente de verdade (Python 3.12) não roda no 7. No modo limitado, o primeiro logon roda este
script do pendrive: drivers, programas com instalador próprio, configurações dos apps (somando,
nunca trocando), Wi-Fi, plano de energia e recursos do Windows. Gera um resumo na área de
trabalho e um log em ``C:\\ProgramData\\WinKit\\legado.log``. Puro: só monta texto.
"""

from __future__ import annotations

from winkit.core.catalog.models import Catalogs
from winkit.core.paths import templates
from winkit.core.recipe.models import Recipe

#: Molde → expressão do PowerShell 2.0 (pastas do usuário que está logado).
PS_FOLDERS = {
    "APPDATA": "$env:APPDATA",
    "LOCALAPPDATA": "$env:LOCALAPPDATA",
    "USERPROFILE": "$env:USERPROFILE",
    "PROGRAMDATA": "$env:ProgramData",
    "PROGRAMFILES": "$env:ProgramFiles",
    "PROGRAMFILESX86": "${env:ProgramFiles(x86)}",
    "DOCUMENTS": "[Environment]::GetFolderPath('MyDocuments')",
    "DESKTOP": "[Environment]::GetFolderPath('Desktop')",
    "PICTURES": "[Environment]::GetFolderPath('MyPictures')",
    "MUSIC": "[Environment]::GetFolderPath('MyMusic')",
    "VIDEOS": "[Environment]::GetFolderPath('MyVideos')",
}
POWER = {"balanced": "SCHEME_BALANCED", "high_performance": "SCHEME_MIN"}

HEADER = r"""# WinKit: agente legado (Windows 7/8.1, PowerShell 2.0). Gerado pelo WinKit.
$ErrorActionPreference = 'Continue'
$base = Join-Path $env:ProgramData 'WinKit'
New-Item -ItemType Directory -Force -Path $base | Out-Null
$log = Join-Path $base 'legado.log'
$done = Join-Path $base 'legado.feito'
if (Test-Path $done) { exit 0 }
$root = (Get-Item $MyInvocation.MyCommand.Path).Directory.Parent.Parent.Parent.FullName
$wk = Join-Path $root 'WinKit'
$lines = New-Object System.Collections.ArrayList
function Log([string]$m) {
  $l = '{0} {1}' -f (Get-Date -Format s), $m
  Add-Content -Path $log -Value $l
  [void]$lines.Add($m)
}
Log ('início em ' + $env:COMPUTERNAME)
"""

FOOTER = r"""
$html = '<html><head><meta charset="utf-8"><title>WinKit</title></head><body><h1>WinKit</h1><ul>'
foreach ($m in $lines) { $html += '<li>' + [System.Security.SecurityElement]::Escape($m) + '</li>' }
$html += '</ul></body></html>'
$desk = [Environment]::GetFolderPath('Desktop')
Set-Content -Path (Join-Path $desk 'WinKit - resumo.html') -Value $html -Encoding UTF8
Set-Content -Path $done -Value (Get-Date -Format s)
Log 'fim'
"""


def ps_quote(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def ps_path(template: str) -> str | None:
    """Molde de caminho → expressão do PowerShell; ``None`` se usa uma pasta que o 7 não tem."""
    parsed = templates.parse(template)
    if parsed.absolute is not None:
        return ps_quote(parsed.absolute)
    base = PS_FOLDERS.get(parsed.var)
    if base is None:
        return None
    return f"(Join-Path ({base}) {ps_quote(parsed.rest)})" if parsed.rest else f"({base})"


def _payload(rel: str) -> str:
    return f"(Join-Path $wk {ps_quote(rel.replace('/', chr(92)))})"


DRIVERS = (
    "if (Test-Path (Join-Path $wk 'Drivers')) {\n"
    "  Get-ChildItem (Join-Path $wk 'Drivers') -Recurse -Filter *.inf | ForEach-Object {\n"
    "    & pnputil.exe -i -a $_.FullName | Out-Null\n"
    "    Log ('driver ' + $_.Name + ': ' + $LASTEXITCODE)\n"
    "  }\n}"
)


def _log_code(label: str) -> str:
    return f"Log ({ps_quote(label + ': ')} + $LASTEXITCODE)"


def _apps(recipe: Recipe) -> list[str]:
    out = []
    for app in recipe.selected_apps():
        spec = app.installer
        if spec is None or spec.path is None or app.source != "offline":
            continue  # sem winget no 7/8.1: só instalador próprio
        exe, args = _payload(spec.path), ps_quote(" ".join(spec.args) or " ")
        if spec.type == "msi":
            launch = f"msiexec.exe -ArgumentList ('/i \"' + {exe} + '\" ' + {args})"
        else:
            launch = f"{exe} -ArgumentList {args}"
        label = ps_quote("app " + app.name + ": ")
        out.append(f"$p = Start-Process {launch} -Wait -PassThru\nLog ({label} + $p.ExitCode)")
    return out


def _backups(recipe: Recipe) -> list[str]:
    out = []
    for b in recipe.selected_backups():
        dest = ps_path(b.template)
        if dest is None:
            out.append(f"Log {ps_quote('pulado (pasta sem equivalente no 7/8.1): ' + b.name)}")
            continue
        src = _payload(b.data_path)
        if b.kind == "folder":  # robocopy sem trocar o que existe (soma, D-007)
            out.append(
                f"& robocopy.exe {src} {dest} /E /XC /XN /XO /R:1 /W:1 /NP /NJH /NJS | Out-Null\n"
                + _log_code("configurações " + b.name)
            )
        else:
            out.append(
                f"$d = {dest}; $s = Get-ChildItem {src} | Select-Object -First 1\n"
                "if ($s -and -not (Test-Path $d)) {\n"
                "  New-Item -ItemType Directory -Force -Path (Split-Path $d) | Out-Null\n"
                "  Copy-Item $s.FullName $d\n}\n"
                f"Log {ps_quote('configuração ' + b.name)}"
            )
    return out


def _system(recipe: Recipe, catalogs: Catalogs) -> list[str]:
    out = []
    for net in recipe.wifi.networks:
        if net.selected:
            profile = _payload(net.file)
            out.append(
                f"& netsh.exe wlan add profile filename=({profile}) user=all | Out-Null\n"
                + _log_code("Wi-Fi " + net.ssid)
            )
    scheme = POWER.get(recipe.power.scheme)
    if scheme:
        out.append(f"& powercfg.exe /setactive {scheme}\n" + _log_code("energia"))
    for fid in recipe.windows.optional_features:
        entry = catalogs.feature(fid)
        for part in entry.parts if entry else []:
            if part.feature:
                out.append(
                    f"& dism.exe /online /enable-feature /featurename:{part.feature}"
                    " /norestart /quiet\n" + _log_code("recurso " + part.feature)
                )
    return out


def generate(recipe: Recipe, catalogs: Catalogs) -> str:
    return "\n".join(
        [HEADER, DRIVERS, *_apps(recipe), *_backups(recipe), *_system(recipe, catalogs), FOOTER]
    )

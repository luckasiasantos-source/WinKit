# WinKit — bootstrap (PLANO.md §10.1, D-012, D-013, D-023)
#
# Chamado pelo autounattend.xml na etapa "specialize", como SYSTEM:
#   powershell -nop -ep Bypass -File X:\WinKit\Agent\bootstrap.ps1 X: <pendrive_id> <perfil>
#
# Regras: nunca falhar a instalação do Windows (sempre sai com código 0); não depender de
# nada além do PowerShell 5.1; registrar tudo em C:\ProgramData\WinKit\Logs\bootstrap.log.

param(
    [Parameter(Position = 0)] [string] $Root,
    [Parameter(Position = 1)] [string] $PendriveId,
    [Parameter(Position = 2)] [string] $ProfileId
)

$ErrorActionPreference = 'Continue'
$base = Join-Path $env:ProgramData 'WinKit'
$logDir = Join-Path $base 'Logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir 'bootstrap.log'

function Write-Log([string] $message) {
    $line = "{0} {1}" -f (Get-Date -Format 'yyyy-MM-ddTHH:mm:ss.fffzzz'), $message
    Add-Content -LiteralPath $log -Value $line -Encoding UTF8
}

$proceed = $true
$pendriveRoot = $null
try {
    $pendriveRoot = $Root.TrimEnd('\') + '\'
    Write-Log "início: raiz=$pendriveRoot id=$PendriveId perfil=$ProfileId"

    $markerPath = Join-Path $pendriveRoot 'WinKit\winkit.marker'
    $marker = Get-Content -LiteralPath $markerPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($marker.pendrive_id -ne $PendriveId) {
        Write-Log "marcador de outro pendrive ($($marker.pendrive_id)); ignorando esta unidade"
        $proceed = $false
    }

    $stamp = Join-Path $base 'bootstrap.json'
    if ($proceed -and (Test-Path -LiteralPath $stamp)) {
        Write-Log 'bootstrap já executado antes; nada a fazer'
        $proceed = $false
    }

    if ($proceed) {
        # 1. Agente: cópia local (D-013)
        $agentSrc = Join-Path $pendriveRoot 'WinKit\Agent\winkit-agent'
        $agentDst = Join-Path $base 'Agent\winkit-agent'
        if (Test-Path -LiteralPath $agentSrc) {
            $robocopy = Join-Path $env:SystemRoot 'System32\robocopy.exe'
            & $robocopy $agentSrc $agentDst /E /R:2 /W:2 /NP /NJH /NJS /NFL /NDL | Out-Null
            Write-Log "agente copiado (robocopy código $LASTEXITCODE)"
        } else {
            Write-Log 'AVISO: agente ausente no pendrive; só o registro será feito'
        }

        # 2. Receita
        $recipeSrc = Join-Path $pendriveRoot "WinKit\Perfis\$ProfileId\receita.json"
        Copy-Item -LiteralPath $recipeSrc -Destination (Join-Path $base 'receita.json') -Force
        Write-Log 'receita copiada'

        # 3. SetupComplete.cmd → Fase 1 (preserva um SetupComplete.cmd existente)
        $exe = Join-Path $agentDst 'winkit-agent.exe'
        if (Test-Path -LiteralPath $exe) {
            $scripts = Join-Path $env:SystemRoot 'Setup\Scripts'
            New-Item -ItemType Directory -Force -Path $scripts | Out-Null
            $setupComplete = Join-Path $scripts 'SetupComplete.cmd'
            $line = "`"$exe`" phase1"
            if (Test-Path -LiteralPath $setupComplete) {
                Add-Content -LiteralPath $setupComplete -Value $line -Encoding ASCII
                Write-Log 'SetupComplete.cmd existente: linha da Fase 1 acrescentada'
            } else {
                Set-Content -LiteralPath $setupComplete -Value @('@echo off', $line) -Encoding ASCII
                Write-Log 'SetupComplete.cmd criado'
            }

            # 4. Tarefa da Fase 2 (o Agente também garante a tarefa; aqui é a primeira tentativa)
            try {
                $action = New-ScheduledTaskAction -Execute $exe -Argument 'phase2'
                $trigger = New-ScheduledTaskTrigger -AtLogOn
                # S-1-5-32-544 = Administradores (SID, para não depender do idioma — R-13)
                $principal = New-ScheduledTaskPrincipal -GroupId 'S-1-5-32-544' -RunLevel Highest
                $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries `
                    -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew `
                    -ExecutionTimeLimit (New-TimeSpan -Hours 12)
                Register-ScheduledTask -TaskPath '\WinKit\' -TaskName 'Fase2' -Action $action `
                    -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
                Write-Log 'tarefa \WinKit\Fase2 registrada'
            } catch {
                Write-Log "AVISO: tarefa não registrada agora (o Agente tenta de novo): $($_.Exception.Message)"
            }
        }

        $info = [ordered]@{
            pendrive_id = $PendriveId
            profile = $ProfileId
            timestamp = (Get-Date).ToString('o')
            agent_present = (Test-Path -LiteralPath $exe)
            agent_version = (Get-Content -LiteralPath (Join-Path $pendriveRoot 'WinKit\Agent\VERSION') -ErrorAction SilentlyContinue)
        }
        $info | ConvertTo-Json | Set-Content -LiteralPath $stamp -Encoding UTF8
        Write-Log 'bootstrap concluído'
    }
} catch {
    Write-Log ("ERRO: " + ($_ | Out-String))
} finally {
    if ($pendriveRoot) {
        try {
            $dest = Join-Path $pendriveRoot ("WinKit\Logs\{0}_{1}" -f $env:COMPUTERNAME, (Get-Date -Format 'yyyy-MM-dd_HH-mm'))
            New-Item -ItemType Directory -Force -Path $dest | Out-Null
            Copy-Item -LiteralPath $log -Destination $dest -Force
        } catch { }
    }
}
exit 0

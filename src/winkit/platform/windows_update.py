"""Windows Update pela API COM ``Microsoft.Update.Session`` (PLANO.md §20, M8; D-011).

Sem módulos de terceiros (PSWindowsUpdate). Uma passada: procura, baixa e instala.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from winkit.platform.powershell import PowerShell

#: OperationResultCode da API do Windows Update.
WU_SUCCEEDED = 2
WU_SUCCEEDED_WITH_ERRORS = 3

_INSTALL = r"""
$session = New-Object -ComObject Microsoft.Update.Session
$session.ClientApplicationID = 'WinKit'
$searcher = $session.CreateUpdateSearcher()
$criteria = if ($p.Drivers) { "IsInstalled=0 and IsHidden=0" } else { "IsInstalled=0 and IsHidden=0 and Type='Software'" }
$found = $searcher.Search($criteria)
if ($found.Updates.Count -eq 0) {
    [pscustomobject]@{ Found = 0; ResultCode = 2; Reboot = $false; Titles = @() }
    return
}
$list = New-Object -ComObject Microsoft.Update.UpdateColl
$titles = @()
foreach ($u in $found.Updates) {
    if (-not $u.EulaAccepted) { $u.AcceptEula() }
    [void]$list.Add($u)
    $titles += [string]$u.Title
}
$downloader = $session.CreateUpdateDownloader()
$downloader.Updates = $list
[void]$downloader.Download()
$installer = $session.CreateUpdateInstaller()
$installer.Updates = $list
$r = $installer.Install()
[pscustomobject]@{
    Found = $list.Count
    ResultCode = [int]$r.ResultCode
    Reboot = [bool]$r.RebootRequired
    Titles = $titles
}
"""


@dataclass(frozen=True)
class UpdateResult:
    found: int
    result_code: int
    reboot_required: bool
    titles: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return self.found == 0 or self.result_code in (WU_SUCCEEDED, WU_SUCCEEDED_WITH_ERRORS)


class WindowsUpdater(Protocol):
    def install_all(self, *, include_drivers: bool, log: Path | None) -> UpdateResult: ...


class ComWindowsUpdater:
    def __init__(self, ps: PowerShell) -> None:
        self._ps = ps

    def install_all(self, *, include_drivers: bool, log: Path | None) -> UpdateResult:
        out = self._ps.run_json(
            _INSTALL, {"Drivers": include_drivers}, timeout=4 * 3600, log_to=log
        )
        data = out[0] if out else {}
        return UpdateResult(
            found=int(data.get("Found") or 0),
            result_code=int(data.get("ResultCode") or 0),
            reboot_required=bool(data.get("Reboot")),
            titles=tuple(str(x) for x in data.get("Titles") or []),
        )

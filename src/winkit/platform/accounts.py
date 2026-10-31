"""Contas locais (rede de segurança da hipótese H11)."""

from __future__ import annotations

from typing import Protocol

from winkit.platform.powershell import PowerShell

_ENSURE_ADMIN = r"""
$user = Get-LocalUser -Name $p.User -ErrorAction SilentlyContinue
if (-not $user) { 'no_user'; return }
$members = @(Get-LocalGroupMember -SID 'S-1-5-32-544' -ErrorAction SilentlyContinue)
if ($members | Where-Object { $_.SID -eq $user.SID }) { 'already'; return }
Add-LocalGroupMember -SID 'S-1-5-32-544' -Member $user
'added'
"""


ADMINISTRATORS_SID = "S-1-5-32-544"
USERS_SID = "S-1-5-32-545"

_ENSURE_GROUP = r"""
$user = Get-LocalUser -Name $p.User -ErrorAction SilentlyContinue
if (-not $user) { 'no_user'; return }
$changed = $false
$admins = @(Get-LocalGroupMember -SID 'S-1-5-32-544' -ErrorAction SilentlyContinue)
$users = @(Get-LocalGroupMember -SID 'S-1-5-32-545' -ErrorAction SilentlyContinue)
$isAdmin = [bool]($admins | Where-Object { $_.SID -eq $user.SID })
$isUser = [bool]($users | Where-Object { $_.SID -eq $user.SID })
if (-not $isUser) { Add-LocalGroupMember -SID 'S-1-5-32-545' -Member $user; $changed = $true }
if ($p.Admin -and -not $isAdmin) { Add-LocalGroupMember -SID 'S-1-5-32-544' -Member $user; $changed = $true }
if (-not $p.Admin -and $isAdmin) { Remove-LocalGroupMember -SID 'S-1-5-32-544' -Member $user; $changed = $true }
if ($changed) { 'changed' } else { 'same' }
"""

_EXPIRE = r"""
$u = [ADSI]"WinNT://./$($p.User),user"
if (-not $u.Path) { 'no_user'; return }
$u.PasswordExpired = 1
$u.SetInfo()
'expired'
"""


class Accounts(Protocol):
    def ensure_administrator(self, username: str) -> str:
        """Devolve ``"already"``, ``"added"`` ou ``"no_user"``."""
        ...

    def ensure_group(self, username: str, *, admin: bool) -> str:
        """Pelos SIDs (H11): ``"same"``, ``"changed"`` ou ``"no_user"``. Tira de Admin se padrão."""
        ...

    def expire_password(self, username: str) -> bool:
        """O Windows pede senha nova no próximo login (``PasswordExpired``)."""
        ...


class WindowsAccounts:
    def __init__(self, ps: PowerShell) -> None:
        self._ps = ps

    def ensure_administrator(self, username: str) -> str:
        out = self._ps.run_json(_ENSURE_ADMIN, {"User": username}, timeout=120)
        return str(out[0]) if out else "no_user"

    def ensure_group(self, username: str, *, admin: bool) -> str:
        out = self._ps.run_json(_ENSURE_GROUP, {"User": username, "Admin": admin}, timeout=120)
        return str(out[0]) if out else "no_user"

    def expire_password(self, username: str) -> bool:
        return self._ps.run_json(_EXPIRE, {"User": username}, timeout=120) == ["expired"]

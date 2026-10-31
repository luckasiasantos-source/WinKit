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


class Accounts(Protocol):
    def ensure_administrator(self, username: str) -> str:
        """Devolve ``"already"``, ``"added"`` ou ``"no_user"``."""
        ...


class WindowsAccounts:
    def __init__(self, ps: PowerShell) -> None:
        self._ps = ps

    def ensure_administrator(self, username: str) -> str:
        out = self._ps.run_json(_ENSURE_ADMIN, {"User": username}, timeout=120)
        return str(out[0]) if out else "no_user"

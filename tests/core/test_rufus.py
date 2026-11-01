"""Opções do Rufus no pendrive (V3-07): leitura e comparação com a receita."""

from __future__ import annotations

from tests.factories import recipe
from winkit.core import rufus

RUFUS_XML = """<?xml version="1.0" encoding="utf-8"?>
<unattend xmlns="urn:schemas-microsoft-com:unattend">
  <settings pass="windowsPE"><component name="Microsoft-Windows-Setup"><RunSynchronous>
    <RunSynchronousCommand><Path>reg add HKLM\\SYSTEM\\Setup\\LabConfig
      /v BypassTPMCheck /t REG_DWORD /d 1 /f</Path></RunSynchronousCommand>
  </RunSynchronous></component></settings>
  <settings pass="oobeSystem"><component name="Microsoft-Windows-Shell-Setup">
    <OOBE><ProtectYourPC>3</ProtectYourPC></OOBE>
    <UserAccounts><LocalAccounts><LocalAccount><Name>samuel</Name></LocalAccount></LocalAccounts></UserAccounts>
  </component></settings>
</unattend>"""


def test_detect_and_compare() -> None:
    found = rufus.detect([RUFUS_XML])
    assert found == ["bypass_requirements", "local_account", "no_data_collection"]
    r = recipe()
    assert all(o.covered for o in rufus.compare(found, r))
    r.target_windows.version = "10"
    assert not rufus.compare(found, r)[0].covered  # no Windows 10 o WinKit não grava o LabConfig
    assert rufus.detect(["<unattend/>"]) == []

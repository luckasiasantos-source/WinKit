"""Relatório antes/depois (V2-19): o que o PC antigo tinha e o Windows novo não tem. Puro."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field

from winkit.core.inventory_snapshot import Snapshot

_VERSIONISH = re.compile(
    r"\b(v?\d+(\.\d+)+|\(x64\)|\(x86\)|x64|x86|64-bit|32-bit)\b", re.IGNORECASE
)
_NON_WORD = re.compile(r"[^a-z0-9]+")
#: Abaixo disto, o hardware é considerado outro PC e os drivers não são comparados.
SAME_HARDWARE_RATIO = 0.5


class Comparison(BaseModel):
    model_config = ConfigDict(extra="forbid")
    missing_apps: list[str] = Field(default_factory=list)
    driverless: list[str] = Field(default_factory=list)
    missing_features: list[str] = Field(default_factory=list)
    same_hardware: bool = True

    @property
    def empty(self) -> bool:
        return not (self.missing_apps or self.driverless or self.missing_features)


def normalize_name(name: str) -> str:
    """``"7-Zip 24.08 (x64)"`` → ``"7zip"`` (sem versão, arquitetura nem pontuação)."""
    return _NON_WORD.sub("", _VERSIONISH.sub(" ", name.casefold()))


def _hardware(snapshot: Snapshot) -> set[str]:
    return {h.casefold() for d in snapshot.devices for h in d.hardware_ids[:1]}


def compare(before: Snapshot, after: Snapshot, feature_names: dict[str, str]) -> Comparison:
    after_ids = {a.winget_id.casefold() for a in after.apps if a.winget_id}
    after_names = {normalize_name(a.name) for a in after.apps}
    missing_apps = sorted(
        {
            a.name
            for a in before.apps
            if not (a.winget_id and a.winget_id.casefold() in after_ids)
            and normalize_name(a.name) not in after_names
        },
        key=str.casefold,
    )
    old_hw, new_hw = _hardware(before), _hardware(after)
    same = bool(old_hw) and len(old_hw & new_hw) / len(old_hw) >= SAME_HARDWARE_RATIO
    driverless: list[str] = []
    if same:
        ok_before = {
            d.hardware_ids[0].casefold() for d in before.devices if d.code == 0 and d.hardware_ids
        }
        driverless = sorted(
            {
                d.name
                for d in after.devices
                if d.code not in (0, 22, 45)
                and d.hardware_ids
                and d.hardware_ids[0].casefold() in ok_before
            },
            key=str.casefold,
        )
    missing_features = sorted(
        feature_names.get(f, f) for f in set(before.features) - set(after.features)
    )
    return Comparison(
        missing_apps=missing_apps,
        driverless=driverless,
        missing_features=missing_features,
        same_hardware=same,
    )

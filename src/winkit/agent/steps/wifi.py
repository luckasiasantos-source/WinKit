"""Etapa: adicionar uma rede Wi-Fi antes do login (V2-02, R17, D-036)."""

from __future__ import annotations

from winkit.agent.steps.base import StepBase, StepContext, StepResult
from winkit.core.recipe.models import WifiNetwork
from winkit.core.secrets import SECRETS
from winkit.core.wifi import key_material, parse_profile
from winkit.i18n import msg


def _item(ctx: StepContext) -> WifiNetwork | None:
    return next((n for n in ctx.recipe.wifi.networks if n.id == ctx.step.ref), None)


class WifiStep(StepBase):
    live_safe = True

    def check(self, ctx: StepContext) -> bool:
        item = _item(ctx)
        if item is None or ctx.pendrive is None:
            return False
        try:
            name = parse_profile(ctx.payload(item.file).read_bytes()).name
        except (OSError, ValueError):
            return False
        return ctx.services.wifi.profile_exists(name)

    def run(self, ctx: StepContext) -> StepResult:
        item = _item(ctx)
        if item is None:
            return StepResult.skipped(msg("step.not_in_recipe"))
        wifi = ctx.services.wifi
        if not wifi.has_wlan():
            return StepResult.skipped(msg("step.wifi.no_adapter"))
        source = ctx.payload(item.file)
        try:
            data = source.read_bytes()
            parse_profile(data)
        except (OSError, ValueError) as exc:
            return StepResult.failed(msg("step.failed_generic", detail=str(exc)), recoverable=False)
        SECRETS.add(key_material(data))  # R-53: a senha nunca aparece em log
        tmp_dir = ctx.paths.base / "tmp" / "wifi"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        tmp = tmp_dir / f"{item.id}.xml"
        SECRETS.add(str(tmp))
        try:
            tmp.write_bytes(data)
            code = wifi.add_profile(tmp)
        finally:
            tmp.unlink(missing_ok=True)  # a cópia com senha não fica no disco
        if code != 0:
            return StepResult.failed(msg("step.wifi.code", code=code))
        return StepResult.ok(msg("step.wifi.added", ssid=item.ssid))

"""Etapas: servidores DNS / DoH e bloqueio pelo ``hosts`` (V2-16, R18).

Seguras no modo ao vivo. O DNS vale para os adaptadores físicos que existem agora; a política
de DoH é global, para cobrir os que aparecerem depois (DT-021).
"""

from __future__ import annotations

from pathlib import Path

from winkit.agent.steps.base import StepBase, StepContext, StepResult, local_path
from winkit.core import dns as rules
from winkit.core.errors import WinKitError
from winkit.i18n import Msg, msg
from winkit.platform.dns import DOH_ALLOW, DOH_POLICY_KEY, DOH_POLICY_VALUE, DOH_REQUIRE
from winkit.platform.hosts import hosts_file, read_hosts, write_block


def _policy(ctx: StepContext) -> int:
    return DOH_REQUIRE if ctx.recipe.dns.require_doh else DOH_ALLOW


class DnsStep(StepBase):
    live_safe = True

    def check(self, ctx: StepContext) -> bool:
        target = rules.resolve(ctx.recipe.dns, ctx.catalogs)
        if target is None:
            return True
        adapters = ctx.services.dns.adapters()
        if not adapters or any((a.ipv4, a.ipv6) != (target.ipv4, target.ipv6) for a in adapters):
            return False
        if target.doh_template is None:
            return True
        doh = ctx.services.dns.doh()
        if not doh.available:
            return True
        reg = ctx.services.registry.get("HKLM", DOH_POLICY_KEY, DOH_POLICY_VALUE)
        return reg == _policy(ctx) and all(
            doh.servers.get(s) == target.doh_template for s in target.servers
        )

    def preview_changes(self, ctx: StepContext) -> tuple[Msg, ...]:
        target = rules.resolve(ctx.recipe.dns, ctx.catalogs)
        if target is None:
            return ()
        return (msg("preview.dns", servers=", ".join(target.ipv4)),)

    def run(self, ctx: StepContext) -> StepResult:
        target = rules.resolve(ctx.recipe.dns, ctx.catalogs)
        if target is None:
            return StepResult.skipped(msg("step.not_in_recipe"))
        client = ctx.services.dns
        try:
            adapters = client.adapters()
            if not adapters:
                return StepResult.skipped(msg("step.dns.no_adapter"))
            for a in adapters:
                client.set_servers(a.index, list(target.servers))
            encrypted = False
            if target.doh_template:
                doh = client.doh()
                if doh.available:
                    for server in target.servers:
                        client.set_doh(
                            server, target.doh_template, require=ctx.recipe.dns.require_doh
                        )
                    ctx.services.registry.set(
                        "HKLM", DOH_POLICY_KEY, DOH_POLICY_VALUE, "dword", _policy(ctx)
                    )
                    encrypted = True
                else:
                    ctx.log.info("Windows sem DoH: só os servidores", step=ctx.step.id)
        except (WinKitError, RuntimeError) as exc:
            return StepResult.failed(msg("step.failed_generic", detail=str(exc)))
        key = "step.dns.done_encrypted" if encrypted else "step.dns.done"
        return StepResult.ok(msg(key, n=len(adapters)))


class HostsStep(StepBase):
    live_safe = True

    def _domains(self, ctx: StepContext) -> list[str]:
        return rules.blocked_domains(ctx.recipe.dns, ctx.catalogs)

    def _path(self, ctx: StepContext) -> Path:
        return local_path(str(hosts_file(ctx.services.folders.windows_dir())))

    def check(self, ctx: StepContext) -> bool:
        domains = self._domains(ctx)
        return not domains or rules.has_block(read_hosts(self._path(ctx)), domains)

    def preview_changes(self, ctx: StepContext) -> tuple[Msg, ...]:
        return (msg("preview.hosts", n=len(self._domains(ctx))),)

    def run(self, ctx: StepContext) -> StepResult:
        domains = self._domains(ctx)
        if not domains:
            return StepResult.skipped(msg("step.not_in_recipe"))
        try:
            write_block(self._path(ctx), domains)
        except OSError as exc:
            return StepResult.failed(msg("step.failed_generic", detail=str(exc)))
        return StepResult.ok(msg("step.hosts.done", n=len(domains)))

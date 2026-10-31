"""Planejador de fases (PLANO.md §11.2, regras R1–R15).

Função pura e determinística: a mesma receita e o mesmo contexto produzem exatamente o
mesmo plano. Não executa nada.
"""

from __future__ import annotations

import heapq
from collections.abc import Callable
from dataclasses import dataclass, field

from winkit.core import dns as dns_rules
from winkit.core.catalog.models import Catalogs
from winkit.core.errors import PathTemplateError, PlanError
from winkit.core.paths import templates
from winkit.core.planner.models import (
    ExcludedItem,
    Phase,
    Plan,
    PlanContext,
    PlannedStep,
    StepKind,
    Target,
)
from winkit.core.recipe.models import AppItem, BackupItem, Recipe
from winkit.core.recipe.validation import find_cycle
from winkit.i18n import t, tn

# Ordem dos grupos dentro de cada fase (PLANO.md §11.2, tabela "Ordem dentro de cada fase").
_G1 = {
    "account": 2,  # R24: no começo da Fase 1
    "driver": 10,
    "user_folders": 12,  # R16: antes de backups e ajustes do usuário
    "wifi": 15,  # R17: logo depois dos drivers (precisa do driver de rede)
    "dns": 16,  # R18: depois do Wi-Fi
    "hosts": 17,
    "power": 20,
    "bloat": 30,
    "feature": 35,
    "tweak": 40,
    "network_drive": 45,
    "maintenance": 47,
    "env": 48,
    "font": 49,
    "personal": 42,  # R23: perfil Default, junto dos ajustes de aparência
    "browser": 44,  # R21: políticas antes dos apps; valem quando o navegador for instalado
    "start_layout": 46,  # R20: perfil Default, antes do primeiro login
    "backup": 50,
    "default_apps": 65,  # depois dos apps offline, para que os ProgIds já existam
    "app": 60,
}
_G2 = {
    "backup": 20,
    "app": 30,
    "feature": 35,
    "tweak": 40,
    "shortcut": 50,
    "game_library": 52,  # R22: depois do app do launcher
    "maintenance": 55,  # R27: a tarefa do winget é do usuário
    "rename_computer": 60,
    "windows_update": 70,
    "driver_report": 75,  # R28: depois do Windows Update, que já resolve muitos drivers
    "default_apps_verify": 77,
    "compare": 78,  # R29: no fim, depois de instalar e procurar drivers
    "restore_point": 80,
    "finalize": 99,
}
#: Modo ao vivo: o ponto de restauração "antes" vem antes de tudo (R30).
_LIVE_FIRST = 1
#: Tipos que nunca saem do plano pelo filtro "o que aplicar".
_ALWAYS = ("finalize", "restore_point")
_FALLBACK_GROUP = 5

#: Ajustes ligados por campos da receita, não pela lista ``tweaks``.
TWEAK_WU_DRIVERS = "system.wu_no_driver_replacement"
TWEAK_CONSUMER_CONTENT = "system.consumer_content"
TWEAK_STORAGE_SENSE = "maintenance.storage_sense"

#: Decide se um item marcado como "decidir na hora" vai para a janela (R1, R2).
Ask = Callable[[bool], bool]


@dataclass
class _Draft:
    kind: StepKind
    ref: str
    phase: Phase
    title: str
    target: Target
    needs_pendrive: bool = False
    needs_network: bool = False
    depends_on: list[str] = field(default_factory=list)
    user_choice: bool = False
    phase2_fallback: bool = False
    sort: tuple[int, int, str] = (0, 0, "")

    @property
    def id(self) -> str:
        return f"{self.kind}:{self.ref}"


def plan(recipe: Recipe, catalogs: Catalogs, ctx: PlanContext | None = None) -> Plan:
    ctx = ctx or PlanContext()
    mode = recipe.execution.mode
    interactive = mode != "silent"  # R1

    def ask(flag: bool) -> bool:  # R2
        return interactive and flag

    drafts: list[_Draft] = []
    excluded: list[ExcludedItem] = []

    _plan_accounts(recipe, drafts)
    _plan_drivers(recipe, drafts)
    _plan_user_folders(recipe, drafts)
    _plan_wifi(recipe, drafts)
    _plan_network_privacy(recipe, catalogs, drafts)
    _plan_network_drives(recipe, drafts)
    _plan_maintenance(recipe, drafts)
    _plan_env(recipe, drafts)
    _plan_fonts(recipe, drafts)
    _plan_default_apps(recipe, ctx, drafts)
    _plan_personal(recipe, catalogs, drafts)
    _plan_browsers(recipe, catalogs, drafts)
    _plan_start_layout(recipe, drafts)
    _plan_games(recipe, drafts)
    _plan_power(recipe, drafts)
    _plan_bloat(recipe, catalogs, ctx, drafts, excluded)
    _plan_features(recipe, catalogs, ctx, drafts, excluded)
    _plan_tweaks(recipe, catalogs, ctx, ask, out=drafts, excluded=excluded)
    post_install = {b for a in recipe.selected_apps() for b in a.restore_backups_after_install}
    _plan_backups(recipe, ask, post_install, drafts)
    _plan_apps(recipe, ask, post_install, drafts)
    _plan_tail(recipe, ask, drafts, ctx)
    _plan_live_and_restore(recipe, ctx, drafts)
    if ctx.only_kinds is not None:
        kept = [d for d in drafts if d.kind in ctx.only_kinds or d.kind in _ALWAYS]
        for d in drafts:
            if d not in kept:
                excluded.append(
                    ExcludedItem(kind=d.kind, ref=d.ref, reason=t("plan.excluded_not_selected"))
                )
        drafts = kept

    steps = _finalize(drafts, ctx)
    return Plan(mode=mode, steps=tuple(steps), excluded=tuple(excluded))


# ------------------------------------------------------------------ etapas por tipo
def _plan_drivers(recipe: Recipe, out: list[_Draft]) -> None:  # R3
    for d in recipe.selected_drivers():
        name = f"{d.class_name} {d.provider}".strip()
        out.append(
            _Draft(
                "driver",
                d.id,
                1,
                t("plan.driver", name=name),
                "machine",
                needs_pendrive=True,
                sort=(_G1["driver"], d.priority, d.id),
            )
        )


def _plan_accounts(recipe: Recipe, out: list[_Draft]) -> None:  # R24
    for a in recipe.windows.extra_accounts:
        ref = a.username.casefold()
        out.append(
            _Draft(
                "account",
                ref,
                1,
                t("plan.account", name=a.username),
                "machine",
                sort=(_G1["account"], 0, ref),
            )
        )


def _plan_user_folders(recipe: Recipe, out: list[_Draft]) -> None:  # R16
    uf = recipe.user_folders
    if uf.enabled and uf.volume is not None and uf.folders:
        out.append(
            _Draft(
                "user_folders",
                "default",
                1,
                t("plan.user_folders"),
                "default_profile",
                sort=(_G1["user_folders"], 0, "default"),
            )
        )


def _plan_wifi(recipe: Recipe, out: list[_Draft]) -> None:  # R17
    for n in recipe.wifi.networks:
        if not n.selected or n.security == "enterprise":
            continue
        out.append(
            _Draft(
                "wifi",
                n.id,
                1,
                t("plan.wifi", name=n.ssid),
                "machine",
                needs_pendrive=True,
                sort=(_G1["wifi"], 0, n.id),
            )
        )


def _plan_network_privacy(recipe: Recipe, catalogs: Catalogs, out: list[_Draft]) -> None:  # R18
    if dns_rules.resolve(recipe.dns, catalogs) is not None:
        out.append(
            _Draft("dns", "servers", 1, t("plan.dns"), "machine", sort=(_G1["dns"], 0, "servers"))
        )
    domains = dns_rules.blocked_domains(recipe.dns, catalogs)
    if domains:
        title = tn("plan.hosts", len(domains))
        out.append(_Draft("hosts", "block", 1, title, "machine", sort=(_G1["hosts"], 0, "block")))


def _plan_network_drives(recipe: Recipe, out: list[_Draft]) -> None:  # R25
    for d in recipe.network_drives:
        if not d.selected:
            continue
        title = t("plan.network_drive", letter=d.letter, path=d.remote_path)
        out.append(
            _Draft(
                "network_drive",
                d.letter,
                1,
                title,
                "default_profile",
                sort=(_G1["network_drive"], 0, d.letter),
            )
        )


def _plan_maintenance(recipe: Recipe, out: list[_Draft]) -> None:  # R27
    m = recipe.maintenance
    if m.ensure_defrag_schedule:
        out.append(
            _Draft(
                "maintenance",
                "defrag",
                1,
                t("plan.maintenance_defrag"),
                "machine",
                sort=(_G1["maintenance"], 0, "defrag"),
            )
        )
    if m.winget_upgrade != "off":
        out.append(
            _Draft(
                "maintenance",
                "winget",
                2,
                t("plan.maintenance_winget"),
                "user_profile",
                sort=(_G2["maintenance"], 0, "winget"),
            )
        )


def _plan_env(recipe: Recipe, out: list[_Draft]) -> None:  # R26
    env = recipe.environment

    def target(scope: str) -> Target:
        return "machine" if scope == "machine" else "default_profile"

    for v in env.variables:
        if v.selected:
            ref = f"var.{v.scope}.{v.name}"
            title = t("plan.env_var", name=v.name)
            out.append(_Draft("env", ref, 1, title, target(v.scope), sort=(_G1["env"], 0, ref)))
    for scope in ("machine", "user"):
        n = sum(1 for p in env.path_entries if p.selected and p.scope == scope)
        if n:
            ref = f"path.{scope}"
            title = tn(f"plan.env_path_{scope}", n)
            out.append(_Draft("env", ref, 1, title, target(scope), sort=(_G1["env"], 1, ref)))


def _plan_fonts(recipe: Recipe, out: list[_Draft]) -> None:
    for f in recipe.fonts:
        if f.selected and f.file:
            title = t("plan.font", name=f.full_name)
            out.append(
                _Draft(
                    "font",
                    f.id,
                    1,
                    title,
                    "machine",
                    needs_pendrive=True,
                    sort=(_G1["font"], 0, f.id),
                )
            )


def _plan_default_apps(recipe: Recipe, ctx: PlanContext, out: list[_Draft]) -> None:  # R20
    d = recipe.default_apps
    if not (d.enabled and d.groups and d.associations_file):
        return
    out.append(
        _Draft(
            "default_apps",
            "import",
            1,
            t("plan.default_apps"),
            "machine",
            needs_pendrive=True,
            sort=(_G1["default_apps"], 0, "import"),
        )
    )
    if ctx.mode == "install":
        out.append(
            _Draft(
                "default_apps_verify",
                "user",
                2,
                t("plan.default_apps_verify"),
                "user_profile",
                needs_pendrive=True,
                depends_on=["default_apps:import"],
                sort=(_G2["default_apps_verify"], 0, "user"),
            )
        )


def _plan_personal(recipe: Recipe, catalogs: Catalogs, out: list[_Draft]) -> None:  # R23
    p = recipe.personal
    for group_id in p.groups:
        group = catalogs.personal_group(group_id)
        if group is None:
            continue
        has_values = any(f"{s.key}\\{s.value}" in p.values for s in group.values)
        if not has_values and not (group.file and p.wallpaper_file):
            continue
        out.append(
            _Draft(
                "personal",
                group_id,
                1,
                t("plan.personal", name=group.name),
                "default_profile",
                needs_pendrive=group.file,
                sort=(_G1["personal"], 0, group_id),
            )
        )


def _plan_browsers(recipe: Recipe, catalogs: Catalogs, out: list[_Draft]) -> None:  # R21
    for cfg in recipe.browsers:
        entry = catalogs.browser(cfg.id)
        if not cfg.selected or entry is None:
            continue
        out.append(
            _Draft(
                "browser",
                cfg.id,
                1,
                t("plan.browser", name=entry.name),
                "machine",
                sort=(_G1["browser"], 0, cfg.id),
            )
        )


def _plan_start_layout(recipe: Recipe, out: list[_Draft]) -> None:  # R20
    s = recipe.start_layout
    wants = any(p.selected for p in s.taskbar_pins) or any(p.selected for p in s.start_pins)
    if s.mode == "off" or not (wants or (s.mode == "exact" and s.start_file)):
        return
    out.append(
        _Draft(
            "start_layout",
            "default",
            1,
            t("plan.start_layout"),
            "default_profile",
            needs_pendrive=s.mode == "exact",
            sort=(_G1["start_layout"], 0, "default"),
        )
    )


#: Launcher → ids do winget, para a etapa esperar o app (R22).
LAUNCHER_WINGET = {"steam": ("Valve.Steam",), "epic": ("EpicGames.EpicGamesLauncher",)}


def _plan_games(recipe: Recipe, out: list[_Draft]) -> None:  # R22
    for lib in recipe.game_libraries:
        if not lib.selected:
            continue
        apps = [
            f"app:{a.id}"
            for a in recipe.selected_apps()
            if a.winget_id in LAUNCHER_WINGET[lib.launcher]
        ]
        out.append(
            _Draft(
                "game_library",
                lib.id,
                2,
                t("plan.game_library", name=lib.name),
                "machine",
                needs_pendrive=lib.launcher == "epic",
                depends_on=apps,
                sort=(_G2["game_library"], 0, lib.id),
            )
        )


def _plan_power(recipe: Recipe, out: list[_Draft]) -> None:  # R5
    p = recipe.power
    if p.scheme != "unchanged" or p.hibernate is not None or p.fast_startup is not None:
        out.append(
            _Draft(
                "power",
                "settings",
                1,
                t("plan.power"),
                "machine",
                sort=(_G1["power"], 0, "settings"),
            )
        )


def _plan_bloat(
    recipe: Recipe,
    catalogs: Catalogs,
    ctx: PlanContext,
    out: list[_Draft],
    excluded: list[ExcludedItem],
) -> None:  # R4
    for pkg in sorted(set(recipe.bloatware.remove)):
        entry = catalogs.bloat(pkg)
        if entry is None or entry.risk == "blocked":
            reason = t("plan.excluded_unknown_bloat")
            excluded.append(ExcludedItem(kind="bloat", ref=pkg, reason=reason))
            continue
        if not entry.windows.applies(ctx.os_major, ctx.build):
            excluded.append(ExcludedItem(kind="bloat", ref=pkg, reason=t("plan.excluded_os")))
            continue
        out.append(
            _Draft(
                "bloat",
                pkg,
                1,
                t("plan.bloat", name=entry.name),
                "machine",
                sort=(_G1["bloat"], 0, pkg),
            )
        )


def _plan_features(
    recipe: Recipe,
    catalogs: Catalogs,
    ctx: PlanContext,
    out: list[_Draft],
    excluded: list[ExcludedItem],
) -> None:  # R19
    for feature_id in dict.fromkeys(recipe.windows.optional_features):
        entry = catalogs.feature(feature_id)
        if entry is None:
            reason = t("plan.excluded_unknown_feature")
            excluded.append(ExcludedItem(kind="feature", ref=feature_id, reason=reason))
            continue
        if not entry.windows.applies(ctx.os_major, ctx.build):
            excluded.append(
                ExcludedItem(kind="feature", ref=feature_id, reason=t("plan.excluded_os"))
            )
            continue
        if not entry.windows.allows_edition(recipe.windows.edition):
            reason = t("plan.excluded_edition")
            excluded.append(ExcludedItem(kind="feature", ref=feature_id, reason=reason))
            continue
        offline = entry.offline_source is not None
        title = t("plan.feature", name=entry.name)
        if not entry.needs_network or offline:
            # sem internet ou com fonte offline: antes do login; sem a fonte, tenta na Fase 2
            out.append(
                _Draft(
                    "feature",
                    feature_id,
                    1,
                    title,
                    "machine",
                    needs_pendrive=offline,
                    phase2_fallback=offline and entry.needs_network,
                    sort=(_G1["feature"], 0, feature_id),
                )
            )
        else:
            out.append(
                _Draft(
                    "feature",
                    feature_id,
                    2,
                    title,
                    "machine",
                    needs_network=True,
                    sort=(_G2["feature"], 0, feature_id),
                )
            )


def _plan_tweaks(
    recipe: Recipe,
    catalogs: Catalogs,
    ctx: PlanContext,
    ask: Ask,
    *,
    out: list[_Draft],
    excluded: list[ExcludedItem],
) -> None:  # R5, R6
    selections = [(s.id, s.decide_at_runtime) for s in recipe.enabled_tweaks()]
    implicit = []
    if recipe.updates.block_wu_driver_replacement:
        implicit.append(TWEAK_WU_DRIVERS)
    if recipe.bloatware.disable_consumer_content:
        implicit.append(TWEAK_CONSUMER_CONTENT)
    if recipe.maintenance.storage_sense:
        implicit.append(TWEAK_STORAGE_SENSE)
    chosen = {tid for tid, _ in selections}
    selections += [(tid, False) for tid in implicit if tid not in chosen]

    for tweak_id, decide in selections:
        tweak = catalogs.tweak(tweak_id)
        if tweak is None:
            reason = t("plan.excluded_unknown_tweak")
            excluded.append(ExcludedItem(kind="tweak", ref=tweak_id, reason=reason))
            continue
        if tweak.stage == "specialize":
            reason = t("plan.excluded_specialize")
            excluded.append(ExcludedItem(kind="tweak", ref=tweak_id, reason=reason))
            continue
        if not tweak.windows.applies(ctx.os_major, ctx.build):
            excluded.append(ExcludedItem(kind="tweak", ref=tweak_id, reason=t("plan.excluded_os")))
            continue
        title = t("plan.tweak", name=tweak.title)
        if ask(decide):
            target: Target = "user_profile" if tweak.scope == "user" else "machine"
            out.append(
                _Draft(
                    "tweak",
                    tweak_id,
                    2,
                    title,
                    target,
                    user_choice=True,
                    sort=(_G2["tweak"], 0, tweak_id),
                )
            )
        else:
            target = "default_profile" if tweak.scope == "user" else "machine"
            out.append(
                _Draft("tweak", tweak_id, 1, title, target, sort=(_G1["tweak"], 0, tweak_id))
            )


def _backup_phase(b: BackupItem, ask: Ask) -> tuple[Phase, Target, bool]:
    try:
        parsed = templates.parse(b.template)
    except PathTemplateError as exc:
        raise PlanError(f"backup {b.id}: {exc}") from exc
    if parsed.is_absolute:  # R8
        return 2, "machine", ask(b.decide_at_runtime)
    if ask(b.decide_at_runtime):  # R2
        return 2, ("user_profile" if parsed.is_profile else "machine"), True
    if parsed.is_profile and b.for_accounts == "main":  # V2-11: só a conta principal
        return 2, "user_profile", False
    if parsed.is_profile:  # R7
        return 1, "default_profile", False
    return 1, "machine", False  # R8


def _plan_backups(recipe: Recipe, ask: Ask, post_install: set[str], out: list[_Draft]) -> None:
    for b in recipe.selected_backups():
        if b.id in post_install:
            continue  # R13: planejado junto com o app
        phase, target, choice = _backup_phase(b, ask)
        group = (_G1 if phase == 1 else _G2)["backup"]
        out.append(
            _Draft(
                "backup",
                b.id,
                phase,
                t("plan.backup", name=b.name),
                target,
                needs_pendrive=True,
                user_choice=choice,
                sort=(group, 0, b.id),
            )
        )


def _app_phase(a: AppItem, ask: Ask) -> Phase:
    if ask(a.decide_at_runtime):  # R2
        return 2
    if a.source == "winget_online":  # R10
        return 2
    if a.scope == "user":  # R11
        return 2
    return 1  # R9


def _plan_apps(recipe: Recipe, ask: Ask, post_install: set[str], out: list[_Draft]) -> None:
    apps = {a.id: a for a in recipe.selected_apps()}
    portable = {i: a for i, a in apps.items() if a.source == "portable"}
    installable = {i: a for i, a in apps.items() if a.source != "portable"}

    phases: dict[str, Phase] = {i: _app_phase(a, ask) for i, a in installable.items()}
    deps = {i: [d for d in a.depends_on if d in installable] for i, a in installable.items()}
    cycle = find_cycle(deps)
    if cycle:
        raise PlanError(t("recipe.dependency_cycle", ids=" → ".join(cycle)))
    changed = True
    while changed:  # dependência na Fase 2 puxa o dependente para a Fase 2
        changed = False
        for i, ds in deps.items():
            if phases[i] == 1 and any(phases[d] == 2 for d in ds):
                phases[i] = 2
                changed = True

    for phase in (1, 2):
        ids = [i for i in installable if phases[i] == phase]
        group = (_G1 if phase == 1 else _G2)["app"]
        for seq, app_id in enumerate(_topo_order(ids, deps, installable)):
            a = installable[app_id]
            out.append(
                _Draft(
                    "app",
                    app_id,
                    phase,
                    t("plan.app", name=a.name),
                    "user_profile" if a.scope == "user" else "machine",
                    needs_pendrive=a.source == "offline",
                    needs_network=a.source == "winget_online",
                    depends_on=[f"app:{d}" for d in deps[app_id]],
                    user_choice=ask(a.decide_at_runtime),
                    sort=(group, seq * 100, app_id),
                )
            )
            for k, backup_id in enumerate(a.restore_backups_after_install):  # R13
                b = recipe.backup(backup_id)
                if b is None or not b.selected or backup_id not in post_install:
                    continue
                parsed = templates.parse(b.template)
                if parsed.is_profile:
                    target: Target = "default_profile" if phase == 1 else "user_profile"
                else:
                    target = "machine"
                out.append(
                    _Draft(
                        "backup",
                        backup_id,
                        phase,
                        t("plan.backup", name=b.name),
                        target,
                        needs_pendrive=True,
                        depends_on=[f"app:{app_id}"],
                        sort=(group, seq * 100 + 1 + k, backup_id),
                    )
                )
                post_install.discard(backup_id)  # um backup só é planejado uma vez

    for app_id in sorted(portable):  # R12
        a = portable[app_id]
        deps_ids = [f"backup:{a.portable_backup}"] if a.portable_backup else []
        out.append(
            _Draft(
                "shortcut",
                app_id,
                2,
                t("plan.shortcut", name=a.name),
                "user_profile",
                depends_on=deps_ids,
                sort=(_G2["shortcut"], 0, app_id),
            )
        )


def _topo_order(ids: list[str], deps: dict[str, list[str]], apps: dict[str, AppItem]) -> list[str]:
    """Kahn com prioridade (order, id) — determinístico."""
    present = set(ids)
    pending = {i: {d for d in deps[i] if d in present} for i in ids}
    heap = [(apps[i].order, i) for i in ids if not pending[i]]
    heapq.heapify(heap)
    order: list[str] = []
    while heap:
        _, node = heapq.heappop(heap)
        order.append(node)
        for other in ids:
            if node in pending[other]:
                pending[other].discard(node)
                if not pending[other]:
                    heapq.heappush(heap, (apps[other].order, other))
    if len(order) != len(ids):
        raise PlanError("dependências entre apps não puderam ser ordenadas")
    return order


def _plan_tail(recipe: Recipe, ask: Ask, out: list[_Draft], ctx: PlanContext) -> None:
    if ask(recipe.windows.computer_name_decide_at_runtime):
        out.append(
            _Draft(
                "rename_computer",
                "computer",
                2,
                t("plan.rename_computer"),
                "machine",
                user_choice=True,
                sort=(_G2["rename_computer"], 0, "computer"),
            )
        )
    if recipe.updates.windows_update_after_install:  # R14
        out.append(
            _Draft(
                "windows_update",
                "all",
                2,
                t("plan.windows_update"),
                "machine",
                needs_network=True,
                user_choice=ask(True),
                sort=(_G2["windows_update"], 0, "all"),
            )
        )
    if recipe.compare_after_install and ctx.mode == "install":  # R29
        out.append(
            _Draft(
                "compare",
                "after",
                2,
                t("plan.compare"),
                "machine",
                needs_pendrive=True,
                sort=(_G2["compare"], 0, "after"),
            )
        )
    if recipe.updates.fix_missing_drivers:  # R28
        out.append(
            _Draft(
                "driver_report",
                "devices",
                2,
                t("plan.driver_report"),
                "machine",
                sort=(_G2["driver_report"], 0, "devices"),
            )
        )
    out.append(
        _Draft(
            "finalize",
            "summary",
            2,
            t("plan.finalize"),
            "machine",
            sort=(_G2["finalize"], 0, "summary"),
        )
    )


def _plan_live_and_restore(recipe: Recipe, ctx: PlanContext, out: list[_Draft]) -> None:
    """R30/R31: ponto de restauração e particularidades do modo ao vivo."""
    if ctx.mode == "live":
        if ctx.restore_before:
            out.append(
                _Draft(
                    "restore_point",
                    "before",
                    2,
                    t("plan.restore_before"),
                    "machine",
                    sort=(_LIVE_FIRST, 0, "before"),
                )
            )
        name = recipe.windows.computer_name
        if name and not any(d.kind == "rename_computer" for d in out):
            out.append(
                _Draft(
                    "rename_computer",
                    "computer",
                    2,
                    t("plan.rename_computer"),
                    "machine",
                    sort=(_G2["rename_computer"], 0, "computer"),
                )
            )
        return
    if recipe.restore_point.enabled:
        out.append(
            _Draft(
                "restore_point",
                "ready",
                2,
                t("plan.restore_ready"),
                "machine",
                sort=(_G2["restore_point"], 0, "ready"),
            )
        )


# ------------------------------------------------------------------ montagem final
def _finalize(drafts: list[_Draft], ctx: PlanContext) -> list[PlannedStep]:
    ids = [d.id for d in drafts]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise PlanError(f"etapas repetidas: {sorted(dupes)}")
    known = set(ids)

    steps: list[tuple[tuple[int, int, int, str], PlannedStep]] = []
    for d in drafts:
        phase, target, moved = d.phase, d.target, False
        if not ctx.phase1_ran and d.phase == 1:  # fallback (D-012)
            phase, moved = 2, True
            if target == "default_profile":
                target = "user_profile"
        group, sub, name = d.sort
        if moved and d.kind != "restore_point":
            key = (phase, _FALLBACK_GROUP, group * 10000 + sub, name)
        else:
            key = (phase, group, sub, name)
        steps.append(
            (
                key,
                PlannedStep(
                    id=d.id,
                    kind=d.kind,
                    ref=d.ref,
                    phase=phase,
                    title=d.title,
                    target=target,
                    needs_pendrive=d.needs_pendrive,
                    needs_network=d.needs_network,
                    depends_on=tuple(x for x in d.depends_on if x in known),
                    user_choice=d.user_choice,
                    moved_from_phase1=moved,
                    phase2_fallback=d.phase2_fallback and not moved,
                ),
            )
        )
    steps.sort(key=lambda item: item[0])
    return [s for _, s in steps]

"""English (United States) texts. Same keys and placeholders as ``pt_br`` (R-51)."""

from __future__ import annotations

from winkit.i18n.core import Entry, Plural

MESSAGES: dict[str, Entry] = {
    "legacy.text": "{text}",
    # ---------------------------------------------------------------- general
    "app.name": "WinKit",
    "error.unexpected": "Unexpected error: {detail}. See the log for details.",
    "error.not_windows": "This command only works on Windows.",
    "error.needs_admin": "This command must be run as administrator.",
    # ---------------------------------------------------------------- recipe
    "recipe.invalid": "The recipe has problems:\n{problems}",
    "recipe.silent_missing": "In silent mode nobody will answer questions. Fill in: {fields}",
    "recipe.computer_name_invalid": (
        'Invalid computer name: "{name}". Use 1 to 15 characters '
        "(letters, numbers and hyphen), not only numbers."
    ),
    "recipe.username_invalid": 'Invalid user name: "{name}". {reason}',
    "recipe.username_reserved": "This name is reserved by Windows.",
    "recipe.username_chars": 'Do not use the characters \\ / [ ] : ; | = , + * ? < > " @',
    "recipe.password_missing": "The password is set to stored, but it is empty.",
    "recipe.password_stored_warning": (
        "Warning: the password will be readable on the USB drive (Windows only accepts "
        "a plain or Base64 password in the answer file)."
    ),
    "recipe.duplicate_id": 'Duplicate identifier: "{id}" appears more than once in {section}.',
    "recipe.unknown_dependency": '"{id}" depends on "{dep}", which is not in the recipe.',
    "recipe.dependency_cycle": "Circular dependency between: {ids}.",
    "recipe.unknown_backup_ref": '"{app}" refers to the backup "{backup}", which does not exist.',
    "recipe.unknown_tweak": 'Unknown tweak: "{id}".',
    "recipe.unknown_bloat": 'Unknown bloatware package: "{id}".',
    "recipe.blocked_bloat": '"{id}" cannot be removed: {reason}',
    "recipe.missing_installer": 'The app "{id}" needs an installer (field installer.path).',
    "recipe.missing_winget_id": 'The app "{id}" is installed with winget but has no winget_id.',
    "recipe.portable_needs_backup": (
        'The portable app "{id}" must point to the program folder (portable_backup).'
    ),
    "recipe.unknown_installer_type": (
        'The installer of "{id}" is of an unknown type: provide the silent arguments.'
    ),
    "recipe.migration_unsupported": (
        "This recipe was created by a newer version of WinKit (format {found}); "
        "this version understands up to format {supported}."
    ),
    # ---------------------------------------------------------------- paths
    "paths.inside_windows": "Folders inside C:\\Windows cannot be copied: {path}",
    "paths.absolute_warning": (
        "This path is outside the user folders and requires drive {drive} to exist "
        "on the new PC: {path}"
    ),
    "paths.drive_missing": "Drive {drive} does not exist on this PC.",
    # ---------------------------------------------------------------- USB drive / builder
    "pendrive.none": (
        "No Ventoy USB drive was found. Connect the drive (with Ventoy already installed) "
        "and try again."
    ),
    "pendrive.many": "More than one Ventoy USB drive found. Choose one with --pendrive.",
    "pendrive.not_found_letter": "Drive {letter} is not the data partition of a Ventoy USB drive.",
    "pendrive.fat32_big_file": "The USB drive is FAT32, which does not accept files over 4 GB: {path}",
    "pendrive.no_space": (
        "Not enough space on the USB drive: {needed} needed, {free} free "
        "(keeping a {margin} margin)."
    ),
    "builder.summary": "Build summary:",
    "builder.done": "USB drive ready at {root}.",
    "builder.iso_found": "ISO found: {name} — Windows {os} build {build}, {arch}, {langs}",
    "builder.iso_skipped": "Ignored (does not look like a Windows ISO): {name}",
    "builder.no_isos": "No Windows ISO found on the USB drive.",
    "builder.arch_mismatch": (
        "The ISO {name} is {iso_arch}, but the recipe is for {recipe_arch}. It will not get "
        "the WinKit template."
    ),
    "builder.ventoy_json_invalid": (
        "The existing ventoy.json is invalid ({detail}). Nothing was changed. Fix or delete "
        "the file and try again."
    ),
    "builder.confirm": "Continue? [y/N] ",
    "builder.cancelled": "Cancelled. Nothing was changed.",
    "validate.ok": "All good: the USB drive is consistent.",
    "validate.problems": Plural(one="{n} problem was found:", other="{n} problems were found:"),
    "validate.warnings": "Warnings ({count}):",
    # ---------------------------------------------------------------- collector
    "collect.apps_found": Plural(one="{n} app found.", other="{n} apps found."),
    "collect.drivers_found": Plural(
        one="{n} third-party driver found.", other="{n} third-party drivers found."
    ),
    "collect.vss_unavailable": (
        "Could not create the shadow copy of {volume} ({detail}). Copying directly: "
        "files in use may fail."
    ),
    "collect.vss_not_ntfs": "{volume} is not an internal NTFS disk; copying without a shadow copy.",
    "collect.dpapi_warning": "{path}: {what}. It will be backed up, but it will not work on the new PC.",
    "collect.close_app_hint": (
        "Tip: close {app} before capturing; open databases may become inconsistent."
    ),
    "collect.many_files": "{path} has {count} files; copying to the USB drive may take a while.",
    # ---------------------------------------------------------------- agent
    "agent.title": "WinKit — Finishing setup",
    "agent.done_before_login": "Already done before sign-in",
    "agent.todo_now": "To do now",
    "agent.starting_in": "Starting in {seconds} s…",
    "agent.start": "Start",
    "agent.postpone": "Postpone to next sign-in",
    "agent.progress": "{done} of {total} — {current}",
    "agent.tray_tip": "WinKit: {done} of {total} — {current}",
    "agent.finished": "WinKit finished",
    "agent.finished_with_warnings": Plural(
        one="WinKit finished — {n} warning", other="WinKit finished — {n} warnings"
    ),
    "agent.finished_with_failures": Plural(
        one="WinKit finished — {n} failure. Open the summary.",
        other="WinKit finished — {n} failures. Open the summary.",
    ),
    "agent.reconnect_pendrive": "Reconnect the WinKit USB drive to continue.",
    "agent.reboot_needed": "A restart is needed to continue the setup.",
    "agent.reboot_now": "Restart now",
    "agent.reboot_later": "Later",
    "agent.reboot_idle_warning": "The computer will restart in {seconds} s to continue the setup.",
    "agent.summary_shortcut": "WinKit summary",
    "agent.already_running": "WinKit is already running.",
    "agent.waiting_winget": "Waiting for winget to become available…",
    "agent.waiting_network": "Waiting for an internet connection…",
    # ---------------------------------------------------------------- agent window
    "ui.ask": "Ask",
    "ui.ask_tip": "Show in the first sign-in window to confirm at that moment",
    "ui.agent.title": "Finishing setup",
    "ui.agent.subtitle": "Windows is installed. Almost there to make it your own.",
    "ui.agent.nothing_before": "Nothing — everything will be done now.",
    "ui.agent.included": "included",
    "ui.agent.only_summary": "Only the summary is left.",
    "ui.agent.todo_footer": "Turn off what you do not want now. Items without a switch are part of the recipe.",
    "ui.agent.countdown_paused": "Countdown paused — click Start when you are ready.",
    "ui.agent.progress_title": "Setting up…",
    "ui.agent.minimize": "Continue in the background",
    "ui.agent.open_summary": "Open summary",
    "ui.agent.close": "Close",
    "ui.agent.all_done": "All done",
    "ui.agent.done_with_failures": "Finished with pending items",
    "ui.agent.reboot_title": "Restart now?",
    "ui.agent.show_progress": "Show progress",
    "ui.count.driver": Plural(one="{n} driver installed", other="{n} drivers installed"),
    "ui.count.bloat": Plural(
        one="{n} preinstalled app removed", other="{n} preinstalled apps removed"
    ),
    "ui.count.tweak": Plural(one="{n} tweak applied", other="{n} tweaks applied"),
    "ui.count.power": Plural(one="Power plan adjusted", other="Power plan adjusted"),
    "ui.count.backup": Plural(one="{n} setting restored", other="{n} settings restored"),
    "ui.count.app": Plural(one="{n} app installed", other="{n} apps installed"),
    # ---------------------------------------------------------------- step titles
    "plan.driver": "Driver: {name}",
    "plan.bloat": "Remove: {name}",
    "plan.tweak": "Tweak: {name}",
    "plan.power": "Power plan",
    "plan.backup": "Restore: {name}",
    "plan.app": "Install: {name}",
    "plan.shortcut": "Shortcuts: {name}",
    "plan.rename_computer": "Computer name",
    "plan.windows_update": "Windows Update",
    "plan.finalize": "Finish and create summary",
    "plan.excluded_os": "does not apply to this Windows version",
    "plan.excluded_unknown_tweak": "unknown tweak in the catalog",
    "plan.excluded_specialize": "applied during Windows setup",
    "plan.excluded_unknown_bloat": "unknown package in the catalog",
    # ---------------------------------------------------------------- summary
    "summary.title": "WinKit summary",
    "summary.total_time": "Total time: {duration}",
    "summary.phase_time": "Phase {phase}: {duration}",
    "summary.counts": "{done} done · {failed} failed · {skipped} skipped",
    "summary.failures": "Failures",
    "summary.warnings": "Warnings",
    "summary.open_log": "Open log",
    "summary.retry_failed": "Retry the failed ones",
    "summary.remove_shortcut": "Delete this shortcut",
    "summary.set_password": "Your account has no password. Set one in Settings > Accounts.",
    # ---------------------------------------------------------------- steps (reasons)
    "step.dependency_failed": 'not run because "{dep}" failed',
    "step.already_done": "was already done",
    "step.drive_missing": "drive {drive} does not exist",
    "step.no_network": "no internet connection; will be retried at the next sign-in",
    "step.winget_unavailable": "winget did not become available; will be retried at the next sign-in",
    "step.exit_code": "the installer returned code {code}",
    "step.timeout": "the installer exceeded the {minutes} min time limit",
    "step.hash_mismatch": "the file on the USB drive is corrupted or was changed: {path}",
    "step.not_selected": "turned off in the window",
    "step.manual_install_hint": "Install it manually; the installer is at {path}",
    "step.os_not_applicable": "does not apply to this Windows version",
    "step.failed_generic": "failed: {detail}",
}

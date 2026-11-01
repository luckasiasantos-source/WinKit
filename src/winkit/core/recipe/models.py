"""Modelo da receita (PLANO.md §6).

A receita é a única entrada do Agente. Campos e valores padrão aqui são o contrato
entre o Studio e o Agente; mudança incompatível exige nova ``schema_version`` e
migração em ``migrations.py`` (R-47).
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from winkit.i18n.languages import LanguageChoice

#: Identificadores de itens: minúsculas, números, ponto, hífen e sublinhado (R-05).
ItemId = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,79}$")]
#: Caminho relativo à pasta ``WinKit`` do pendrive, sempre com barras normais.
PayloadPath = Annotated[str, Field(min_length=1, max_length=400)]

ExecutionMode = Literal["silent", "countdown", "interactive"]
RebootPolicy = Literal["ask", "auto_if_idle", "never"]
Edition = Literal[
    "home", "home_single_language", "pro", "pro_n", "pro_workstations", "education", "enterprise"
]
Architecture = Literal["amd64", "arm64"]
AppSource = Literal["offline", "winget_online", "portable"]
Scope = Literal["machine", "user"]
InstallerType = Literal[
    "msi", "msix", "inno", "nsis", "wix_burn", "installshield", "squirrel", "exe_custom", "unknown"
]
ConflictPolicy = Literal["merge", "overwrite", "skip"]
BackupKind = Literal["folder", "file"]
PowerScheme = Literal["unchanged", "balanced", "high_performance", "ultimate"]
OsMajor = Literal[10, 11]

SCHEMA_VERSION: Literal[1] = 1


def _only_11() -> list[OsMajor]:
    return [11]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, validate_assignment=True)


class VolumeRef(_Model):
    """Volume fora do disco do sistema, achado pelo número de série (D-035, R-52)."""

    serial: Annotated[str, Field(pattern=r"^[0-9A-F]{8}$")]
    label: str | None = None
    #: Só informativo: a letra que o volume tinha no PC antigo. Nunca usada para achar o volume.
    letter_hint: Annotated[str, Field(pattern=r"^[A-Z]$")] | None = None
    size: int = 0


class Meta(_Model):
    profile_id: Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,39}$")] = "padrao"
    pendrive_id: Annotated[str, Field(min_length=8, max_length=64)]
    created_at: datetime
    updated_at: datetime
    winkit_version: str
    source_pc: str | None = None
    #: Serial do volume do sistema antigo (V2-13/V2-14): o que estiver nele será formatado.
    source_system_volume: Annotated[str, Field(pattern=r"^[0-9A-F]{8}$")] | None = None
    #: V2-21: última vez que os instaladores do pendrive foram conferidos.
    last_update_check: datetime | None = None
    #: V2-20: sugestões que o usuário ignorou (não voltam).
    dismissed_suggestions: list[str] = Field(default_factory=list)


class Execution(_Model):
    mode: ExecutionMode = "countdown"
    countdown_seconds: Annotated[int, Field(ge=5, le=600)] = 30
    show_tray_icon: bool = True
    notify_on_finish: bool = True
    desktop_summary_shortcut: bool = True
    reboot_policy: RebootPolicy = "ask"
    #: Idioma da janela do primeiro login e do resumo (D-030); ``auto`` = idioma do Windows novo.
    language: LanguageChoice = "auto"


class Account(_Model):
    username: Annotated[str, Field(min_length=1, max_length=20)]
    display_name: str | None = None
    password_mode: Literal["empty", "stored"] = "empty"  # noqa: S105 — modo, não senha
    password: str | None = Field(default=None, repr=False)
    auto_logon: bool = True


class ExtraAccount(_Model):
    """V2-11: outra conta local criada na instalação (o login automático fica só na principal)."""

    username: Annotated[str, Field(min_length=1, max_length=20)]
    display_name: str | None = None
    group: Literal["administrators", "users"] = "users"
    #: ``must_change``: nasce sem senha e o Windows pede uma nova no primeiro login.
    password_mode: Literal["empty", "stored", "must_change"] = "must_change"  # noqa: S105
    password: str | None = Field(default=None, repr=False)


class WindowsSettings(_Model):
    target_os: list[OsMajor] = Field(default_factory=_only_11)
    edition: Edition = "pro"
    architecture: Architecture = "amd64"
    ui_language: str = "auto"
    input_locale: str = "0416:00010416"
    user_locale: str = "pt-BR"
    system_locale: str = "pt-BR"
    time_zone: str = "E. South America Standard Time"
    computer_name: str | None = None
    computer_name_decide_at_runtime: bool = False
    #: D-020: ligado por padrão — o Windows não criptografa o disco sozinho.
    prevent_device_encryption: bool = True
    account: Account
    #: V2-08: ids de ``features.yaml`` a ligar (nunca desliga nada).
    optional_features: list[ItemId] = Field(default_factory=list)
    #: V2-11: contas locais além da principal.
    extra_accounts: list[ExtraAccount] = Field(default_factory=list)


class Updates(_Model):
    during_setup: bool = False
    windows_update_after_install: bool = True
    include_drivers_from_windows_update: bool = False
    block_wu_driver_replacement: bool = True
    #: V2-09: no fim, procurar no Windows Update os drivers dos dispositivos que ficaram sem.
    fix_missing_drivers: bool = True


class DriverItem(_Model):
    id: ItemId
    selected: bool = True
    path: PayloadPath
    class_name: str = Field(alias="class")
    provider: str = ""
    version: str = ""
    original_inf: str = ""
    priority: Annotated[int, Field(ge=0, le=9)] = 5


class InstallerSpec(_Model):
    path: PayloadPath | None = None
    type: InstallerType = "unknown"
    args: list[str] = Field(default_factory=list)
    success_codes: list[int] = Field(default_factory=lambda: [0])
    reboot_codes: list[int] = Field(default_factory=lambda: [3010, 1641])
    timeout_minutes: Annotated[int, Field(ge=1, le=240)] = 30
    sha256: str | None = None


class AutostartEntry(_Model):
    hive: Literal["HKCU", "HKLM"] = "HKCU"
    key: str = r"Software\Microsoft\Windows\CurrentVersion\Run"
    value: str


class ShortcutSpec(_Model):
    name: str
    target: str  # molde de caminho, ex.: {LOCALAPPDATA}\App\app.exe
    arguments: str = ""
    location: Literal["desktop", "start_menu"] = "start_menu"


class AfterInstall(_Model):
    kill_processes: list[str] = Field(default_factory=list)
    disable_autostart: list[AutostartEntry] = Field(default_factory=list)
    shortcuts: list[ShortcutSpec] = Field(default_factory=list)


class AppItem(_Model):
    id: ItemId
    name: str
    selected: bool = True
    source: AppSource = "offline"
    scope: Scope = "machine"
    installer: InstallerSpec | None = None
    winget_id: str | None = None
    winget_source: Literal["winget", "msstore"] = "winget"
    #: Para ``source=portable``: id do backup que contém a pasta do programa.
    portable_backup: ItemId | None = None
    #: O instalador recusa rodar elevado (ex.: Spotify) — DT-002.
    requires_non_elevated: bool = False
    after_install: AfterInstall = Field(default_factory=AfterInstall)
    order: Annotated[int, Field(ge=0, le=9999)] = 100
    depends_on: list[ItemId] = Field(default_factory=list)
    restore_backups_after_install: list[ItemId] = Field(default_factory=list)
    decide_at_runtime: bool = False
    #: V2-21: versão do instalador offline no pendrive (do manifesto do winget).
    installer_version: str | None = None


class BackupItem(_Model):
    id: ItemId
    name: str
    selected: bool = True
    kind: BackupKind = "folder"
    template: str
    data_path: PayloadPath
    exclude: list[str] = Field(default_factory=list)
    on_conflict: ConflictPolicy = "merge"
    related_app: ItemId | None = None
    decide_at_runtime: bool = False
    warnings: list[str] = Field(default_factory=list)
    #: V2-11: ``main`` = só a conta principal (Fase 2), em vez do perfil padrão de todas.
    for_accounts: Literal["all", "main"] = "all"


class Bloatware(_Model):
    remove: list[str] = Field(default_factory=list)
    block_reinstall: bool = True
    disable_consumer_content: bool = True


class TweakSelection(_Model):
    id: str
    enabled: bool = True
    decide_at_runtime: bool = False


WifiSecurity = Literal["open", "wpa2_personal", "wpa3_personal", "enterprise", "other"]


class WifiNetwork(_Model):
    """V2-02: rede Wi-Fi levada do PC antigo (M14). A senha fica no arquivo, nunca aqui (D-036)."""

    id: ItemId
    ssid: str
    security: WifiSecurity = "wpa2_personal"
    include_key: bool = True
    selected: bool = True
    file: PayloadPath


class Wifi(_Model):
    networks: list[WifiNetwork] = Field(default_factory=list)


class Dns(_Model):
    """V2-16: servidor DNS e bloqueios pelo ``hosts`` (M14)."""

    #: ``unchanged``, id de ``dns_providers.yaml`` ou ``custom``.
    provider: str = "unchanged"
    #: Id pessoal dos serviços que exigem (NextDNS).
    provider_id: str | None = None
    custom_servers: list[str] = Field(default_factory=list)
    custom_doh_template: str | None = None
    #: Exigir DNS criptografado (só Windows 11); desligado = permitir.
    require_doh: bool = False
    hosts_blocklists: list[ItemId] = Field(default_factory=list)


class NetworkDrive(_Model):
    """V2-17: unidade de rede mapeada (a senha do servidor nunca é levada)."""

    letter: Annotated[str, Field(pattern=r"^[D-Z]$")]
    remote_path: Annotated[str, Field(pattern=r"^\\\\[^\\]+\\.+")]
    label: str | None = None
    selected: bool = True


Weekday = Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


class Maintenance(_Model):
    """V2-18: o Windows novo se mantém sozinho."""

    #: ``monthly`` = a cada 4 semanas (o agendador do PowerShell não tem gatilho mensal).
    winget_upgrade: Literal["off", "weekly", "monthly"] = "off"
    winget_day: Weekday = "sun"
    winget_time: Annotated[str, Field(pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$")] = "12:00"
    storage_sense: bool = False
    ensure_defrag_schedule: bool = True


EnvScope = Literal["user", "machine"]


class EnvVar(_Model):
    """V2-22: variável de ambiente; o valor usa ``%USERPROFILE%`` etc. quando aponta para perfis."""

    name: Annotated[str, Field(pattern=r"^[A-Za-z_][A-Za-z0-9_.()-]{0,99}$")]
    value: str
    scope: EnvScope = "user"
    kind: Literal["sz", "expand_sz"] = "expand_sz"
    #: R-21: por padrão nunca sobrescreve um valor diferente que já exista.
    on_conflict: Literal["skip", "replace"] = "skip"
    selected: bool = True


class EnvPathEntry(_Model):
    """Pasta a acrescentar no fim do PATH (nunca remove nada)."""

    value: Annotated[str, Field(min_length=2)]
    scope: EnvScope = "user"
    selected: bool = True


class Environment(_Model):
    variables: list[EnvVar] = Field(default_factory=list)
    path_entries: list[EnvPathEntry] = Field(default_factory=list)


class FontItem(_Model):
    """V2-07: fonte instalada no PC antigo; o arquivo vai para ``Perfis/<p>/Fontes``."""

    id: ItemId
    family: str
    full_name: str
    #: Arquivo no pendrive (relativo a ``WinKit``); vazio até a fonte ser marcada e copiada.
    file: str = ""
    source: str  # caminho no PC antigo (só para a tela)
    origin: Scope = "user"
    size: int = 0
    sha256: str | None = None
    selected: bool = False


class DefaultApps(_Model):
    """V2-05: apps padrão. O XML exportado fica inteiro no pendrive; os grupos filtram."""

    enabled: bool = False
    associations_file: PayloadPath | None = None
    groups: list[ItemId] = Field(default_factory=list)


class PersonalValue(_Model):
    type: Literal["dword", "sz", "expand_sz", "binary"]
    data: int | str  # binário em hexadecimal


class Personal(_Model):
    """V2-06: aparência pessoal; os valores são capturados e validados pelo catálogo (D-037)."""

    groups: list[ItemId] = Field(default_factory=list)
    #: ``<chave>\<valor>`` → valor capturado.
    values: dict[str, PersonalValue] = Field(default_factory=dict)
    wallpaper_file: PayloadPath | None = None


class BrowserExtension(_Model):
    """Extensão pelo id da loja (Chromium: 32 letras a–p; Firefox: e-mail ou GUID)."""

    id: Annotated[str, Field(min_length=3, max_length=80)]
    name: str = ""
    #: Nome curto no addons.mozilla.org (só Firefox; sem ele, usa o id).
    slug: str | None = None
    selected: bool = True


class BrowserConfig(_Model):
    """V2-12: um navegador pronto. Senhas, cookies e login nunca são levados."""

    id: ItemId  # id de browsers.yaml
    extensions: list[BrowserExtension] = Field(default_factory=list)
    homepage: Annotated[str, Field(pattern=r"^https?://")] | None = None
    search: str | None = None  # id de search_providers.yaml
    #: ``suggest`` = o usuário pode mudar (D-038); ``force`` = políticas obrigatórias.
    mode: Literal["suggest", "force"] = "suggest"
    selected: bool = True


class PinRef(_Model):
    """Um ícone fixado: atalho do menu Iniciar (molde ``%APPDATA%\\…\\X.lnk``) ou app da Store."""

    kind: Literal["desktop_link", "packaged_app"]
    value: str
    name: str
    selected: bool = True


class StartLayout(_Model):
    """V2-04: Iniciar e barra de tarefas. ``exact`` copia o ``start2.bin`` (mesma versão)."""

    mode: Literal["off", "list", "exact"] = "off"
    start_file: PayloadPath | None = None
    #: Build do Windows de onde veio o ``start2.bin`` (o modo exato só vale no mesmo build).
    source_build: int | None = None
    start_pins: list[PinRef] = Field(default_factory=list)
    taskbar_pins: list[PinRef] = Field(default_factory=list)


UserFolderId = Literal["desktop", "documents", "downloads", "pictures", "videos", "music"]


#: Caminho relativo à raiz de um volume: nunca com letra de unidade (R-52).
def _volume_relative(value: str) -> str:
    if (len(value) >= 2 and value[1] == ":") or value.startswith(("\\", "/")):
        raise ValueError("caminho relativo ao volume, sem letra de unidade (R-52)")
    return value


VolumeRelative = Annotated[str, Field(min_length=1), AfterValidator(_volume_relative)]


class UserFolders(_Model):
    """V2-14: Documentos, Downloads… num outro disco, achado pelo serial (D-035)."""

    enabled: bool = False
    volume: VolumeRef | None = None
    #: Pasta → caminho no volume (aceita ``%USERNAME%``), ex.: ``Usuarios\%USERNAME%\Documentos``.
    folders: dict[UserFolderId, VolumeRelative] = Field(default_factory=dict)


class GameLibrary(_Model):
    """V2-13: biblioteca de jogos num outro disco (Steam) ou um jogo da Epic."""

    id: ItemId
    launcher: Literal["steam", "epic"]
    name: str
    volume: VolumeRef
    relative_path: VolumeRelative  # ex.: "SteamLibrary" (nunca com letra, R-52)
    games: int = 0
    #: Manifesto ``.item`` da Epic copiado para o pendrive.
    manifest: PayloadPath | None = None
    selected: bool = True


class RestorePoint(_Model):
    """V2-10: ponto de restauração "Windows pronto" no fim da instalação (M12)."""

    enabled: bool = True
    max_disk_percent: Annotated[int, Field(ge=1, le=50)] = 5


class Power(_Model):
    scheme: PowerScheme = "unchanged"
    hibernate: bool | None = None
    fast_startup: bool | None = None


TargetVersion = Literal["11", "10"]
MediaPath = Literal["ventoy", "rufus", "microsoft"]


class PcBackup(_Model):
    """Backup do PC para outro disco (V3-09/10, D-051). Sem senha, sem versões antigas."""

    sources: list[str] = Field(default_factory=list)  # pastas do PC atual (caminhos literais)
    destination: VolumeRef | None = None
    zip: bool = False
    #: Na Fase 2, o Agente traz os arquivos de volta do disco de backup (soma, nunca troca).
    restore_after_install: bool = False


class TargetWindows(_Model):
    """Windows que vai ser instalado (V3-06). O 8.1 e o 7 entram no M25."""

    version: TargetVersion = "11"
    arch: Literal["x64", "x86"] = "x64"  # o Windows 11 só existe em 64 bits


class Media(_Model):
    """Como o Windows chega ao PC (V3-06): pendrive Ventoy, do Rufus ou da Microsoft."""

    path: MediaPath = "ventoy"


class Recipe(_Model):
    schema_version: Literal[1] = SCHEMA_VERSION
    meta: Meta
    execution: Execution = Field(default_factory=Execution)
    windows: WindowsSettings
    updates: Updates = Field(default_factory=Updates)
    drivers: list[DriverItem] = Field(default_factory=list)
    apps: list[AppItem] = Field(default_factory=list)
    backups: list[BackupItem] = Field(default_factory=list)
    bloatware: Bloatware = Field(default_factory=Bloatware)
    tweaks: list[TweakSelection] = Field(default_factory=list)
    power: Power = Field(default_factory=Power)
    restore_point: RestorePoint = Field(default_factory=RestorePoint)
    wifi: Wifi = Field(default_factory=Wifi)
    dns: Dns = Field(default_factory=Dns)
    network_drives: list[NetworkDrive] = Field(default_factory=list)
    maintenance: Maintenance = Field(default_factory=Maintenance)
    environment: Environment = Field(default_factory=Environment)
    #: V2-15: perfis rápidos já aplicados (só histórico, para a tela).
    presets_applied: list[str] = Field(default_factory=list)
    fonts: list[FontItem] = Field(default_factory=list)
    default_apps: DefaultApps = Field(default_factory=DefaultApps)
    personal: Personal = Field(default_factory=Personal)
    browsers: list[BrowserConfig] = Field(default_factory=list)
    start_layout: StartLayout = Field(default_factory=StartLayout)
    user_folders: UserFolders = Field(default_factory=UserFolders)
    game_libraries: list[GameLibrary] = Field(default_factory=list)
    #: V2-19: no fim da instalação, comparar com o inventário do PC antigo.
    compare_after_install: bool = True
    #: V3-06: Windows a instalar e caminho até o pendrive (orienta o Studio).
    target_windows: TargetWindows = Field(default_factory=TargetWindows)
    media: Media = Field(default_factory=Media)
    pc_backup: PcBackup = Field(default_factory=PcBackup)

    # ---- consultas de conveniência (sem efeito colateral)
    def app(self, app_id: str) -> AppItem | None:
        return next((a for a in self.apps if a.id == app_id), None)

    def backup(self, backup_id: str) -> BackupItem | None:
        return next((b for b in self.backups if b.id == backup_id), None)

    def selected_apps(self) -> list[AppItem]:
        return [a for a in self.apps if a.selected]

    def selected_backups(self) -> list[BackupItem]:
        return [b for b in self.backups if b.selected]

    def selected_drivers(self) -> list[DriverItem]:
        return [d for d in self.drivers if d.selected]

    def enabled_tweaks(self) -> list[TweakSelection]:
        return [t for t in self.tweaks if t.enabled]

"""Modelos dos catálogos em ``winkit/data`` (PLANO.md §15, R-32 a R-34)."""

from __future__ import annotations

import ipaddress
import re
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from winkit.core.recipe.models import (
    AfterInstall,
    Edition,
    InstallerType,
    OsMajor,
    PowerScheme,
    Scope,
)

Hive = Literal["HKLM", "HKCU"]
RegType = Literal["dword", "qword", "sz", "expand_sz", "multi_sz", "binary"]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


def _both_os() -> list[OsMajor]:
    return [10, 11]


class OsFilter(_Model):
    os: list[OsMajor] = Field(default_factory=_both_os)
    min_build: int | None = None
    max_build: int | None = None
    #: Edições em que o item existe (vazio = todas), ex.: Sandbox só a partir do Pro.
    editions: list[Edition] = Field(default_factory=list)

    def allows_edition(self, edition: str | None) -> bool:
        return not self.editions or edition is None or edition in self.editions

    def applies(self, os_major: int | None, build: int | None) -> bool:
        if os_major is not None and os_major not in self.os:
            return False
        if build is None:
            return True
        if self.min_build is not None and build < self.min_build:
            return False
        return self.max_build is None or build <= self.max_build


# ------------------------------------------------------------------ ajustes
class RegSet(_Model):
    key: str
    value: str
    type: RegType
    data: int | str | list[str]
    hive: Hive | None = None  # padrão: pelo escopo do ajuste

    @model_validator(mode="after")
    def _check_data(self) -> Self:
        if self.type in ("dword", "qword") and not isinstance(self.data, int):
            raise ValueError(f"{self.value}: {self.type} exige número")
        if self.type == "multi_sz" and not isinstance(self.data, list):
            raise ValueError(f"{self.value}: multi_sz exige lista")
        if self.type in ("sz", "expand_sz", "binary") and not isinstance(self.data, str):
            raise ValueError(f"{self.value}: {self.type} exige texto (binary em hexadecimal)")
        return self


class RegDeleteValue(_Model):
    key: str
    value: str
    hive: Hive | None = None


class RegDeleteKey(_Model):
    key: str
    hive: Hive | None = None


class ServiceStartType(_Model):
    service: str
    start: Literal["automatic", "manual", "disabled"]


class OptionalFeature(_Model):
    feature: str


class Capability(_Model):
    name: str


class Powercfg(_Model):
    args: list[str]

    @model_validator(mode="after")
    def _only_known(self) -> Self:
        allowed = {"/setactive", "/hibernate", "/change", "/duplicatescheme"}
        if not self.args or self.args[0].lower() not in allowed:
            raise ValueError(f"powercfg só aceita {sorted(allowed)}")
        return self


class AppxRemove(_Model):
    package: str


class TweakOp(_Model):
    """Exatamente uma operação tipada por item (não existe comando arbitrário — R-34)."""

    reg_set: RegSet | None = None
    reg_delete_value: RegDeleteValue | None = None
    reg_delete_key: RegDeleteKey | None = None
    service_start_type: ServiceStartType | None = None
    optional_feature_disable: OptionalFeature | None = None
    optional_feature_enable: OptionalFeature | None = None
    capability_add: Capability | None = None
    capability_remove: Capability | None = None
    powercfg: Powercfg | None = None
    appx_remove: AppxRemove | None = None

    def _present(self) -> list[str]:
        return [name for name in type(self).model_fields if getattr(self, name) is not None]

    @model_validator(mode="after")
    def _exactly_one(self) -> Self:
        if len(self._present()) != 1:
            raise ValueError("cada operação deve ter exatamente um tipo")
        return self

    @property
    def kind(self) -> str:
        return self._present()[0]


class Tweak(_Model):
    id: Annotated[str, Field(pattern=r"^[a-z]+\.[a-z0-9_]+$")]
    title: str
    description: str
    category: Literal["privacy", "visual", "power", "system", "maintenance", "gaming"]
    risk: Literal["safe", "caution"] = "safe"
    scope: Scope
    windows: OsFilter = Field(default_factory=OsFilter)
    source: Annotated[str, Field(min_length=5)]
    recommended: bool = False
    #: Etapa do Windows em que roda: ``agent`` (padrão) ou ``specialize`` (via XML).
    stage: Literal["agent", "specialize"] = "agent"
    apply: Annotated[list[TweakOp], Field(min_length=1)]
    undo: Annotated[list[TweakOp], Field(min_length=1)]


# ------------------------------------------------------------------ bloatware
class BloatwareEntry(_Model):
    id: str  # nome do pacote Appx, ex.: "Microsoft.BingNews"
    name: str
    risk: Literal["safe", "caution", "blocked"]
    publisher_id: str = "8wekyb3d8bbwe"
    side_effect: str | None = None
    reason: str | None = None  # obrigatório para blocked
    recommended: bool = False
    windows: OsFilter = Field(default_factory=OsFilter)

    @property
    def family_name(self) -> str:
        return f"{self.id}_{self.publisher_id}"

    @model_validator(mode="after")
    def _blocked_has_reason(self) -> Self:
        if self.risk == "blocked" and not self.reason:
            raise ValueError(f"{self.id}: item bloqueado precisa de 'reason'")
        if self.risk == "caution" and not self.side_effect:
            raise ValueError(f"{self.id}: item 'caution' precisa de 'side_effect'")
        if self.risk == "blocked" and self.recommended:
            raise ValueError(f"{self.id}: item bloqueado não pode ser recomendado")
        return self


# ------------------------------------------------------------------ apps
class AppMatch(_Model):
    display_name_regex: str | None = None
    winget_ids: list[str] = Field(default_factory=list)


class CatalogInstaller(_Model):
    type: InstallerType
    args: list[str] = Field(default_factory=list)
    success_codes: list[int] = Field(default_factory=lambda: [0])
    timeout_minutes: int = 30


class ConfigPath(_Model):
    template: str
    kind: Literal["folder", "file"] = "folder"
    recommended: bool = False
    warning: str | None = None  # id de padrão em dpapi_patterns
    exclude: list[str] = Field(default_factory=list)


class AppCatalogEntry(_Model):
    id: Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")]
    name: str
    match: AppMatch
    scope: Scope
    installer: CatalogInstaller | None = None
    after_install: AfterInstall = Field(default_factory=AfterInstall)
    config_paths: list[ConfigPath] = Field(default_factory=list)
    installer_wipes_config: bool = False
    requires_non_elevated: bool = False
    close_before_capture: bool = False


# ------------------------------------------------------------------ recursos do Windows
class FeaturePart(_Model):
    """Uma parte de um recurso: um *optional feature* ou uma *capability* (nunca as duas)."""

    feature: str | None = None
    capability: str | None = None
    #: Pasta da mídia de instalação com os arquivos do recurso (ex.: ``sources/sxs``).
    offline_source: str | None = None

    @model_validator(mode="after")
    def _one(self) -> Self:
        if (self.feature is None) == (self.capability is None):
            raise ValueError("cada parte deve ter 'feature' ou 'capability'")
        if self.offline_source is not None and self.feature is None:
            raise ValueError("'offline_source' só vale para 'feature'")
        return self

    @property
    def name(self) -> str:
        return self.feature or self.capability or ""


class FeatureEntry(_Model):
    id: Annotated[str, Field(pattern=r"^[a-z0-9_]+$")]
    name: str
    description: str
    parts: Annotated[list[FeaturePart], Field(min_length=1)]
    #: Precisa de internet quando não há fonte offline (capacidades sempre precisam).
    needs_network: bool = False
    restart: bool = False
    windows: OsFilter = Field(default_factory=OsFilter)
    source: Annotated[str, Field(min_length=5)]

    @property
    def offline_source(self) -> str | None:
        return next((p.offline_source for p in self.parts if p.offline_source), None)

    @model_validator(mode="after")
    def _capability_needs_network(self) -> Self:
        if any(p.capability for p in self.parts) and not self.needs_network:
            raise ValueError(f"{self.id}: capacidades são baixadas e exigem 'needs_network'")
        return self


# ------------------------------------------------------------------ DNS e bloqueios (V2-16)
def _valid_ip(value: str, version: int) -> str:
    addr = ipaddress.ip_address(value)
    if addr.version != version:
        raise ValueError(f"{value}: não é IPv{version}")
    return value


class DnsProvider(_Model):
    id: Annotated[str, Field(pattern=r"^[a-z0-9_]+$")]
    name: str
    ipv4: Annotated[list[str], Field(min_length=1)]
    ipv6: list[str] = Field(default_factory=list)
    #: Modelo DoH (``https://``); ``{id}`` é trocado pelo id pessoal quando ``needs_id``.
    doh_template: str
    family: bool = False
    needs_id: bool = False
    source: Annotated[str, Field(min_length=5)]

    @model_validator(mode="after")
    def _check(self) -> Self:
        for v4 in self.ipv4:
            _valid_ip(v4, 4)
        for v6 in self.ipv6:
            _valid_ip(v6, 6)
        if not self.doh_template.startswith("https://"):
            raise ValueError(f"{self.id}: o modelo DoH deve começar com https://")
        if self.needs_id != ("{id}" in self.doh_template):
            raise ValueError(f"{self.id}: 'needs_id' e '{{id}}' no modelo devem andar juntos")
        return self


class HostsBlocklist(_Model):
    id: Annotated[str, Field(pattern=r"^[a-z0-9_]+$")]
    name: str
    description: str
    source: str
    license: str
    domains: Annotated[list[str], Field(min_length=1)]

    @model_validator(mode="after")
    def _check(self) -> Self:
        for d in self.domains:
            if not re.fullmatch(r"(?:[a-z0-9-]+\.)+[a-z]{2,}", d):
                raise ValueError(f"{self.id}: domínio inválido {d!r}")
        return self


# ------------------------------------------------------------------ variáveis de ambiente (V2-22)
class ProtectedEnv(_Model):
    names: list[str] = Field(default_factory=list)
    default_path_entries: list[str] = Field(default_factory=list)

    def is_protected(self, name: str) -> bool:
        key = name.casefold()
        return any(n.casefold() == key for n in self.names)


# ------------------------------------------------------------------ perfis rápidos (V2-15)
class Preset(_Model):
    """Um clique marca itens que já existem nos outros catálogos (aplicar = mesclar, D-040)."""

    id: Annotated[str, Field(pattern=r"^[a-z0-9_]+$")]
    name: str
    description: str
    tweaks: list[str] = Field(default_factory=list)
    #: Todos os ajustes "safe" destas categorias.
    all_in_category: list[str] = Field(default_factory=list)
    power_scheme: PowerScheme | None = None
    features: list[str] = Field(default_factory=list)
    #: Apps pré-instalados que o perfil nunca remove (ex.: Xbox Game Bar no Gamer).
    bloatware_keep: list[str] = Field(default_factory=list)
    dns_provider: str | None = None
    blocklists: list[str] = Field(default_factory=list)
    storage_sense: bool = False
    winget_weekly: bool = False


# ------------------------------------------------------------------ apps padrão (V2-05)
class AssociationGroup(_Model):
    id: Annotated[str, Field(pattern=r"^[a-z0-9_]+$")]
    name: str
    #: Extensões (``.pdf``) e protocolos (``http``), em minúsculas.
    identifiers: Annotated[list[str], Field(min_length=1)]

    @model_validator(mode="after")
    def _lower(self) -> Self:
        if any(i != i.lower() for i in self.identifiers):
            raise ValueError(f"{self.id}: identificadores em minúsculas")
        return self


# ------------------------------------------------------------------ aparência pessoal (V2-06)
class PersonalValueSpec(_Model):
    key: str  # sempre relativo ao HKCU
    value: str  # "" = valor padrão da chave
    type: Literal["dword", "sz", "expand_sz", "binary"]
    allowed: list[int | str] | None = None
    pattern: str | None = None
    #: Tamanho exato, em bytes, de um valor binário.
    length: int | None = None

    @model_validator(mode="after")
    def _check(self) -> Self:
        if self.pattern is not None:
            re.compile(self.pattern)
        return self


class PersonalGroup(_Model):
    id: Annotated[str, Field(pattern=r"^[a-z0-9_]+$")]
    name: str
    values: list[PersonalValueSpec]
    #: O grupo leva um arquivo (o papel de parede).
    file: bool = False
    source: Annotated[str, Field(min_length=5)]


# ------------------------------------------------------------------ navegadores (V2-12)
CHROMIUM_ID = r"^[a-p]{32}$"
FIREFOX_ID = r"^(\{[0-9a-fA-F-]{36}\}|[A-Za-z0-9._+-]+@[A-Za-z0-9._-]+)$"


class BrowserEntry(_Model):
    id: Annotated[str, Field(pattern=r"^[a-z0-9_]+$")]
    name: str
    engine: Literal["chromium", "firefox"]
    policy_key: str
    #: Extensões externas (modo "sugerir") — só Chromium.
    extensions_key: str | None = None
    #: Pasta de dados, começando pela variável (``LOCALAPPDATA\...`` ou ``APPDATA\...``).
    user_data: str
    winget_ids: list[str] = Field(default_factory=list)
    source: Annotated[str, Field(min_length=5)]


class ExtensionEntry(_Model):
    id: Annotated[str, Field(pattern=r"^[a-z0-9_]+$")]
    name: str
    chromium_id: Annotated[str, Field(pattern=CHROMIUM_ID)] | None = None
    firefox_id: Annotated[str, Field(pattern=FIREFOX_ID)] | None = None
    firefox_slug: str | None = None


class SearchProvider(_Model):
    id: Annotated[str, Field(pattern=r"^[a-z0-9_]+$")]
    name: str
    search_url: Annotated[str, Field(pattern=r"^https://.*\{searchTerms\}")]


# ------------------------------------------------------------------ saves de jogos (V2-20)
class GameSave(_Model):
    id: Annotated[str, Field(pattern=r"^[a-z0-9_]+$")]
    name: str
    template: str


class DownloadSource(_Model):
    """Programa ou arquivo baixado de fonte oficial (R-61, V3-07)."""

    id: Annotated[str, Field(pattern=r"^[a-z0-9_]+$")]
    name: str
    #: Repositório no GitHub (``dono/nome``): a última release é consultada pela API oficial.
    repo: str
    #: Expressão regular do nome do arquivo na release.
    asset: str
    #: Arquivo da release com as somas SHA-256 (``None`` = procurar no texto da release).
    checksum_asset: str | None = None
    #: Para ``.zip``: caminho do executável dentro dele (``{version}`` é trocado).
    exe_in_zip: str | None = None


# ------------------------------------------------------------------ outros
class EditionEntry(_Model):
    id: str
    name: str
    generic_key: Annotated[str, Field(pattern=r"^([A-Z0-9]{5}-){4}[A-Z0-9]{5}$")]
    os: list[OsMajor] = Field(default_factory=_both_os)


class InstallerSignature(_Model):
    type: InstallerType
    markers: list[str] = Field(default_factory=list)  # trechos ASCII procurados no arquivo
    pe_section: str | None = None
    extensions: list[str] = Field(default_factory=list)
    args: list[str]
    scope_hint: Scope | None = None
    needs_confirmation: bool = False


class DpapiPattern(_Model):
    id: str
    glob: str  # relativo à pasta do backup, com '/' ou '\\'
    what: str  # texto pt-BR para o aviso


class DriverClass(_Model):
    name: str  # ClassName do Windows
    label: str
    priority: Annotated[int, Field(ge=0, le=9)] = 5
    recommended: bool = False


class Catalogs(_Model):
    apps: list[AppCatalogEntry]
    tweaks: list[Tweak]
    bloatware: list[BloatwareEntry]
    editions: list[EditionEntry]
    installer_signatures: list[InstallerSignature]
    dpapi_patterns: list[DpapiPattern]
    default_excludes: list[str]
    driver_classes: list[DriverClass]
    features: list[FeatureEntry] = Field(default_factory=list)
    dns_providers: list[DnsProvider] = Field(default_factory=list)
    hosts_blocklists: list[HostsBlocklist] = Field(default_factory=list)
    protected_env: ProtectedEnv = Field(default_factory=ProtectedEnv)
    presets: list[Preset] = Field(default_factory=list)
    association_groups: list[AssociationGroup] = Field(default_factory=list)
    personal_groups: list[PersonalGroup] = Field(default_factory=list)
    browsers: list[BrowserEntry] = Field(default_factory=list)
    extensions: list[ExtensionEntry] = Field(default_factory=list)
    search_providers: list[SearchProvider] = Field(default_factory=list)
    game_saves: list[GameSave] = Field(default_factory=list)
    downloads: list[DownloadSource] = Field(default_factory=list)

    def download(self, source_id: str) -> DownloadSource | None:
        return next((x for x in self.downloads if x.id == source_id), None)

    def browser(self, browser_id: str) -> BrowserEntry | None:
        return next((x for x in self.browsers if x.id == browser_id), None)

    def extension(self, ext_id: str) -> ExtensionEntry | None:
        return next((x for x in self.extensions if x.id == ext_id), None)

    def search_provider(self, provider_id: str) -> SearchProvider | None:
        return next((x for x in self.search_providers if x.id == provider_id), None)

    def personal_group(self, group_id: str) -> PersonalGroup | None:
        return next((x for x in self.personal_groups if x.id == group_id), None)

    def association_group(self, group_id: str) -> AssociationGroup | None:
        return next((x for x in self.association_groups if x.id == group_id), None)

    def preset(self, preset_id: str) -> Preset | None:
        return next((x for x in self.presets if x.id == preset_id), None)

    def dns_provider(self, provider_id: str) -> DnsProvider | None:
        return next((x for x in self.dns_providers if x.id == provider_id), None)

    def blocklist(self, list_id: str) -> HostsBlocklist | None:
        return next((x for x in self.hosts_blocklists if x.id == list_id), None)

    def feature(self, feature_id: str) -> FeatureEntry | None:
        return next((x for x in self.features if x.id == feature_id), None)

    def tweak(self, tweak_id: str) -> Tweak | None:
        return next((x for x in self.tweaks if x.id == tweak_id), None)

    def bloat(self, package: str) -> BloatwareEntry | None:
        return next((x for x in self.bloatware if x.id == package), None)

    def edition(self, edition_id: str) -> EditionEntry | None:
        return next((x for x in self.editions if x.id == edition_id), None)

    def app(self, app_id: str) -> AppCatalogEntry | None:
        return next((x for x in self.apps if x.id == app_id), None)

    def driver_class(self, name: str) -> DriverClass | None:
        key = name.casefold()
        return next((x for x in self.driver_classes if x.name.casefold() == key), None)

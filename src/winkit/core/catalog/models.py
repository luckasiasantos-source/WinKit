"""Modelos dos catálogos em ``winkit/data`` (PLANO.md §15, R-32 a R-34)."""

from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from winkit.core.recipe.models import AfterInstall, InstallerType, OsMajor, Scope

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
    category: Literal["privacy", "visual", "power", "system"]
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

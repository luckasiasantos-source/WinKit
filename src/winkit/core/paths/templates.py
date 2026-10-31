"""Moldes de caminho portáveis entre máquinas (PLANO.md §6.3).

Um molde é ``{VARIAVEL}\\resto`` ou ``{ABS:X:\\caminho}``. A tradução usa a pasta
conhecida de **prefixo mais longo** da máquina de origem; a resolução usa as pastas
conhecidas da máquina de destino (ou do perfil Default, na Fase 1).

Toda a manipulação usa ``ntpath`` para funcionar igual no Linux (testes) e no Windows.
"""

from __future__ import annotations

import ntpath
import re
from collections.abc import Mapping
from dataclasses import dataclass

from winkit.core.errors import PathTemplateError
from winkit.i18n import t

#: Variáveis que dependem do perfil do usuário (resolvidas no Default na Fase 1).
PROFILE_VARS: tuple[str, ...] = (
    "USERPROFILE",
    "APPDATA",
    "LOCALAPPDATA",
    "LOCALLOW",
    "DOCUMENTS",
    "PICTURES",
    "VIDEOS",
    "MUSIC",
    "DESKTOP",
    "DOWNLOADS",
    "SAVEDGAMES",
)
#: Variáveis da máquina (não dependem de perfil).
MACHINE_VARS: tuple[str, ...] = ("PROGRAMDATA", "PROGRAMFILES", "PROGRAMFILESX86", "PUBLIC")
ALL_VARS: tuple[str, ...] = PROFILE_VARS + MACHINE_VARS

#: Layout das pastas de perfil relativo à raiz do perfil, usado para o perfil Default.
#: (No perfil Default não há redirecionamento de OneDrive.)
PROFILE_LAYOUT: Mapping[str, str] = {
    "USERPROFILE": "",
    "APPDATA": r"AppData\Roaming",
    "LOCALAPPDATA": r"AppData\Local",
    "LOCALLOW": r"AppData\LocalLow",
    "DOCUMENTS": "Documents",
    "PICTURES": "Pictures",
    "VIDEOS": "Videos",
    "MUSIC": "Music",
    "DESKTOP": "Desktop",
    "DOWNLOADS": "Downloads",
    "SAVEDGAMES": "Saved Games",
}

_TEMPLATE_RE = re.compile(r"^\{(?P<var>[A-Z0-9]+)(?::(?P<abs>[^}]+))?\}(?P<rest>.*)$")
_DRIVE_RE = re.compile(r"^[A-Za-z]:\\")


@dataclass(frozen=True)
class ParsedTemplate:
    var: str  # nome da variável, ou "ABS"
    rest: str  # parte após a variável, sem barra inicial ("" = a própria pasta)
    absolute: str | None = None  # só para ABS

    @property
    def is_absolute(self) -> bool:
        return self.var == "ABS"

    @property
    def is_profile(self) -> bool:
        return self.var in PROFILE_VARS

    @property
    def drive(self) -> str | None:
        """Letra da unidade (``"D:"``) para moldes absolutos."""
        if self.absolute is None:
            return None
        return ntpath.splitdrive(self.absolute)[0].upper() or None


@dataclass(frozen=True)
class TranslationResult:
    template: str
    parsed: ParsedTemplate
    warning: str | None = None


def normalize(path: str) -> str:
    """Normaliza um caminho do Windows: barras invertidas, sem ``..``, sem barra final."""
    if not path or not path.strip():
        raise PathTemplateError("caminho vazio")
    cleaned = path.strip().replace("/", "\\")
    if cleaned.startswith("\\\\?\\"):
        cleaned = cleaned[4:]
    norm = ntpath.normpath(cleaned)
    if len(norm) > 3:
        norm = norm.rstrip("\\")
    return norm


def _is_under(path: str, root: str) -> bool:
    p, r = path.casefold(), root.casefold().rstrip("\\")
    return p == r or p.startswith(r + "\\")


def _rest(path: str, root: str) -> str:
    return path[len(root.rstrip("\\")) :].lstrip("\\")


def to_template(
    path: str, known_folders: Mapping[str, str], *, windows_dir: str | None = None
) -> TranslationResult:
    """Traduz um caminho literal da máquina de origem para um molde.

    ``known_folders`` mapeia nomes de ``ALL_VARS`` para caminhos absolutos da origem.
    """
    norm = normalize(path)
    if not _DRIVE_RE.match(norm + ("\\" if len(norm) == 2 else "")):
        raise PathTemplateError(f"caminho precisa ser absoluto com letra de unidade: {path}")
    if windows_dir and _is_under(norm, normalize(windows_dir)):
        raise PathTemplateError(t("paths.inside_windows", path=norm))

    best: tuple[int, str, str] | None = None
    for var in ALL_VARS:
        root = known_folders.get(var)
        if not root:
            continue
        root_n = normalize(root)
        if _is_under(norm, root_n) and (best is None or len(root_n) > best[0]):
            best = (len(root_n), var, root_n)

    if best is None:
        parsed = ParsedTemplate(var="ABS", rest="", absolute=norm)
        drive = parsed.drive or "?"
        return TranslationResult(
            template=f"{{ABS:{norm}}}",
            parsed=parsed,
            warning=t("paths.absolute_warning", drive=drive, path=norm),
        )
    _, var, root_n = best
    rest = _rest(norm, root_n)
    template = "{" + var + "}" + (("\\" + rest) if rest else "")
    return TranslationResult(template=template, parsed=ParsedTemplate(var=var, rest=rest))


def parse(template: str) -> ParsedTemplate:
    match = _TEMPLATE_RE.match(template.strip())
    if not match:
        raise PathTemplateError(f"molde inválido: {template!r}")
    var, absolute, rest = match.group("var"), match.group("abs"), match.group("rest")
    rest = rest.replace("/", "\\").lstrip("\\")
    if var == "ABS":
        if absolute is None:
            raise PathTemplateError(f"molde ABS inválido: {template!r}")
        # "{ABS:D:\\Apps\\X}\\x.exe" = arquivo dentro de uma pasta absoluta (apps portáteis)
        norm = normalize(absolute + ("\\" + rest if rest else ""))
        if not _DRIVE_RE.match(norm + ("\\" if len(norm) == 2 else "")):
            raise PathTemplateError(f"molde ABS sem letra de unidade: {template!r}")
        _reject_traversal(norm, template)
        return ParsedTemplate(var="ABS", rest="", absolute=norm)
    if absolute is not None:
        raise PathTemplateError(f"só ABS aceita caminho embutido: {template!r}")
    if var not in ALL_VARS:
        raise PathTemplateError(f"variável desconhecida {{{var}}} em {template!r}")
    _reject_traversal(rest, template)
    return ParsedTemplate(var=var, rest=rest)


def _reject_traversal(rest: str, template: str) -> None:
    if any(part == ".." for part in rest.split("\\")):
        raise PathTemplateError(f"molde não pode conter '..': {template!r}")


def resolve(template: str | ParsedTemplate, folders: Mapping[str, str]) -> str:
    """Resolve um molde para um caminho absoluto da máquina de destino."""
    parsed = parse(template) if isinstance(template, str) else template
    if parsed.absolute is not None:
        return parsed.absolute
    root = folders.get(parsed.var)
    if not root:
        raise PathTemplateError(f"pasta {{{parsed.var}}} desconhecida no destino")
    root_n = normalize(root)
    return ntpath.join(root_n, parsed.rest) if parsed.rest else root_n


def profile_folders(profile_root: str) -> dict[str, str]:
    """Pastas de perfil a partir da raiz (ex.: ``C:\\Users\\Default``), layout padrão."""
    root = normalize(profile_root)
    return {var: (ntpath.join(root, rel) if rel else root) for var, rel in PROFILE_LAYOUT.items()}


def retarget(folders: Mapping[str, str], profile_root: str) -> dict[str, str]:
    """Substitui as pastas de perfil por um perfil-alvo, mantendo as da máquina."""
    out = {k: v for k, v in folders.items() if k in MACHINE_VARS}
    out.update(profile_folders(profile_root))
    return out

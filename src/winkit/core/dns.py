"""DNS seguro e bloqueio pelo ``hosts`` (V2-16): regras puras, sem Windows.

O bloco do WinKit no ``hosts`` fica entre ``# >>> WinKit`` e ``# <<< WinKit``. Todo o resto do
arquivo é preservado **byte a byte**, com a codificação e as quebras de linha originais.
"""

from __future__ import annotations

import codecs
import hashlib
import ipaddress
from dataclasses import dataclass

from winkit.core.catalog.models import Catalogs
from winkit.core.recipe.models import Dns
from winkit.core.text import Msg, msg

BEGIN = "# >>> WinKit"
END = "# <<< WinKit"
SINKHOLE = "0.0.0.0"  # noqa: S104 — endereço de bloqueio do hosts, não um bind


@dataclass(frozen=True)
class DnsTarget:
    ipv4: tuple[str, ...]
    ipv6: tuple[str, ...]
    doh_template: str | None

    @property
    def servers(self) -> tuple[str, ...]:
        return self.ipv4 + self.ipv6


def resolve(dns: Dns, catalogs: Catalogs) -> DnsTarget | None:
    """Servidores e modelo DoH desejados; ``None`` = não mudar o DNS."""
    if dns.provider == "unchanged":
        return None
    if dns.provider == "custom":
        v4 = tuple(s for s in dns.custom_servers if ipaddress.ip_address(s).version == 4)
        v6 = tuple(s for s in dns.custom_servers if ipaddress.ip_address(s).version == 6)
        return DnsTarget(v4, v6, dns.custom_doh_template)
    p = catalogs.dns_provider(dns.provider)
    if p is None:
        return None
    template = (
        p.doh_template.replace("{id}", dns.provider_id or "") if p.needs_id else p.doh_template
    )
    return DnsTarget(tuple(p.ipv4), tuple(p.ipv6), template)


def problems(dns: Dns, catalogs: Catalogs) -> list[Msg]:
    """Erros de configuração do DNS na receita (validação)."""
    out: list[Msg] = []
    if dns.provider == "custom":
        if not dns.custom_servers:
            out.append(msg("recipe.dns_no_servers"))
        for s in dns.custom_servers:
            try:
                ipaddress.ip_address(s)
            except ValueError:
                out.append(msg("recipe.dns_bad_server", server=s))
        if dns.custom_doh_template and not dns.custom_doh_template.startswith("https://"):
            out.append(msg("recipe.dns_bad_template"))
    elif dns.provider != "unchanged":
        p = catalogs.dns_provider(dns.provider)
        if p is None:
            out.append(msg("recipe.dns_unknown_provider", id=dns.provider))
        elif p.needs_id and not (dns.provider_id or "").isalnum():
            out.append(msg("recipe.dns_needs_id", name=p.name))
    out += [
        msg("recipe.unknown_blocklist", id=b)
        for b in dns.hosts_blocklists
        if catalogs.blocklist(b) is None
    ]
    return out


def blocked_domains(dns: Dns, catalogs: Catalogs) -> list[str]:
    seen: dict[str, None] = {}
    for list_id in dns.hosts_blocklists:
        entry = catalogs.blocklist(list_id)
        if entry is not None:
            seen.update(dict.fromkeys(entry.domains))
    return sorted(seen)


# ------------------------------------------------------------------ hosts
def digest(domains: list[str]) -> str:
    return hashlib.sha256("\n".join(sorted(domains)).encode()).hexdigest()[:16]


@dataclass(frozen=True)
class HostsText:
    text: str
    encoding: str
    newline: str


def decode(data: bytes) -> HostsText:
    """UTF-8 (com ou sem BOM) ou, se não for, Latin-1 — ambos voltam aos mesmos bytes."""
    if data.startswith(codecs.BOM_UTF8):
        encoding = "utf-8-sig"
    else:
        try:
            data.decode("utf-8")
            encoding = "utf-8"
        except UnicodeDecodeError:
            encoding = "latin-1"
    text = data.decode(encoding)
    newline = "\r\n" if "\r\n" in text or not text else "\n"
    return HostsText(text, encoding, newline)


def _strip(text: str) -> tuple[str, bool]:
    lines = text.splitlines(keepends=True)
    start = next((i for i, x in enumerate(lines) if x.rstrip("\r\n").startswith(BEGIN)), None)
    if start is None:
        return text, False
    end = next((i for i in range(start, len(lines)) if lines[i].rstrip("\r\n") == END), None)
    if end is None:
        return text, False  # bloco quebrado: não mexe no que não reconhece
    return "".join(lines[:start] + lines[end + 1 :]), True


def without_block(data: bytes) -> tuple[bytes, bool]:
    h = decode(data)
    text, removed = _strip(h.text)
    return (text.encode(h.encoding) if removed else data), removed


def with_block(data: bytes, domains: list[str]) -> bytes:
    h = decode(data)
    text, _ = _strip(h.text)
    if text and not text.endswith(("\n", "\r")):
        text += h.newline
    nl = h.newline
    block = [
        f"{BEGIN} {digest(domains)}",
        "# Bloqueios do WinKit; para desfazer, apague este bloco.",
    ]
    block += [f"{SINKHOLE} {d}" for d in domains]
    block.append(END)
    return (text + nl.join(block) + nl).encode(h.encoding)


def has_block(data: bytes, domains: list[str]) -> bool:
    expected = f"{BEGIN} {digest(domains)}"
    return any(line == expected for line in decode(data).text.splitlines())

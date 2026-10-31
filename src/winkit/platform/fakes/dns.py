"""Dublê do cliente DNS: adaptadores e DoH em memória."""

from __future__ import annotations

from dataclasses import dataclass, field

from winkit.platform.dns import AdapterDns, DohState


@dataclass
class FakeDns:
    adapter_list: list[AdapterDns] = field(
        default_factory=lambda: [
            AdapterDns(4, "Wi-Fi", ("192.168.0.1",), ()),
            AdapterDns(7, "Ethernet", ("192.168.0.1",), ()),
        ]
    )
    doh_available: bool = True
    doh_servers: dict[str, str] = field(default_factory=dict)
    require_flags: dict[str, bool] = field(default_factory=dict)

    def adapters(self) -> list[AdapterDns]:
        return list(self.adapter_list)

    def set_servers(self, index: int, servers: list[str]) -> None:
        v4 = tuple(s for s in servers if ":" not in s)
        v6 = tuple(s for s in servers if ":" in s)
        self.adapter_list = [
            AdapterDns(a.index, a.name, v4, v6) if a.index == index else a
            for a in self.adapter_list
        ]

    def doh(self) -> DohState:
        return DohState(self.doh_available, dict(self.doh_servers))

    def set_doh(self, server: str, template: str, *, require: bool) -> None:
        if not self.doh_available:
            raise RuntimeError("sem DoH neste Windows")
        self.doh_servers[server] = template
        self.require_flags[server] = require

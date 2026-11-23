# src/rhosocial/activerecord/backend/impl/sqlite/adapters/network.py
"""MAC-address and IP-address adapters for SQLite (canonical TEXT).

Standard SQLite builds have no MAC or IP address type. A TEXT column carrying
the canonical form is portable, human-readable, and directly comparable, so
that is the storage shape these adapters use.
"""

from typing import Any, Dict, Optional, Type

from rhosocial.activerecord.backend.adapters.network import (
    IPAddress,
    IPAddressAdapterBase,
    MacAddress,
    MacAddressAdapterBase,
)


class SQLiteMacAddressAdapter(MacAddressAdapterBase):
    """Store neutral MAC addresses as their canonical ``aa:bb:...`` text."""

    def __init__(self):
        super().__init__()
        self.register_type(MacAddress, str)

    def _encode(self, mac: MacAddress, target_type: Type, options: Optional[Dict[str, Any]]) -> str:
        return str(mac)

    def _decode(self, value: Any, options: Optional[Dict[str, Any]]) -> MacAddress:
        return MacAddress.parse(self._require_text(value))


class SQLiteIPAddressAdapter(IPAddressAdapterBase):
    """Store neutral IP addresses as canonical text (``192.0.2.1`` / ``2001:db8::1``)."""

    def __init__(self):
        super().__init__()
        self.register_type(IPAddress, str)

    def _encode(
        self, ip_addr: IPAddress, target_type: Type, options: Optional[Dict[str, Any]]
    ) -> str:
        return str(ip_addr)

    def _decode(self, value: Any, options: Optional[Dict[str, Any]]) -> IPAddress:
        return IPAddress.parse(self._require_text(value))

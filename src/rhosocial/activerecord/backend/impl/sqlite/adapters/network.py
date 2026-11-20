# src/rhosocial/activerecord/backend/impl/sqlite/adapters/network.py
"""MAC-address adapter for SQLite (canonical TEXT).

Standard SQLite builds have no MAC-address type. A TEXT column carrying the
canonical lowercase colon-separated form is portable, human-readable, and
directly comparable, so that is the storage shape this adapter uses.
"""

from typing import Any, Dict, Optional, Type

from rhosocial.activerecord.backend.adapters.network import (
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

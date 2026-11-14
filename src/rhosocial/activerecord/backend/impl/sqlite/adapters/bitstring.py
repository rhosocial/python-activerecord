# src/rhosocial/activerecord/backend/impl/sqlite/adapters/bitstring.py
"""Bit-string adapter for SQLite (TEXT ``0``/``1`` digits).

SQLite has no bit-string type; a TEXT column holding only ``0``/``1`` digits is
the natural lossless carrier for arbitrary bit lengths (unlike BLOB, which
cannot express a partial-byte length).
"""

from typing import Any, Dict, Optional, Type

from rhosocial.activerecord.backend.adapters.bitstring import (
    BitString,
    BitStringAdapterBase,
)


class SQLiteBitStringAdapter(BitStringAdapterBase):
    """Store neutral bit strings as their ``to_bits()`` text."""

    def __init__(self):
        super().__init__()
        self.register_type(BitString, str)

    def _encode(self, bits: BitString, target_type: Type, options: Optional[Dict[str, Any]]) -> str:
        return bits.to_bits()

    def _decode(self, value: Any, options: Optional[Dict[str, Any]]) -> BitString:
        return BitString.from_bits(self._require_text(value))

# src/rhosocial/activerecord/backend/impl/sqlite/adapters/range.py
"""Range / Multirange adapter for SQLite (TEXT JSON).

SQLite has no native range type. This adapter stores the neutral type's
lossless JSON form (``Range.to_json_value`` / ``Multirange.to_json_value``)
in TEXT. The neutral JSON keeps ``element_type`` so values such as dates,
datetimes and decimals round-trip without guessing.
"""

import json
from typing import Any, Dict, Optional, Type

from rhosocial.activerecord.backend.adapters.range import (
    Multirange,
    Range,
    RangeAdapterBase,
)


class SQLiteRangeAdapter(RangeAdapterBase):
    """Store neutral ranges and multiranges as JSON text.

    A ``Multirange`` is a JSON array of range objects; a ``Range`` is a JSON
    object. Decoding follows the requested ``target_type`` when it names one of
    the neutral classes, and otherwise infers the shape from the JSON stream.
    """

    def __init__(self):
        super().__init__()
        self.register_type(Range, str)
        self.register_type(Multirange, str)

    def _encode(self, value: Any, target_type: Type, options: Optional[Dict[str, Any]]) -> str:
        return json.dumps(value.to_json_value(), allow_nan=False)

    def _decode(self, value: Any, target_type: Type, options: Optional[Dict[str, Any]]) -> Any:
        text = self._require_text(value)
        parsed = json.loads(text)

        if target_type is Multirange:
            return Multirange.from_json_value(parsed)
        if target_type is Range:
            return Range.from_json_value(parsed)
        if isinstance(parsed, list):
            return Multirange.from_json_value(parsed)
        if isinstance(parsed, dict):
            return Range.from_json_value(parsed)
        raise ValueError(
            "range JSON value must be an object or an array, " f"got {type(parsed).__name__}"
        )

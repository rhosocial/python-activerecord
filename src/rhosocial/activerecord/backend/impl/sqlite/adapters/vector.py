# src/rhosocial/activerecord/backend/impl/sqlite/adapters/vector.py
"""Dense-vector adapter for SQLite (TEXT JSON array).

SQLite is commonly used with embeddings via extension modules that accept a
JSON array in TEXT. This adapter binds the neutral :class:`Vector` canonical
JSON form and reconstructs it on read, including the JSON spellings of non-
finite components.
"""

import json
from typing import Any, Dict, Optional, Type

from rhosocial.activerecord.backend.adapters.vector import Vector, VectorAdapterBase


class SQLiteVectorAdapter(VectorAdapterBase):
    """Store neutral vectors as a JSON array in ``TEXT``."""

    def __init__(self):
        super().__init__()
        self.register_type(Vector, str)

    def _encode(self, vector: Vector, target_type: Type, options: Optional[Dict[str, Any]]) -> str:
        return json.dumps(vector.to_json_value(), allow_nan=False)

    def _decode(self, value: Any, options: Optional[Dict[str, Any]]) -> Vector:
        text = self._require_text(value)
        return Vector.from_json_value(json.loads(text))

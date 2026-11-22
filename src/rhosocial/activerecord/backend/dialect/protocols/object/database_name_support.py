# src/rhosocial/activerecord/backend/dialect/protocols/object/DatabaseNameSupport.py
"""Protocol mirroring DatabaseNameMixin (pure-format/object-naming feature group)."""

from typing import runtime_checkable, Protocol, Tuple

@runtime_checkable
class DatabaseNameSupport(Protocol):
    def format_database_object(self, expr: "Database") -> Tuple[str, tuple]:
        ...  # pragma: no cover

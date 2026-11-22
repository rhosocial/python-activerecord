# src/rhosocial/activerecord/backend/dialect/protocols/object/SchemaNameSupport.py
"""Protocol mirroring SchemaNameMixin (pure-format/object-naming feature group)."""

from typing import runtime_checkable, Protocol, Tuple

@runtime_checkable
class SchemaNameSupport(Protocol):
    def format_schema_object(self, expr: "Schema") -> Tuple[str, tuple]:
        ...  # pragma: no cover

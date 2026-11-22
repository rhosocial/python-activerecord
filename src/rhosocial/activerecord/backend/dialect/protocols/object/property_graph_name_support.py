# src/rhosocial/activerecord/backend/dialect/protocols/object/PropertyGraphNameSupport.py
"""Protocol mirroring PropertyGraphNameMixin (pure-format/object-naming feature group)."""

from typing import runtime_checkable, Protocol, Tuple

@runtime_checkable
class PropertyGraphNameSupport(Protocol):
    def format_property_graph_object(self, expr: "PropertyGraph") -> Tuple[str, tuple]:
        ...  # pragma: no cover

# src/rhosocial/activerecord/backend/dialect/protocols/query/TrimSupport.py
"""Protocol mirroring TrimMixin (pure-format/object-naming feature group)."""

from typing import runtime_checkable, Protocol, Tuple

@runtime_checkable
class TrimSupport(Protocol):
    def format_trim_expression(self, expr: "TrimExpression") -> Tuple[str, Tuple]:
        ...  # pragma: no cover

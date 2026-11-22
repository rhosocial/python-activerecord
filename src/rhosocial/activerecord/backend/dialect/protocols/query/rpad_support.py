# src/rhosocial/activerecord/backend/dialect/protocols/query/RpadSupport.py
"""Protocol mirroring RpadMixin (pure-format/object-naming feature group)."""

from typing import runtime_checkable, Protocol, Tuple

@runtime_checkable
class RpadSupport(Protocol):
    def format_rpad_expression(self, expr: "RpadFunction") -> Tuple[str, tuple]:
        ...  # pragma: no cover

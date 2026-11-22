# src/rhosocial/activerecord/backend/dialect/protocols/query/LpadSupport.py
"""Protocol mirroring LpadMixin (pure-format/object-naming feature group)."""

from typing import runtime_checkable, Protocol, Tuple

@runtime_checkable
class LpadSupport(Protocol):
    def format_lpad_expression(self, expr: "LpadFunction") -> Tuple[str, tuple]:
        ...  # pragma: no cover

# src/rhosocial/activerecord/backend/dialect/protocols/query/RepeatSupport.py
"""Protocol mirroring RepeatMixin (pure-format/object-naming feature group)."""

from typing import runtime_checkable, Protocol, Tuple

@runtime_checkable
class RepeatSupport(Protocol):
    def format_repeat_expression(self, expr: "RepeatFunction") -> Tuple[str, tuple]:
        ...  # pragma: no cover

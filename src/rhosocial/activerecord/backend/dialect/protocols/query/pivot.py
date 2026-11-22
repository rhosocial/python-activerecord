# src/rhosocial/activerecord/backend/dialect/protocols/query/pivot.py
"""PIVOT and UNPIVOT: reshaping a result set by a columns values.

SQL:1999 calls these ``<rotate>`` / ``<reverse rotate>``. Only some engines
have them, and they differ in how the aggregated columns are named, so both
are separate switches rather than one.
"""

from typing import Protocol, runtime_checkable, Tuple, Union

@runtime_checkable
class PivotSupport(Protocol):
    """PIVOT and UNPIVOT support."""

    def supports_pivot(self) -> bool:
        """Whether PIVOT is supported."""
        ...  # pragma: no cover

    def supports_unpivot(self) -> bool:
        """Whether UNPIVOT is supported."""
        ...  # pragma: no cover

    def format_pivot(self, expr: "Pivot") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_pivot_value(self, expr: "Union[BaseExpression, str, int, float]") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_unpivot(self, expr: "Unpivot") -> Tuple[str, tuple]:
        ...  # pragma: no cover

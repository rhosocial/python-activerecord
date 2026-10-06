# src/rhosocial/activerecord/backend/dialect/protocols/query/pivot.py
"""PIVOT and UNPIVOT: reshaping a result set by a columns values.

SQL:1999 calls these ``<rotate>`` / ``<reverse rotate>``. Only some engines
have them, and they differ in how the aggregated columns are named, so both
are separate switches rather than one.
"""

from typing import Protocol, runtime_checkable

@runtime_checkable
class PivotSupport(Protocol):
    """PIVOT and UNPIVOT support."""

    def supports_pivot(self) -> bool:
        """Whether PIVOT is supported."""
        ...  # pragma: no cover

    def supports_unpivot(self) -> bool:
        """Whether UNPIVOT is supported."""
        ...  # pragma: no cover

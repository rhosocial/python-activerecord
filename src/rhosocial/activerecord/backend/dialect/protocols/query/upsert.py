# src/rhosocial/activerecord/backend/dialect/protocols/query/upsert.py
"""UpsertSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`;
see that package for the full protocol surface and the rules the conformance
tests enforce.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ....expression import OnConflictClause


@runtime_checkable
class UpsertSupport(Protocol):
    """Protocol for UPSERT operation support."""

    def supports_upsert(self) -> bool:
        """Whether UPSERT is supported."""
        ...  # pragma: no cover

    def get_upsert_syntax_type(self) -> str:
        """
        Get UPSERT syntax type.

        Returns:
            'ON CONFLICT' (PostgreSQL) or 'ON DUPLICATE KEY' (MySQL)
        """
        ...  # pragma: no cover

    def supports_on_conflict_clause(self) -> bool:
        """
        Whether INSERT statements can carry an ON CONFLICT (or backend
        equivalent, e.g. ON DUPLICATE KEY) clause.

        Independent of ``supports_upsert()``: a dialect may support upsert
        via another mechanism (e.g. Oracle MERGE) while rejecting the
        ON CONFLICT clause form.
        """
        ...  # pragma: no cover

    def supports_multiple_on_conflict_clauses(self) -> bool:
        """
        Whether a single INSERT can carry more than one ON CONFLICT clause.

        Currently only SQLite (>= 3.35.0) supports this.
        """
        ...  # pragma: no cover

    def format_on_conflict_clause(self, expr: "OnConflictClause") -> Tuple[str, tuple]:
        """
        Format ON CONFLICT clause.

        Args:
            expr: OnConflictClause object

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted clause.
        """
        ...  # pragma: no cover

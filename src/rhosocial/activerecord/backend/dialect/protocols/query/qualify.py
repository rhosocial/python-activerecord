# src/rhosocial/activerecord/backend/dialect/protocols/query/qualify.py
"""QualifyClauseSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`;
see that package for the full protocol surface and the rules the conformance
tests enforce.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ....expression import QualifyClause


@runtime_checkable
class QualifyClauseSupport(Protocol):
    """Protocol for QUALIFY clause support."""

    def supports_qualify_clause(self) -> bool:
        """Whether QUALIFY clause is supported."""
        ...  # pragma: no cover

    def format_qualify_clause(self, clause: "QualifyClause") -> Tuple[str, tuple]:
        """
        Formats a QUALIFY clause.

        Args:
            clause: QualifyClause object

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted clause.
        """
        ...  # pragma: no cover

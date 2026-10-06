# src/rhosocial/activerecord/backend/dialect/protocols/query/returning.py
"""ReturningSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`;
see that package for the full protocol surface and the rules the conformance
tests enforce.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.statements import ReturningClause


@runtime_checkable
class ReturningSupport(Protocol):
    """Protocol for RETURNING clause support."""

    def supports_returning_insert(self) -> bool:
        """Whether RETURNING clause is supported for INSERT statements."""
        ...  # pragma: no cover

    def supports_returning_update(self) -> bool:
        """Whether RETURNING clause is supported for UPDATE statements."""
        ...  # pragma: no cover

    def supports_returning_delete(self) -> bool:
        """Whether RETURNING clause is supported for DELETE statements."""
        ...  # pragma: no cover

    def supports_returning_expressions(self) -> bool:
        """Whether non-column expressions are allowed in a RETURNING clause."""
        ...  # pragma: no cover

    def supports_returning_alias(self) -> bool:
        """Whether a clause-level alias is allowed on a RETURNING clause."""
        ...  # pragma: no cover

    def supports_returning_wildcard(self) -> bool:
        """Whether ``RETURNING *`` is allowed."""
        ...  # pragma: no cover

    def supports_returning_single_row(self) -> bool:
        """Whether RETURNING is inherently single-row."""
        ...  # pragma: no cover

    def supports_returning_old_new(self) -> bool:
        """Whether ``OLD.<col>`` / ``NEW.<col>`` references are allowed."""
        ...  # pragma: no cover

    def supports_returning_into(self) -> bool:
        """Whether ``RETURNING ... INTO`` / ``OUTPUT ... INTO`` is supported."""
        ...  # pragma: no cover

    def format_returning_clause(self, clause: "ReturningClause") -> Tuple[str, Tuple]:
        """Format a RETURNING clause.

        Args:
            clause: ReturningClause object containing expressions to return

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...  # pragma: no cover

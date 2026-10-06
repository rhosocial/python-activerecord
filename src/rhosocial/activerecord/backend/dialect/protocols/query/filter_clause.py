# src/rhosocial/activerecord/backend/dialect/protocols/query/filter_clause.py
"""FilterClauseSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`;
see that package for the full protocol surface and the rules the conformance
tests enforce.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.statements.filter_clause import FilterClauseExpression


@runtime_checkable
class FilterClauseSupport(Protocol):
    """Protocol for aggregate FILTER clause support."""

    def supports_filter_clause(self) -> bool:
        """Whether FILTER (WHERE ...) clause is supported in aggregate functions."""
        ...  # pragma: no cover

    def format_filter_clause(self, expr: "FilterClauseExpression") -> Tuple[str, tuple]:
        """
        Format a FILTER (WHERE ...) clause.

        Args:
            expr: FilterClauseExpression wrapping the condition.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted clause.
        """
        ...  # pragma: no cover

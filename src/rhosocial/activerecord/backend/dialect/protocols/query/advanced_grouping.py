# src/rhosocial/activerecord/backend/dialect/protocols/advancedgroupingsupport.py
"""AdvancedGroupingSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`;
see that package for the full protocol surface and the rules the conformance
tests enforce.
"""

from typing import Tuple, Protocol, runtime_checkable

from ....expression import bases

@runtime_checkable
class AdvancedGroupingSupport(Protocol):
    """Protocol for advanced grouping operations (ROLLUP, CUBE, GROUPING SETS)."""

    def supports_rollup(self) -> bool:
        """Whether ROLLUP is supported."""
        ...  # pragma: no cover

    def supports_cube(self) -> bool:
        """Whether CUBE is supported."""
        ...  # pragma: no cover

    def supports_grouping_sets(self) -> bool:
        """Whether GROUPING SETS are supported."""
        ...  # pragma: no cover

    def format_grouping_clause(
        self, expr: "bases.BaseExpression"
    ) -> Tuple[str, tuple]:
        """
        Formats a grouping expression (ROLLUP, CUBE, GROUPING SETS).

        Args:
            expr: The GroupingClause node (operation + grouped expressions).

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted expression.
        """
        ...  # pragma: no cover

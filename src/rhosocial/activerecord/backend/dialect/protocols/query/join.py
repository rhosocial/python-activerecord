# src/rhosocial/activerecord/backend/dialect/protocols/query/join.py
"""JoinSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`;
see that package for the full protocol surface and the rules the conformance
tests enforce.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ....expression import JoinClause


@runtime_checkable
class JoinSupport(Protocol):
    """Protocol for JOIN clause support."""

    def supports_explicit_inner_join(self) -> bool:
        """Whether the engine accepts the form ``explicit_inner_join``.

        Defaults to ``False``.
        """
        ...  # pragma: no cover

    def supports_straight_join(self) -> bool:
        """Whether the engine accepts the form ``straight_join``.

        Defaults to ``False``.
        """
        ...  # pragma: no cover

    def supports_inner_join(self) -> bool:
        """Whether INNER JOIN is supported."""
        ...  # pragma: no cover

    def supports_left_join(self) -> bool:
        """Whether LEFT JOIN and LEFT OUTER JOIN are supported."""
        ...  # pragma: no cover

    def supports_right_join(self) -> bool:
        """Whether RIGHT JOIN and RIGHT OUTER JOIN are supported."""
        ...  # pragma: no cover

    def supports_full_join(self) -> bool:
        """Whether FULL JOIN and FULL OUTER JOIN are supported."""
        ...  # pragma: no cover

    def supports_cross_join(self) -> bool:
        """Whether CROSS JOIN is supported."""
        ...  # pragma: no cover

    def supports_natural_join(self) -> bool:
        """Whether NATURAL JOIN is supported."""
        ...  # pragma: no cover

    def format_join_clause(self, join_expr: "JoinClause") -> Tuple[str, Tuple]:
        """
        Formats a JOIN expression.

        Args:
            join_expr: JoinClause object.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted expression.
        """
        ...  # pragma: no cover

# src/rhosocial/activerecord/backend/dialect/protocols/query/ilike.py
"""ILIKESupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`;
see that package for the full protocol surface and the rules the conformance
tests enforce.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ....expression import ILIKEExpression


@runtime_checkable
class ILIKESupport(Protocol):
    """
    Protocol for ILIKE (case-insensitive LIKE) support.

    ILIKE is a PostgreSQL extension for case-insensitive pattern matching.
    Support varies across databases:
    - PostgreSQL: Native ILIKE operator
    - MySQL: Uses LIKE with case-insensitive collation or LOWER() function
    - SQLite: No native ILIKE (requires LOWER() workaround)
    - Oracle: Uses UPPER() or LOWER() with LIKE
    """

    def supports_ilike(self) -> bool:
        """Whether ILIKE operator is supported."""
        ...  # pragma: no cover

    def format_ilike_expression(self, expr: "ILIKEExpression") -> Tuple[str, Tuple]:
        """
        Format ILIKE expression (case-insensitive pattern matching).

        Args:
            expr: The ILIKE expression node carrying column, pattern and
                negate state.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted expression.
        """
        ...  # pragma: no cover

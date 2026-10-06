# src/rhosocial/activerecord/backend/dialect/protocols/query/collation.py
"""CollationSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`;
see that package for the full protocol surface and the rules the conformance
tests enforce.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.collation import CollateExpression


@runtime_checkable
class CollationSupport(Protocol):
    """Protocol for expression-level COLLATE support."""

    def supports_collate_expression(self) -> bool:
        """Whether expression-level COLLATE is supported."""
        ...  # pragma: no cover

    def validate_collation_name(self, expr: "CollateExpression") -> str:
        """Validate a collation expression and return its SQL representation."""
        ...  # pragma: no cover

    def format_collate_expression(self, expr: "CollateExpression") -> Tuple[str, tuple]:
        """Format expression-level COLLATE."""
        ...  # pragma: no cover

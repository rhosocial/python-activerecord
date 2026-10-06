# src/rhosocial/activerecord/backend/dialect/protocols/query/array.py
"""ArraySupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`;
see that package for the full protocol surface and the rules the conformance
tests enforce.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.advanced_functions import ArrayExpression


@runtime_checkable
class ArraySupport(Protocol):
    """Protocol for array type support."""

    def supports_array_type(self) -> bool:
        """Whether array types are supported."""
        ...  # pragma: no cover

    def supports_array_constructor(self) -> bool:
        """Whether ARRAY constructor is supported."""
        ...  # pragma: no cover

    def supports_array_access(self) -> bool:
        """Whether array subscript access is supported."""
        ...  # pragma: no cover

    def format_array_expression(
        self,
        expr: "ArrayExpression",
    ) -> Tuple[str, Tuple]:
        """Format array expression.

        Args:
            expr: ArrayExpression node carrying all formatting state
                  (operation, elements, base_expr, index_expr).

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted expression.
        """
        ...  # pragma: no cover

# src/rhosocial/activerecord/backend/dialect/protocols/lateraljoinsupport.py
"""LateralJoinSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`;
see that package for the full protocol surface and the rules the conformance
tests enforce.
"""

from typing import Tuple, Protocol, runtime_checkable

from ....expression import bases

@runtime_checkable
class LateralJoinSupport(Protocol):
    """Protocol for LATERAL join support."""

    def supports_lateral_join(self) -> bool:
        """Whether LATERAL joins are supported."""
        ...  # pragma: no cover

    def format_lateral_expression(
        self, expr: "bases.BaseExpression"
    ) -> Tuple[str, Tuple]:
        """Format a LateralExpression node."""
        ...  # pragma: no cover

    def format_table_function_expression(
        self, expr: "bases.BaseExpression"
    ) -> Tuple[str, Tuple]:
        """Format table-valued function expression."""
        ...  # pragma: no cover

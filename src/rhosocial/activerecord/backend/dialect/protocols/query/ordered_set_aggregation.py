# src/rhosocial/activerecord/backend/dialect/protocols/query/ordered_set_aggregation.py
"""OrderedSetAggregationSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`;
see that package for the full protocol surface and the rules the conformance
tests enforce.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.advanced_functions import OrderedSetAggregation


@runtime_checkable
class OrderedSetAggregationSupport(Protocol):
    """Protocol for ordered-set aggregate function support (WITHIN GROUP (ORDER BY ...))."""

    def supports_ordered_set_aggregation(self) -> bool:
        """Whether ordered-set aggregate functions are supported."""
        ...  # pragma: no cover

    def format_ordered_set_aggregation(self, aggregation: "OrderedSetAggregation") -> Tuple[str, Tuple]:
        """
        Formats an ordered-set aggregate function call.

        Args:
            aggregation: OrderedSetAggregation object to format

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted expression.
        """
        ...  # pragma: no cover

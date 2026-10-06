# src/rhosocial/activerecord/backend/dialect/protocols/query/temporal.py
"""TemporalTableSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`;
see that package for the full protocol surface and the rules the conformance
tests enforce.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.datetime import TemporalOptionsExpression


@runtime_checkable
class TemporalTableSupport(Protocol):
    """Protocol for temporal table query support (FOR SYSTEM_TIME)."""

    def supports_temporal_tables(self) -> bool:
        """Whether temporal table queries are supported."""
        ...  # pragma: no cover

    def format_temporal_options(self, expr: "TemporalOptionsExpression") -> Tuple[str, tuple]:
        """
        Formats a temporal table clause (e.g., FOR SYSTEM_TIME AS OF ...).

        Args:
            expr: TemporalOptionsExpression carrying the temporal options dict.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted clause.
        """
        ...  # pragma: no cover

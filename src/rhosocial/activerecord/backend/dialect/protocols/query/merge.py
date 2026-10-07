# src/rhosocial/activerecord/backend/dialect/protocols/query/merge.py
"""MergeSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`;
see that package for the full protocol surface and the rules the conformance
tests enforce.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ....expression import MergeExpression


@runtime_checkable
class MergeSupport(Protocol):
    """Protocol for MERGE statement support."""

    def supports_merge_statement(self) -> bool:
        """Whether MERGE statement is supported."""
        ...  # pragma: no cover

    def format_merge_statement(self, expr: "MergeExpression") -> Tuple[str, tuple]:
        """
        Formats a complete MERGE statement from a MergeExpression object.

        Args:
            expr: MergeExpression object containing the merge specifications

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted statement.
        """
        ...  # pragma: no cover

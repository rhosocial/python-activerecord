# src/rhosocial/activerecord/backend/dialect/protocols/query/set_operation.py
"""SetOperationSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`;
see that package for the full protocol surface and the rules the conformance
tests enforce.
"""

from typing import Tuple, Protocol, runtime_checkable

from ....expression import bases

@runtime_checkable
class SetOperationSupport(Protocol):
    """Protocol for set operation (UNION, INTERSECT, EXCEPT) support."""

    def supports_union(self) -> bool:
        """Whether UNION operation is supported."""
        ...  # pragma: no cover

    def supports_union_all(self) -> bool:
        """Whether UNION ALL operation is supported."""
        ...  # pragma: no cover

    def supports_intersect(self) -> bool:
        """Whether INTERSECT operation is supported."""
        ...  # pragma: no cover

    def supports_except(self) -> bool:
        """Whether EXCEPT operation is supported."""
        ...  # pragma: no cover

    def format_set_operation(
        self, expr: "bases.BaseExpression"
    ) -> Tuple[str, Tuple]:
        """Format a SetOperation node (UNION, INTERSECT, EXCEPT)."""
        ...  # pragma: no cover

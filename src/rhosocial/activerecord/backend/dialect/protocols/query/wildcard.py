# src/rhosocial/activerecord/backend/dialect/protocols/wildcardsupport.py
"""WildcardSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`;
see that package for the full protocol surface and the rules the conformance
tests enforce.
"""

from typing import Tuple, Protocol, runtime_checkable

from ....expression import bases

@runtime_checkable
class WildcardSupport(Protocol):
    """Protocol for wildcard expression support (SELECT *)."""

    def format_wildcard(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        """Format a WildcardExpression node (* or table.* or schema.table.*)."""
        ...  # pragma: no cover

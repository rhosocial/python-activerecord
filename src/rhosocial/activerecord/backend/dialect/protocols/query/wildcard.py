# src/rhosocial/activerecord/backend/dialect/protocols/query/wildcard.py
"""WildcardSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`;
see that package for the full protocol surface and the rules the conformance
tests enforce.
"""

from typing import Tuple, Protocol, runtime_checkable

from ....expression import bases

@runtime_checkable
class WildcardSupport(Protocol):
    """Protocol for wildcard support in its two grammar positions.

    The asterisk is one lexical token in two contracts (spec 4.10): the
    select-list/RETURNING expansion and the aggregate row count. Each names
    its own formatter; a dialect spells one differently by overriding that
    one entry alone.
    """

    def format_all_columns_wildcard(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        """Format an AllColumnsWildcard node (* or rel.*)."""
        ...  # pragma: no cover

    def format_row_count_wildcard(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        """Format a RowCountWildcard node (the bare * of COUNT(*))."""
        ...  # pragma: no cover

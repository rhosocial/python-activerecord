# src/rhosocial/activerecord/backend/dialect/protocols/sqlxml/xml_aggregation.py
"""SQLXMLAggregationSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`;
see that package for the full protocol surface and the rules the conformance
tests enforce.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.xml import XMLAggExpression


@runtime_checkable
class SQLXMLAggregationSupport(Protocol):
    """Protocol for SQL/XML aggregation support."""

    def supports_xmlagg(self) -> bool:
        """Whether SQL/XML XMLAGG is supported."""
        ...  # pragma: no cover

    def format_xmlagg_expression(self, expr: "XMLAggExpression") -> Tuple[str, tuple]:
        """Format a SQL/XML XMLAGG expression."""
        ...  # pragma: no cover

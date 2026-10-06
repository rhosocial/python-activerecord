# src/rhosocial/activerecord/backend/dialect/protocols/sqlxml/xml_parsing.py
"""SQLXMLParsingSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`;
see that package for the full protocol surface and the rules the conformance
tests enforce.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.xml import XMLParseExpression


@runtime_checkable
class SQLXMLParsingSupport(Protocol):
    """Protocol for SQL/XML parsing support."""

    def supports_xmlparse(self) -> bool:
        """Whether SQL/XML XMLPARSE is supported."""
        ...  # pragma: no cover

    def format_xmlparse_expression(
        self,
        expr: "XMLParseExpression",
    ) -> Tuple[str, tuple]:
        """Format a SQL/XML XMLPARSE expression."""
        ...  # pragma: no cover

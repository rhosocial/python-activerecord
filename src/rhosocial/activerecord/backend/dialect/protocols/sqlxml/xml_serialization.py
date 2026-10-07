# src/rhosocial/activerecord/backend/dialect/protocols/sqlxml/xml_serialization.py
"""SQLXMLSerializationSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`;
see that package for the full protocol surface and the rules the conformance
tests enforce.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.xml import XMLSerializeExpression


@runtime_checkable
class SQLXMLSerializationSupport(Protocol):
    """Protocol for SQL/XML serialization support."""

    def supports_xmlserialize(self) -> bool:
        """Whether SQL/XML XMLSERIALIZE is supported."""
        ...  # pragma: no cover

    def format_xmlserialize_expression(
        self,
        expr: "XMLSerializeExpression",
    ) -> Tuple[str, tuple]:
        """Format a SQL/XML XMLSERIALIZE expression."""
        ...  # pragma: no cover

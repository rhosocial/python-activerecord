# src/rhosocial/activerecord/backend/dialect/protocols/sqlxmlconstructionsupport.py
"""SQLXMLConstructionSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`;
see that package for the full protocol surface and the rules the conformance
tests enforce.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.xml import (
        XMLAttributesExpression,
        XMLCommentExpression,
        XMLConcatExpression,
        XMLElementExpression,
        XMLForestExpression,
        XMLPIExpression,
        XMLRootExpression,
    )


@runtime_checkable
class SQLXMLConstructionSupport(Protocol):
    """Protocol for SQL/XML construction support."""

    def supports_xmlelement(self) -> bool:
        """Whether SQL/XML XMLELEMENT is supported."""
        ...  # pragma: no cover

    def supports_xmlattributes(self) -> bool:
        """Whether SQL/XML XMLATTRIBUTES is supported."""
        ...  # pragma: no cover

    def supports_xmlforest(self) -> bool:
        """Whether SQL/XML XMLFOREST is supported."""
        ...  # pragma: no cover

    def supports_xmlconcat(self) -> bool:
        """Whether SQL/XML XMLCONCAT is supported."""
        ...  # pragma: no cover

    def supports_xmlcomment(self) -> bool:
        """Whether SQL/XML XMLCOMMENT is supported."""
        ...  # pragma: no cover

    def supports_xmlpi(self) -> bool:
        """Whether SQL/XML XMLPI is supported."""
        ...  # pragma: no cover

    def supports_xmlroot(self) -> bool:
        """Whether SQL/XML XMLROOT is supported."""
        ...  # pragma: no cover

    def format_xmlattributes_expression(self, expr: "XMLAttributesExpression") -> Tuple[str, tuple]:
        """Format a SQL/XML XMLATTRIBUTES clause."""
        ...  # pragma: no cover

    def format_xmlelement_expression(self, expr: "XMLElementExpression") -> Tuple[str, tuple]:
        """Format a SQL/XML XMLELEMENT expression."""
        ...  # pragma: no cover

    def format_xmlforest_expression(self, expr: "XMLForestExpression") -> Tuple[str, tuple]:
        """Format a SQL/XML XMLFOREST expression."""
        ...  # pragma: no cover

    def format_xmlconcat_expression(self, expr: "XMLConcatExpression") -> Tuple[str, tuple]:
        """Format a SQL/XML XMLCONCAT expression."""
        ...  # pragma: no cover

    def format_xmlcomment_expression(self, expr: "XMLCommentExpression") -> Tuple[str, tuple]:
        """Format a SQL/XML XMLCOMMENT expression."""
        ...  # pragma: no cover

    def format_xmlpi_expression(self, expr: "XMLPIExpression") -> Tuple[str, tuple]:
        """Format a SQL/XML XMLPI expression."""
        ...  # pragma: no cover

    def format_xmlroot_expression(self, expr: "XMLRootExpression") -> Tuple[str, tuple]:
        """Format a SQL/XML XMLROOT expression."""
        ...  # pragma: no cover

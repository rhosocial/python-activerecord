# src/rhosocial/activerecord/backend/expression/functions/xml.py
"""SQL/XML expression factory functions."""

from typing import TYPE_CHECKING, Union

from ..bases import BaseExpression
from ..core import Literal
from ..xml import XMLParseDocumentType, XMLParseExpression, XMLWhitespaceOption

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


def xmlparse(
    dialect: "SQLDialectBase",
    content: Union[str, BaseExpression],
    document: bool = True,
    preserve_whitespace: bool = False,
) -> XMLParseExpression:
    """Create a SQL/XML XMLPARSE expression."""
    content_expr = (
        content
        if isinstance(content, BaseExpression)
        else Literal(dialect, content)
    )
    document_type = (
        XMLParseDocumentType.DOCUMENT
        if document
        else XMLParseDocumentType.CONTENT
    )
    whitespace_option = (
        XMLWhitespaceOption.PRESERVE
        if preserve_whitespace
        else None
    )
    return XMLParseExpression(
        dialect,
        content_expr,
        document_type,
        whitespace_option,
    )

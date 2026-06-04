# src/rhosocial/activerecord/backend/expression/xml.py
"""SQL/XML expression constructors."""

from enum import Enum
from typing import Optional, TYPE_CHECKING

from .bases import BaseExpression, SQLQueryAndParams, SQLValueExpression

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import SQLDialectBase


class XMLParseDocumentType(str, Enum):
    """SQL/XML XMLPARSE document type keywords."""

    DOCUMENT = "DOCUMENT"
    CONTENT = "CONTENT"


class XMLWhitespaceOption(str, Enum):
    """SQL/XML XMLPARSE whitespace handling keywords."""

    PRESERVE = "PRESERVE WHITESPACE"
    STRIP = "STRIP WHITESPACE"


class XMLParseExpression(SQLValueExpression):
    """Represents a SQL/XML XMLPARSE expression constructor."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        content: BaseExpression,
        document_type: XMLParseDocumentType = XMLParseDocumentType.DOCUMENT,
        whitespace_option: Optional[XMLWhitespaceOption] = None,
    ):
        super().__init__(dialect)
        self.content = content
        self.document_type = document_type
        self.whitespace_option = whitespace_option

    def to_sql(self) -> SQLQueryAndParams:
        return self.dialect.format_xmlparse_expression(self)

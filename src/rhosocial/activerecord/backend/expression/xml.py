# src/rhosocial/activerecord/backend/expression/xml.py
"""SQL/XML expression constructors."""

from enum import Enum
from typing import Optional, Sequence, TYPE_CHECKING

from .bases import BaseExpression, SQLPredicate, SQLQueryAndParams, SQLValueExpression

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import SQLDialectBase
    from .query_parts import OrderByClause


class XMLParseDocumentType(str, Enum):
    """SQL/XML XMLPARSE document type keywords."""

    DOCUMENT = "DOCUMENT"
    CONTENT = "CONTENT"


class XMLWhitespaceOption(str, Enum):
    """SQL/XML whitespace handling keywords."""

    PRESERVE = "PRESERVE WHITESPACE"
    STRIP = "STRIP WHITESPACE"


class XMLSerializeDocumentType(str, Enum):
    """SQL/XML XMLSERIALIZE document type keywords."""

    DOCUMENT = "DOCUMENT"
    CONTENT = "CONTENT"


class XMLStandaloneOption(str, Enum):
    """SQL/XML XMLROOT standalone option keywords."""

    YES = "YES"
    NO = "NO"
    NO_VALUE = "NO VALUE"


class XMLPassingMechanism(str, Enum):
    """SQL/XML XMLQUERY/XMLEXISTS passing mechanism keywords."""

    BY_REF = "BY REF"
    BY_VALUE = "BY VALUE"


class XMLEmptyHandlingOption(str, Enum):
    """SQL/XML XMLQUERY empty sequence handling keywords."""

    NULL_ON_EMPTY = "NULL ON EMPTY"
    EMPTY_ON_EMPTY = "EMPTY ON EMPTY"


class XMLTableColumnOption(str, Enum):
    """SQL/XML XMLTABLE column option keywords."""

    PATH = "PATH"
    DEFAULT = "DEFAULT"


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

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_xmlparse_expression"


class XMLSerializeExpression(SQLValueExpression):
    """Represents a SQL/XML XMLSERIALIZE expression constructor."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        content: BaseExpression,
        target_type: str,
        document_type: XMLSerializeDocumentType = XMLSerializeDocumentType.CONTENT,
        whitespace_option: Optional[XMLWhitespaceOption] = None,
    ):
        super().__init__(dialect)
        self.content = content
        self.target_type = target_type
        self.document_type = document_type
        self.whitespace_option = whitespace_option

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_xmlserialize_expression"


class XMLAttribute:
    """Represents one XMLATTRIBUTES item."""

    def __init__(self, value: BaseExpression, name: Optional[str] = None):
        self.value = value
        self.name = name


class XMLAttributesExpression(SQLValueExpression):
    """Represents a SQL/XML XMLATTRIBUTES clause."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        attributes: Sequence[XMLAttribute],
    ):
        super().__init__(dialect)
        self.attributes = list(attributes)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_xmlattributes_expression"


class XMLElementExpression(SQLValueExpression):
    """Represents a SQL/XML XMLELEMENT expression constructor."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        name: str,
        content: Optional[Sequence[BaseExpression]] = None,
        attributes: Optional[XMLAttributesExpression] = None,
    ):
        super().__init__(dialect)
        self.name = name
        self.content = list(content or [])
        self.attributes = attributes

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_xmlelement_expression"


class XMLForestItem:
    """Represents one XMLFOREST item."""

    def __init__(self, value: BaseExpression, name: Optional[str] = None):
        self.value = value
        self.name = name


class XMLForestExpression(SQLValueExpression):
    """Represents a SQL/XML XMLFOREST expression constructor."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        items: Sequence[XMLForestItem],
    ):
        super().__init__(dialect)
        self.items = list(items)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_xmlforest_expression"


class XMLConcatExpression(SQLValueExpression):
    """Represents a SQL/XML XMLCONCAT expression constructor."""

    def __init__(self, dialect: "SQLDialectBase", parts: Sequence[BaseExpression]):
        super().__init__(dialect)
        self.parts = list(parts)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_xmlconcat_expression"


class XMLCommentExpression(SQLValueExpression):
    """Represents a SQL/XML XMLCOMMENT expression constructor."""

    def __init__(self, dialect: "SQLDialectBase", content: BaseExpression):
        super().__init__(dialect)
        self.content = content

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_xmlcomment_expression"


class XMLPIExpression(SQLValueExpression):
    """Represents a SQL/XML XMLPI expression constructor."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        target: str,
        content: Optional[BaseExpression] = None,
    ):
        super().__init__(dialect)
        self.target = target
        self.content = content

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_xmlpi_expression"


class XMLRootExpression(SQLValueExpression):
    """Represents a SQL/XML XMLROOT expression constructor."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        content: BaseExpression,
        version: Optional[BaseExpression] = None,
        standalone: Optional[XMLStandaloneOption] = None,
    ):
        super().__init__(dialect)
        self.content = content
        self.version = version
        self.standalone = standalone

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_xmlroot_expression"


class XMLAggExpression(SQLValueExpression):
    """Represents a SQL/XML XMLAGG aggregate expression."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        expression: BaseExpression,
        order_by: Optional["OrderByClause"] = None,
    ):
        super().__init__(dialect)
        self.expression = expression
        self.order_by = order_by

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_xmlagg_expression"


class XMLQueryExpression(SQLValueExpression):
    """Represents a SQL/XML XMLQUERY expression."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        query: BaseExpression,
        passing: Optional[Sequence[BaseExpression]] = None,
        passing_mechanism: Optional[XMLPassingMechanism] = None,
        returning_content: bool = True,
        empty_handling: Optional[XMLEmptyHandlingOption] = None,
    ):
        super().__init__(dialect)
        self.query = query
        self.passing = list(passing or [])
        self.passing_mechanism = passing_mechanism
        self.returning_content = returning_content
        self.empty_handling = empty_handling

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_xmlquery_expression"


class XMLExistsExpression(SQLPredicate):
    """Represents a SQL/XML XMLEXISTS predicate."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        query: BaseExpression,
        passing: Optional[Sequence[BaseExpression]] = None,
        passing_mechanism: Optional[XMLPassingMechanism] = None,
    ):
        super().__init__(dialect)
        self.query = query
        self.passing = list(passing or [])
        self.passing_mechanism = passing_mechanism

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_xmlexists_expression"


class XMLTableColumn:
    """Represents one SQL/XML XMLTABLE column definition."""

    def __init__(
        self,
        name: str,
        data_type: str,
        path: Optional[BaseExpression] = None,
        default: Optional[BaseExpression] = None,
    ):
        self.name = name
        self.data_type = data_type
        self.path = path
        self.default = default


class XMLTableExpression(BaseExpression):
    """Represents a SQL/XML XMLTABLE table expression."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        row_pattern: BaseExpression,
        columns: Sequence[XMLTableColumn],
        passing: Optional[Sequence[BaseExpression]] = None,
        passing_mechanism: Optional[XMLPassingMechanism] = None,
    ):
        super().__init__(dialect)
        self.row_pattern = row_pattern
        self.columns = list(columns)
        self.passing = list(passing or [])
        self.passing_mechanism = passing_mechanism

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_xmltable_expression"

# src/rhosocial/activerecord/backend/expression/xml.py
"""SQL/XML expression constructors."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Sequence, TYPE_CHECKING

from .advanced_functions import DeclaredValueType
from .bases import BaseExpression, SQLPredicate, SQLValue

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import SQLDialectBase
    from .query_parts import OrderByClause


from .surfaces import (
    TextSurface,
    XMLSurface,
)

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


class XMLParseExpression(
    DeclaredValueType,
    XMLSurface,
    SQLValue,
):
    """Represents a SQL/XML XMLPARSE expression constructor.

    The parse of a document *is* an XML value, so it declares
    :class:`~...expression.surfaces.XMLSurface` (see
    :class:`~...expression.advanced_functions.DeclaredValueType` for why these
    nodes inherit the value class rather than being wrapped by one).
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        content: BaseExpression,
        document_type: XMLParseDocumentType = XMLParseDocumentType.DOCUMENT,
        whitespace_option: Optional[XMLWhitespaceOption] = None,
    ):
        BaseExpression.__init__(self, dialect)
        self.content = content
        self.document_type = document_type
        self.whitespace_option = whitespace_option

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_xmlparse_expression"


class XMLSerializeExpression(
    DeclaredValueType,
    TextSurface,
    SQLValue,
):
    """Represents a SQL/XML XMLSERIALIZE expression constructor.

    Serialization leaves the XML family: what comes back is the character
    value named in ``target_type``, so the node declares
    :class:`~...expression.surfaces.TextSurface` and carries the string
    operations rather than the XML surface.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        content: BaseExpression,
        target_type: str,
        document_type: XMLSerializeDocumentType = XMLSerializeDocumentType.CONTENT,
        whitespace_option: Optional[XMLWhitespaceOption] = None,
    ):
        BaseExpression.__init__(self, dialect)
        self.content = content
        self.target_type = target_type
        self.document_type = document_type
        self.whitespace_option = whitespace_option

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_xmlserialize_expression"


@dataclass
class XMLAttribute:
    """One XMLATTRIBUTES item: a value, optionally given a name.

    A dataclass because the expression serializer encodes dataclasses
    structurally. As a plain class this serialised to ``null`` in JSON and to a
    ``repr`` in XML, so an XMLATTRIBUTES clause lost its content on every
    round-trip.
    """

    value: BaseExpression
    name: Optional[str] = None


class XMLAttributesExpression(SQLValue):
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


class XMLElementExpression(
    DeclaredValueType,
    XMLSurface,
    SQLValue,
):
    """Represents a SQL/XML XMLELEMENT expression constructor."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        name: str,
        content: Optional[Sequence[BaseExpression]] = None,
        attributes: Optional[XMLAttributesExpression] = None,
    ):
        BaseExpression.__init__(self, dialect)
        self.name = name
        self.content = list(content or [])
        self.attributes = attributes

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_xmlelement_expression"


@dataclass
class XMLForestItem:
    """One XMLFOREST item: a value, optionally given a name.

    A dataclass for the reason given on :class:`XMLAttribute`.
    """

    value: BaseExpression
    name: Optional[str] = None


class XMLForestExpression(
    DeclaredValueType,
    XMLSurface,
    SQLValue,
):
    """Represents a SQL/XML XMLFOREST expression constructor."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        items: Sequence[XMLForestItem],
    ):
        BaseExpression.__init__(self, dialect)
        self.items = list(items)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_xmlforest_expression"


class XMLConcatExpression(
    DeclaredValueType,
    XMLSurface,
    SQLValue,
):
    """Represents a SQL/XML XMLCONCAT expression constructor."""

    def __init__(self, dialect: "SQLDialectBase", parts: Sequence[BaseExpression]):
        BaseExpression.__init__(self, dialect)
        self.parts = list(parts)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_xmlconcat_expression"


class XMLCommentExpression(
    DeclaredValueType,
    XMLSurface,
    SQLValue,
):
    """Represents a SQL/XML XMLCOMMENT expression constructor."""

    def __init__(self, dialect: "SQLDialectBase", content: BaseExpression):
        BaseExpression.__init__(self, dialect)
        self.content = content

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_xmlcomment_expression"


class XMLPIExpression(
    DeclaredValueType,
    XMLSurface,
    SQLValue,
):
    """Represents a SQL/XML XMLPI expression constructor."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        target: str,
        content: Optional[BaseExpression] = None,
    ):
        BaseExpression.__init__(self, dialect)
        self.target = target
        self.content = content

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_xmlpi_expression"


class XMLRootExpression(
    DeclaredValueType,
    XMLSurface,
    SQLValue,
):
    """Represents a SQL/XML XMLROOT expression constructor."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        content: BaseExpression,
        version: Optional[BaseExpression] = None,
        standalone: Optional[XMLStandaloneOption] = None,
    ):
        BaseExpression.__init__(self, dialect)
        self.content = content
        self.version = version
        self.standalone = standalone

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_xmlroot_expression"


class XMLAggExpression(
    DeclaredValueType,
    XMLSurface,
    SQLValue,
):
    """Represents a SQL/XML XMLAGG aggregate expression."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        expression: BaseExpression,
        order_by: Optional["OrderByClause"] = None,
    ):
        BaseExpression.__init__(self, dialect)
        self.expression = expression
        self.order_by = order_by

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_xmlagg_expression"


class PassingClause(BaseExpression):
    """The SQL/XML ``PASSING`` clause: the values passed into an XML function.

    ``PASSING [BY {VALUE | REF}]expr [, expr]...`` is a named production
    the three querying XML expressions (XMLQUERY, XMLEXISTS, XMLTABLE)
    all carry, so it is a clause node of its own with the dialect's
    public ``format_passing_clause`` as its formatter — instead of the
    unpacked pieces every XML formatter used to pass to a private helper,
    which gave the shared state no home and gave backends nothing to
    override. Carrying no expressions renders as ``("", ())``.

    Renders as, for example: ``PASSING BY VALUE 'x', y``.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_passing_clause"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        expressions: Sequence["BaseExpression"] = (),
        mechanism: Optional[XMLPassingMechanism] = None,
    ):
        super().__init__(dialect)
        self.expressions = list(expressions)
        self.mechanism = mechanism


class XMLQueryExpression(
    DeclaredValueType,
    XMLSurface,
    SQLValue,
):
    """Represents a SQL/XML XMLQUERY expression."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        query: BaseExpression,
        passing_clause: Optional[PassingClause] = None,
        returning_content: bool = True,
        empty_handling: Optional[XMLEmptyHandlingOption] = None,
    ):
        BaseExpression.__init__(self, dialect)
        self.query = query
        self.passing_clause = passing_clause
        self.returning_content = returning_content
        self.empty_handling = empty_handling

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_xmlquery_expression"


class XMLExistsPredicate(SQLPredicate):
    """Represents a SQL/XML XMLEXISTS predicate."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        query: BaseExpression,
        passing_clause: Optional[PassingClause] = None,
    ):
        super().__init__(dialect)
        self.query = query
        self.passing_clause = passing_clause

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_xmlexists_predicate"


@dataclass
class XMLTableColumn:
    """One SQL/XML XMLTABLE column definition.

    A dataclass for the reason given on :class:`XMLAttribute`: the serialiser
    encodes dataclasses structurally, so as a plain class this definition was
    written out as ``null`` by the JSON and XML encoders and an XMLTABLE lost its
    column list on every round-trip.
    """

    name: str
    data_type: str
    path: Optional[BaseExpression] = None
    default: Optional[BaseExpression] = None


class XMLTableExpression(BaseExpression):
    """Represents a SQL/XML XMLTABLE table expression."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        row_pattern: BaseExpression,
        columns: Sequence[XMLTableColumn],
        passing_clause: Optional[PassingClause] = None,
    ):
        super().__init__(dialect)
        self.row_pattern = row_pattern
        self.columns = list(columns)
        self.passing_clause = passing_clause

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_xmltable_expression"

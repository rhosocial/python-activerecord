# src/rhosocial/activerecord/backend/expression/functions/xml.py
"""SQL/XML expression constructors."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Sequence, TYPE_CHECKING, Tuple, Union

from ..functions.advanced_functions import DeclaredValueType
from ..bases.bases import BaseExpression, SQLPredicate, SQLValue
from ..query_parts.query_parts import OrderByClause
from ..value_types.parameter import Parameter

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase
    from ..query_parts.query_parts import OrderByClause
    from ..types import DataType


from ..value_types.value_types import (
    TextValue,
    XMLValue,
)

class XMLParseDocumentType(str, Enum):
    """SQL/XML XMLPARSE document type keywords."""

    #: A member *is* the word it carries; see ``SortDirection.__str__``.
    __str__ = str.__str__

    DOCUMENT = "DOCUMENT"
    CONTENT = "CONTENT"


class XMLWhitespaceOption(str, Enum):
    """SQL/XML whitespace handling keywords."""

    #: A member *is* the word it carries; see ``SortDirection.__str__``.
    __str__ = str.__str__

    PRESERVE = "PRESERVE WHITESPACE"
    STRIP = "STRIP WHITESPACE"


class XMLSerializeDocumentType(str, Enum):
    """SQL/XML XMLSERIALIZE document type keywords."""

    #: A member *is* the word it carries; see ``SortDirection.__str__``.
    __str__ = str.__str__

    DOCUMENT = "DOCUMENT"
    CONTENT = "CONTENT"


class XMLStandaloneOption(str, Enum):
    """SQL/XML XMLROOT standalone option keywords."""

    #: A member *is* the word it carries; see ``SortDirection.__str__``.
    __str__ = str.__str__

    YES = "YES"
    NO = "NO"
    NO_VALUE = "NO VALUE"


class XMLPassingMechanism(str, Enum):
    """SQL/XML XMLQUERY/XMLEXISTS passing mechanism keywords."""

    #: A member *is* the word it carries; see ``SortDirection.__str__``.
    __str__ = str.__str__

    BY_REF = "BY REF"
    BY_VALUE = "BY VALUE"


class XMLEmptyHandlingOption(str, Enum):
    """SQL/XML XMLQUERY empty sequence handling keywords."""

    #: A member *is* the word it carries; see ``SortDirection.__str__``.
    __str__ = str.__str__

    NULL_ON_EMPTY = "NULL ON EMPTY"
    EMPTY_ON_EMPTY = "EMPTY ON EMPTY"


class XMLTableColumnOption(str, Enum):
    """SQL/XML XMLTABLE column option keywords."""

    #: A member *is* the word it carries; see ``SortDirection.__str__``.
    __str__ = str.__str__

    PATH = "PATH"
    DEFAULT = "DEFAULT"


class XMLParseExpression(
    DeclaredValueType,
    XMLValue,
    SQLValue,
):
    """Represents a SQL/XML XMLPARSE expression constructor.

    The parse of a document *is* an XML value, so it declares
    :class:`~...expression.value_types.value_types.XMLValue` (see
    :class:`~...expression.functions.advanced_functions.DeclaredValueType` for why these
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
        return "format_xml_parse_expression"


class XMLSerializeExpression(
    DeclaredValueType,
    TextValue,
    SQLValue,
):
    """Represents a SQL/XML XMLSERIALIZE expression constructor.

    Serialization leaves the XML family: what comes back is the character
    value named in ``target_type``, so the node declares
    :class:`~...expression.value_types.value_types.TextValue` and carries the string
    operations rather than the XML surface.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        content: BaseExpression,
        target_type: "Union[str, DataType]",
        document_type: XMLSerializeDocumentType = XMLSerializeDocumentType.CONTENT,
        whitespace_option: Optional[XMLWhitespaceOption] = None,
    ):
        from ..types import DataType

        BaseExpression.__init__(self, dialect)
        self.content = content
        self.target_type = DataType.as_type(dialect, target_type)
        self.document_type = document_type
        self.whitespace_option = whitespace_option

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_xml_serialize_expression"


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
        return "format_xml_attributes_expression"


class XMLElementExpression(
    DeclaredValueType,
    XMLValue,
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
        return "format_xml_element_expression"


@dataclass
class XMLForestItem:
    """One XMLFOREST item: a value, optionally given a name.

    A dataclass for the reason given on :class:`XMLAttribute`.
    """

    value: BaseExpression
    name: Optional[str] = None


class XMLForestExpression(
    DeclaredValueType,
    XMLValue,
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
        return "format_xml_forest_expression"


class XMLConcatExpression(
    DeclaredValueType,
    XMLValue,
    SQLValue,
):
    """Represents a SQL/XML XMLCONCAT expression constructor."""

    def __init__(self, dialect: "SQLDialectBase", parts: Sequence[BaseExpression]):
        BaseExpression.__init__(self, dialect)
        self.parts = list(parts)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_xml_concat_expression"


class XMLCommentExpression(
    DeclaredValueType,
    XMLValue,
    SQLValue,
):
    """Represents a SQL/XML XMLCOMMENT expression constructor."""

    def __init__(self, dialect: "SQLDialectBase", content: BaseExpression):
        BaseExpression.__init__(self, dialect)
        self.content = content

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_xml_comment_expression"


class XMLPIExpression(
    DeclaredValueType,
    XMLValue,
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
    XMLValue,
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
        return "format_xml_root_expression"


class XMLAggExpression(
    DeclaredValueType,
    XMLValue,
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
        return "format_xml_agg_expression"


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
    XMLValue,
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
        return "format_xml_query_expression"


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
    data_type: "Union[str, DataType]"
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
        return "format_xml_table_expression"

XMLValue = Union[str, BaseExpression]
XMLNamedValue = Tuple[XMLValue, Optional[str]]


def _as_expression(dialect: "SQLDialectBase", value: XMLValue) -> BaseExpression:
    return value if isinstance(value, BaseExpression) else Parameter(dialect, value)


def xmlparse(
    dialect: "SQLDialectBase",
    content: XMLValue,
    document: bool = True,
    preserve_whitespace: bool = False,
) -> XMLParseExpression:
    """Create a SQL/XML XMLPARSE expression."""
    document_type = XMLParseDocumentType.DOCUMENT if document else XMLParseDocumentType.CONTENT
    whitespace_option = XMLWhitespaceOption.PRESERVE if preserve_whitespace else None
    return XMLParseExpression(
        dialect,
        _as_expression(dialect, content),
        document_type,
        whitespace_option,
    )


def xmlserialize(
    dialect: "SQLDialectBase",
    content: XMLValue,
    target_type: "DataType",
    document: bool = False,
    preserve_whitespace: bool = False,
) -> XMLSerializeExpression:
    """Create a SQL/XML XMLSERIALIZE expression.

    Args:
        dialect: The dialect the expression belongs to.
        content: The XML value to serialize.
        target_type: The character type the result is cast to. A type
            position holds a type: ``TextType(dialect)`` for a built-in, or
            ``CustomType(dialect, "name")`` for a name this package does not
            model.
        document: Whether the result is a document rather than content.
        preserve_whitespace: Whether whitespace is preserved.

    Returns:
        The XMLSERIALIZE expression.
    """
    document_type = XMLSerializeDocumentType.DOCUMENT if document else XMLSerializeDocumentType.CONTENT
    whitespace_option = XMLWhitespaceOption.PRESERVE if preserve_whitespace else None
    return XMLSerializeExpression(
        dialect,
        _as_expression(dialect, content),
        target_type,
        document_type,
        whitespace_option,
    )


def xmlattributes(
    dialect: "SQLDialectBase",
    *attributes: Union[XMLNamedValue, XMLValue],
) -> XMLAttributesExpression:
    """Create a SQL/XML XMLATTRIBUTES clause expression."""
    items = []
    for attribute in attributes:
        if isinstance(attribute, tuple):
            value, name = attribute
        else:
            value, name = attribute, None
        items.append(XMLAttribute(_as_expression(dialect, value), name))
    return XMLAttributesExpression(dialect, items)


def xmlelement(
    dialect: "SQLDialectBase",
    name: str,
    *content: XMLValue,
    attributes: Optional[XMLAttributesExpression] = None,
) -> XMLElementExpression:
    """Create a SQL/XML XMLELEMENT expression."""
    return XMLElementExpression(
        dialect,
        name,
        [_as_expression(dialect, item) for item in content],
        attributes,
    )


def xmlforest(
    dialect: "SQLDialectBase",
    *items: Union[XMLNamedValue, XMLValue],
) -> XMLForestExpression:
    """Create a SQL/XML XMLFOREST expression."""
    forest_items = []
    for item in items:
        if isinstance(item, tuple):
            value, name = item
        else:
            value, name = item, None
        forest_items.append(XMLForestItem(_as_expression(dialect, value), name))
    return XMLForestExpression(dialect, forest_items)


def xmlconcat(dialect: "SQLDialectBase", *parts: XMLValue) -> XMLConcatExpression:
    """Create a SQL/XML XMLCONCAT expression."""
    return XMLConcatExpression(dialect, [_as_expression(dialect, part) for part in parts])


def xmlcomment(dialect: "SQLDialectBase", content: XMLValue) -> XMLCommentExpression:
    """Create a SQL/XML XMLCOMMENT expression."""
    return XMLCommentExpression(dialect, _as_expression(dialect, content))


def xmlpi(
    dialect: "SQLDialectBase",
    target: str,
    content: Optional[XMLValue] = None,
) -> XMLPIExpression:
    """Create a SQL/XML XMLPI expression."""
    return XMLPIExpression(
        dialect,
        target,
        _as_expression(dialect, content) if content is not None else None,
    )


def xmlroot(
    dialect: "SQLDialectBase",
    content: XMLValue,
    version: Optional[XMLValue] = None,
    standalone: Optional[XMLStandaloneOption] = None,
) -> XMLRootExpression:
    """Create a SQL/XML XMLROOT expression."""
    return XMLRootExpression(
        dialect,
        _as_expression(dialect, content),
        _as_expression(dialect, version) if version is not None else None,
        standalone,
    )


def xmlagg(
    dialect: "SQLDialectBase",
    expression: XMLValue,
    order_by: Optional[OrderByClause] = None,
) -> XMLAggExpression:
    """Create a SQL/XML XMLAGG aggregate expression."""
    return XMLAggExpression(dialect, _as_expression(dialect, expression), order_by)


def passing_clause(
    dialect: "SQLDialectBase",
    passing: Optional[Sequence[XMLValue]] = None,
    mechanism: Optional[XMLPassingMechanism] = None,
) -> Optional[PassingClause]:
    """Create the SQL/XML ``PASSING`` clause, or ``None`` when there is none.

    The querying XML expressions take a ready-made clause rather than the
    unpacked pieces, so callers that build one of those nodes directly can
    use this factory too. The unpacking lives here instead of at each call
    site because the three querying factories share it.

    Args:
        dialect: The SQL dialect the clause renders against.
        passing: Values to pass into the XML function.
        mechanism: Optional mechanism (``BY VALUE`` / ``BY REF``).

    Returns:
        A :class:`PassingClause`, or ``None`` when neither value is given —
        an absent clause rather than an empty one, so the composing
        formatters need no empty-clause special case.
    """
    if not passing and mechanism is None:
        return None
    return PassingClause(
        dialect,
        [_as_expression(dialect, item) for item in passing or []],
        mechanism,
    )


def xmlquery(
    dialect: "SQLDialectBase",
    query: XMLValue,
    passing: Optional[Sequence[XMLValue]] = None,
    passing_mechanism: Optional[XMLPassingMechanism] = None,
    returning_content: bool = True,
    empty_handling: Optional[XMLEmptyHandlingOption] = None,
) -> XMLQueryExpression:
    """Create a SQL/XML XMLQUERY expression."""
    return XMLQueryExpression(
        dialect,
        _as_expression(dialect, query),
        passing_clause(dialect, passing, passing_mechanism),
        returning_content,
        empty_handling,
    )


def xmlexists(
    dialect: "SQLDialectBase",
    query: XMLValue,
    passing: Optional[Sequence[XMLValue]] = None,
    passing_mechanism: Optional[XMLPassingMechanism] = None,
) -> XMLExistsPredicate:
    """Create a SQL/XML XMLEXISTS predicate."""
    return XMLExistsPredicate(
        dialect,
        _as_expression(dialect, query),
        passing_clause(dialect, passing, passing_mechanism),
    )


def xmltable(
    dialect: "SQLDialectBase",
    row_pattern: XMLValue,
    columns: Sequence[XMLTableColumn],
    passing: Optional[Sequence[XMLValue]] = None,
    passing_mechanism: Optional[XMLPassingMechanism] = None,
) -> XMLTableExpression:
    """Create a SQL/XML XMLTABLE table expression."""
    return XMLTableExpression(
        dialect,
        _as_expression(dialect, row_pattern),
        columns,
        passing_clause(dialect, passing, passing_mechanism),
    )

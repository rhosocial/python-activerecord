# src/rhosocial/activerecord/backend/expression/functions/xml.py
"""SQL/XML expression factory functions."""

from typing import TYPE_CHECKING, Optional, Sequence, Tuple, Union

from ..bases import BaseExpression
from ..core import Literal
from ..query_parts import OrderByClause
from ..xml import (
    PassingClause,
    XMLAggExpression,
    XMLAttribute,
    XMLAttributesExpression,
    XMLCommentExpression,
    XMLConcatExpression,
    XMLElementExpression,
    XMLEmptyHandlingOption,
    XMLExistsPredicate,
    XMLForestExpression,
    XMLForestItem,
    XMLParseDocumentType,
    XMLParseExpression,
    XMLPassingMechanism,
    XMLPIExpression,
    XMLRootExpression,
    XMLSerializeDocumentType,
    XMLSerializeExpression,
    XMLStandaloneOption,
    XMLTableColumn,
    XMLTableExpression,
    XMLWhitespaceOption,
    XMLQueryExpression,
)

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.dialect import SQLDialectBase

XMLValue = Union[str, BaseExpression]
XMLNamedValue = Tuple[XMLValue, Optional[str]]


def _as_expression(dialect: "SQLDialectBase", value: XMLValue) -> BaseExpression:
    return value if isinstance(value, BaseExpression) else Literal(dialect, value)


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
    target_type: str,
    document: bool = False,
    preserve_whitespace: bool = False,
) -> XMLSerializeExpression:
    """Create a SQL/XML XMLSERIALIZE expression."""
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

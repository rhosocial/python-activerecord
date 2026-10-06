# src/rhosocial/activerecord/backend/dialect/protocols/xml_querying.py
"""SQL/XML querying support: XMLQUERY, XMLEXISTS, XMLTABLE.

Also home to :class:`SQLXMLSupport`, the aggregate of all five SQL/XML
protocols, because an engine that supports the whole standard needs to say so
once and inheriting the five peers by hand would let it implement only some of
them while claiming the aggregate.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

from .xml_parsing import SQLXMLParsingSupport
from .xml_serialization import SQLXMLSerializationSupport
from .xml_construction import SQLXMLConstructionSupport
from .xml_aggregation import SQLXMLAggregationSupport

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.xml import (
        XMLExistsExpression,
        XMLQueryExpression,
        XMLTableExpression,
    )


@runtime_checkable
class SQLXMLQueryingSupport(Protocol):
    """Protocol for SQL/XML querying support."""

    def supports_xmlquery(self) -> bool:
        """Whether SQL/XML XMLQUERY is supported."""
        ...  # pragma: no cover

    def supports_xmlexists(self) -> bool:
        """Whether SQL/XML XMLEXISTS is supported."""
        ...  # pragma: no cover

    def supports_xmltable(self) -> bool:
        """Whether SQL/XML XMLTABLE is supported."""
        ...  # pragma: no cover

    def format_xmlquery_expression(self, expr: "XMLQueryExpression") -> Tuple[str, tuple]:
        """Format a SQL/XML XMLQUERY expression."""
        ...  # pragma: no cover

    def format_xmlexists_expression(self, expr: "XMLExistsExpression") -> Tuple[str, tuple]:
        """Format a SQL/XML XMLEXISTS predicate."""
        ...  # pragma: no cover

    def format_xmltable_expression(self, expr: "XMLTableExpression") -> Tuple[str, tuple]:
        """Format a SQL/XML XMLTABLE expression."""
        ...  # pragma: no cover


@runtime_checkable
class SQLXMLSupport(
    SQLXMLParsingSupport,
    SQLXMLSerializationSupport,
    SQLXMLConstructionSupport,
    SQLXMLAggregationSupport,
    SQLXMLQueryingSupport,
    Protocol,
):
    """Aggregate protocol for complete SQL/XML standard support.

    SQL/XML is the one feature split across five protocols by operation --
    parse, serialize, construct, aggregate, query -- because an engine may
    support some without the others. A dialect that supports the whole standard
    mixes this one; a dialect that supports XML but only XMLPARSE mixes
    :class:`~...xml_parsing.SQLXMLParsingSupport` instead.
    """

# src/rhosocial/activerecord/backend/expression/sources/xml.py
"""
``XMLTABLE`` -- XML projected into rows.

Like :mod:`.json`, a table function that only appears in a ``FROM`` clause.
PostgreSQL documents ``XMLTABLE`` as a table function returning
``setof record``: syntactically it reads like a call, semantically it can
only be used as a table.
"""

from typing import Any, Optional

from .base import TableSource

__all__ = ["XmlTableSource"]


class XmlTableSource(TableSource):
    """An ``XMLTABLE(...)`` row source."""

    __slots__ = ("source", "row_path", "columns")

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this source."""
        return "format_xml_table"

    def __init__(
        self,
        dialect: "SQLDialectBase",  # noqa: F821
        source: Any,
        row_path: str,
        columns: Optional[Any] = None,
        passing: Optional[Any] = None,
        alias: Optional[str] = None,
        alias_need_quote: bool = True,
    ) -> None:
        """Project XML into rows.

        Args:
            dialect: The dialect that will render this source.
            source: Expression producing the XML document, or ``None`` when
                the document arrives via ``passing``.
            row_path: XPath selecting the rows.
            columns: Column projections.
            passing: Bindings made available to the XPath expression.
            alias: Name this source is known by inside the query.
            alias_need_quote: Whether the alias is quoted when rendered.
        """
        super().__init__(dialect, alias=alias, alias_need_quote=alias_need_quote)
        self.source = source
        self.row_path = row_path
        self.columns = columns or []
        self.passing = passing
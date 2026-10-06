# src/rhosocial/activerecord/backend/expression/sources/derived.py
"""
Row sources computed for the duration of one statement.

A derived table and a ``VALUES`` list produce rows but nothing in the
catalogue ever refers to them. They are sources, not objects.
"""

from typing import Any, Optional

from .base import TableSource

__all__ = ["DerivedTableSource", "ValuesTableSource"]


class DerivedTableSource(TableSource):
    """A parenthesised subquery used as a table source."""

    __slots__ = ("query",)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this source."""
        return "format_derived_table"

    def __init__(
        self,
        dialect: "SQLDialectBase",  # noqa: F821
        query: Any,
        alias: Optional[str] = None,
        alias_need_quote: bool = True,
    ) -> None:
        """Wrap *query* as a derived table.

        Args:
            dialect: The dialect that will render this source.
            query: The query expression producing the rows.
            alias: Name this source is known by inside the query. Engines
                differ on whether an alias is optional here.
            alias_need_quote: Whether the alias is quoted when rendered.
        """
        super().__init__(dialect, alias=alias, alias_need_quote=alias_need_quote)
        self.query = query


class ValuesTableSource(TableSource):
    """A literal row constructor, ``VALUES (...), (...)``."""

    __slots__ = ("rows", "column_names")

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this source."""
        return "format_values_table"

    def __init__(
        self,
        dialect: "SQLDialectBase",  # noqa: F821
        rows: Any,
        column_names: Optional[Any] = None,
        alias: Optional[str] = None,
        alias_need_quote: bool = True,
    ) -> None:
        """Wrap literal rows as a table source.

        Args:
            dialect: The dialect that will render this source.
            rows: The literal row values.
            column_names: Column names for the constructed relation, if the
                engine accepts them.
            alias: Name this source is known by inside the query.
            alias_need_quote: Whether the alias is quoted when rendered.
        """
        super().__init__(dialect, alias=alias, alias_need_quote=alias_need_quote)
        self.rows = rows
        self.column_names = column_names
# src/rhosocial/activerecord/backend/expression/sources/json.py
"""
``JSON_TABLE`` -- JSON projected into rows.

This is not a table and never was: the rows exist only while the statement
runs, and nothing in the catalogue can name them. PostgreSQL's SQL/JSON
``JSON_TABLE`` and Oracle's row-source ``JSON_TABLE`` both present a
relational view over JSON, but the *view* lives in the query, which is
exactly why this belongs beside the other table sources rather than among
the schema objects.
"""

from typing import Any, Optional

from .base import TableSource

__all__ = ["JsonTableSource"]


class JsonTableSource(TableSource):
    """A ``JSON_TABLE(...)`` row source."""

    __slots__ = ("source", "path", "columns")

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this source."""
        return "format_json_table"

    def __init__(
        self,
        dialect: "SQLDialectBase",  # noqa: F821
        source: Any,
        path: str,
        columns: Optional[Any] = None,
        alias: Optional[str] = None,
        alias_need_quote: bool = True,
    ) -> None:
        """Project JSON into rows.

        Args:
            dialect: The dialect that will render this source.
            source: Expression producing the JSON document.
            path: JSON path selecting the rows.
            columns: Column projections.
            alias: Name this source is known by inside the query.
            alias_need_quote: Whether the alias is quoted when rendered.
        """
        super().__init__(dialect, alias=alias, alias_need_quote=alias_need_quote)
        self.source = source
        self.path = path
        self.columns = columns or []
# src/rhosocial/activerecord/backend/dialect/protocols/query/dql_support.py
"""Protocol for base DQL rendering. Pure-format family group (supports empty)."""

from typing import TYPE_CHECKING, Any, List, Tuple
from rhosocial.activerecord.backend.expression.bases import ToSQLProtocol
from rhosocial.activerecord.backend.expression.query_parts import SortDirection
from typing import runtime_checkable, Protocol

@runtime_checkable
class DQLSupport(Protocol):
    def build_limit_offset(self, limit=None, offset=None) -> Tuple[str, List]:
        ...  # pragma: no cover

    def format_limit_offset_clause(self, expr: "LimitOffsetClause") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_where_clause(self, expr: "WhereClause") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_order_by_clause(self, expr: "OrderByClause") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_order_by_item(self, expr: "OrderByItem") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_group_by_having_clause(self, expr: "GroupByHavingClause") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_query_statement(self, expr: "QueryStatement") -> Tuple[str, tuple]:
        ...  # pragma: no cover

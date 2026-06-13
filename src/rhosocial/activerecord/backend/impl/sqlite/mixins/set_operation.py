# src/rhosocial/activerecord/backend/impl/sqlite/mixins/set_operation.py
"""
SQLite-specific Set Operation implementation.

This module provides the SQLiteSetOperationMixin class.
"""

from typing import Optional, Tuple, TYPE_CHECKING
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.expression.query_parts import (
        OrderByClause,
        LimitOffsetClause,
        ForUpdateClause,
    )

_SUGGESTION_FOR_UPDATE_SET_OP = "SQLite does not support FOR UPDATE clause in set operations (UNION, INTERSECT, EXCEPT)"


class SQLiteSetOperationMixin:
    """SQLite-specific set operation (UNION, INTERSECT, EXCEPT) formatting."""

    def format_set_operation_expression(
        self,
        left,
        right,
        operation: str,
        alias: Optional[str],
        all_: bool,
        order_by_clause: Optional["OrderByClause"] = None,
        limit_offset_clause: Optional["LimitOffsetClause"] = None,
        for_update_clause: Optional["ForUpdateClause"] = None,
    ) -> Tuple[str, Tuple]:
        """Format set operation expression (UNION, INTERSECT, EXCEPT)."""
        left_sql, left_params = left.to_sql()
        right_sql, right_params = right.to_sql()
        all_str = " ALL" if all_ else ""

        base_sql = f"{left_sql} {operation}{all_str} {right_sql}"

        all_params = list(left_params + right_params)
        sql_parts = [base_sql]

        if alias:
            sql_parts.append(f"AS {self.format_identifier(alias)}")

        if order_by_clause:
            order_by_sql, order_by_params = order_by_clause.to_sql()
            sql_parts.append(order_by_sql)
            all_params.extend(order_by_params)

        if limit_offset_clause:
            limit_offset_sql, limit_offset_params = limit_offset_clause.to_sql()
            sql_parts.append(limit_offset_sql)
            all_params.extend(limit_offset_params)

        if for_update_clause:
            if self.supports_set_operation_for_update():
                for_update_sql, for_update_params = for_update_clause.to_sql()
                sql_parts.append(for_update_sql)
                all_params.extend(for_update_params)
            else:
                raise UnsupportedFeatureError(self.name, "FOR UPDATE in set operations", _SUGGESTION_FOR_UPDATE_SET_OP)

        sql = " ".join(sql_parts)
        return sql, tuple(all_params)


# =============================================================================
# SQLiteViewMixin — View DDL support
# =============================================================================


# src/rhosocial/activerecord/backend/impl/sqlite/mixins/dml.py
"""
SQLite-specific Dml implementation.

This module provides the SQLiteDMLMixin class.
"""

from typing import Any, List, Tuple, TYPE_CHECKING
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.expression.statements import InsertExpression, ReturningClause

class SQLiteDMLMixin:
    """SQLite-specific INSERT and RETURNING formatting."""

    def format_insert_statement(self, expr: "InsertExpression") -> Tuple[str, tuple]:
        """Format INSERT statement with SQLite-specific OR REPLACE / OR IGNORE support."""
        or_replace = expr.dialect_options.get("or_replace", False)
        or_ignore = expr.dialect_options.get("or_ignore", False)

        if or_replace and or_ignore:
            raise ValueError("Cannot specify both 'or_replace' and 'or_ignore' in dialect_options.")
        if (or_replace or or_ignore) and expr.on_conflict:
            raise ValueError(
                "Cannot use 'or_replace'/'or_ignore' together with 'on_conflict'. "
                "Use either the SQLite-specific OR REPLACE/IGNORE syntax or the "
                "standard ON CONFLICT clause, but not both."
            )

        if self.strict_validation:
            expr.validate(strict=True)

        all_params: List[Any] = []
        table_sql, table_params = expr.into.to_sql()
        all_params.extend(table_params)

        columns_sql = ""
        if expr.columns:
            columns_sql = "(" + ", ".join([self.format_identifier(c) for c in expr.columns]) + ")"

        source_sql = ""
        from rhosocial.activerecord.backend.expression.statements import (
            DefaultValuesSource,
            ValuesSource,
            SelectSource,
        )

        if isinstance(expr.source, DefaultValuesSource):
            source_sql = "DEFAULT VALUES"
        elif isinstance(expr.source, ValuesSource):
            all_rows_sql = []
            for row in expr.source.values_list:
                row_sql, row_params = [], []
                for val in row:
                    s, p = val.to_sql()
                    row_sql.append(s)
                    row_params.extend(p)
                all_rows_sql.append(f"({', '.join(row_sql)})")
                all_params.extend(row_params)
            source_sql = "VALUES " + ", ".join(all_rows_sql)
        elif isinstance(expr.source, SelectSource):
            s_sql, s_params = expr.source.select_query.to_sql()
            source_sql = s_sql
            all_params.extend(s_params)

        if or_replace:
            sql = f"INSERT OR REPLACE INTO {table_sql} {columns_sql} {source_sql}".strip()
        elif or_ignore:
            sql = f"INSERT OR IGNORE INTO {table_sql} {columns_sql} {source_sql}".strip()
        else:
            sql = f"INSERT INTO {table_sql} {columns_sql} {source_sql}".strip()

        if expr.on_conflict:
            conflict_sql, conflict_params = self.format_on_conflict_clauses(expr)
            sql += f" {conflict_sql}"
            all_params.extend(conflict_params)

        if expr.returning:
            if not self.supports_returning_insert():
                raise UnsupportedFeatureError(
                    self.name,
                    "RETURNING clause in INSERT",
                    "This SQLite version does not support RETURNING in INSERT statements.",
                )
            returning_sql, returning_params = self.format_returning_clause(expr.returning)
            sql += f" {returning_sql}"
            all_params.extend(returning_params)

        return sql, tuple(all_params)

    def format_returning_clause(self, clause: "ReturningClause") -> Tuple[str, tuple]:
        """Format RETURNING clause."""
        all_params = []
        expr_parts = []
        for expr in clause.expressions:
            expr_sql, expr_params = expr.to_sql()
            expr_parts.append(expr_sql)
            all_params.extend(expr_params)

        returning_sql = f"RETURNING {', '.join(expr_parts)}"

        if clause.alias:
            returning_sql += f" AS {self.format_identifier(clause.alias)}"

        return returning_sql, tuple(all_params)

    def format_match_predicate(
        self,
        expr,
    ) -> Tuple[str, tuple]:
        """Format full-text search MATCH predicate for FTS5."""
        return self.format_fts5_match_expression(expr.table, expr.query, expr.columns, expr.negate)


# =============================================================================
# SQLiteSetOperationMixin — UNION/INTERSECT/EXCEPT formatting
# =============================================================================


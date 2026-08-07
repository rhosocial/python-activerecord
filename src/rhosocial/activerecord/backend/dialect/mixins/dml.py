# src/rhosocial/activerecord/backend/dialect/mixins/dml.py
from typing import Any, List, Tuple, TYPE_CHECKING

from ..exceptions import UnsupportedFeatureError
from ...expression.bases import BaseExpression

if TYPE_CHECKING:
    from ...expression.statements.dml import (
        DeleteExpression,
        InsertExpression,
        UpdateExpression,
    )


class DMLMixin:
    """Mixin for DML (INSERT/UPDATE/DELETE) statement formatting."""

    def format_insert_statement(self, expr: "InsertExpression") -> Tuple[str, tuple]:
        from ..exceptions import UnsupportedFeatureError
        from ...expression.statements import DefaultValuesSource, ValuesSource, SelectSource
        if self.strict_validation:
            expr.validate(strict=True)
        all_params: List[Any] = []
        table_sql, table_params = expr.into.to_sql()
        all_params.extend(table_params)
        columns_sql = ""
        if expr.columns:
            columns_sql = "(" + ", ".join([self.format_identifier(c) for c in expr.columns]) + ")"
        source_sql = ""
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
                    "This dialect does not support RETURNING in INSERT statements.",
                )
            returning_sql, returning_params = self.format_returning_clause(expr.returning)
            sql += f" {returning_sql}"
            all_params.extend(returning_params)
        return sql, tuple(all_params)

    def format_on_conflict_clauses(self, expr: "InsertExpression") -> Tuple[str, tuple]:
        """Format one or more ON CONFLICT clauses, gated by capability switches.

        Args:
            expr: InsertExpression carrying ``on_conflict`` (list of clauses or None).

        Returns:
            Tuple of (SQL string, parameters tuple). Returns ("", ()) when no
            clauses are present.
        """
        if not expr.on_conflict:
            return "", ()
        if not self.supports_on_conflict_clause():
            raise UnsupportedFeatureError(
                self.name,
                "ON CONFLICT clause in INSERT",
                "This dialect does not support ON CONFLICT style clauses in "
                "INSERT; use the backend-specific upsert mechanism instead.",
            )
        if len(expr.on_conflict) > 1 and not self.supports_multiple_on_conflict_clauses():
            raise UnsupportedFeatureError(
                self.name,
                "multiple ON CONFLICT clauses in INSERT",
                "This dialect supports at most one ON CONFLICT clause per "
                "INSERT statement.",
            )
        parts: List[str] = []
        params: List[Any] = []
        for clause in expr.on_conflict:
            clause_sql, clause_params = clause.to_sql()
            parts.append(clause_sql)
            params.extend(clause_params)
        return " ".join(parts), tuple(params)

    def format_update_statement(self, expr: "UpdateExpression") -> Tuple[str, tuple]:
        from ..exceptions import UnsupportedFeatureError
        from ...expression.statements import QueryExpression
        all_params: List[Any] = []
        table_sql, table_params = expr.table.to_sql()
        all_params.extend(table_params)
        assignment_parts = []
        for col, e in expr.assignments.items():
            col_sql = self.format_identifier(col)
            expr_sql, expr_params = e.to_sql()
            assignment_parts.append(f"{col_sql} = {expr_sql}")
            all_params.extend(expr_params)
        current_sql = f"UPDATE {table_sql} SET {', '.join(assignment_parts)}"
        if expr.from_:
            from_sql_parts = []
            from_params: List[Any] = []

            def _fmt_from(source):
                if isinstance(source, str):
                    return self.format_identifier(source), []
                if isinstance(source, QueryExpression):
                    s_sql, s_params = source.to_sql()
                    return f"({s_sql})", list(s_params)
                if isinstance(source, BaseExpression):
                    s_sql, s_params = source.to_sql()
                    return s_sql, list(s_params)
                raise TypeError(f"Unsupported FROM source type: {type(source)}")

            if isinstance(expr.from_, list):
                for source_item in expr.from_:
                    item_sql, item_params = _fmt_from(source_item)
                    from_sql_parts.append(item_sql)
                    from_params.extend(item_params)
                current_sql += f" FROM {', '.join(from_sql_parts)}"
                all_params.extend(from_params)
            else:
                from_expr_sql, from_expr_params = _fmt_from(expr.from_)
                current_sql += f" FROM {from_expr_sql}"
                all_params.extend(from_expr_params)
        if expr.where:
            where_sql, where_params = expr.where.to_sql()
            current_sql += f" {where_sql}"
            all_params.extend(where_params)
        if expr.returning:
            if not self.supports_returning_update():
                raise UnsupportedFeatureError(
                    self.name,
                    "RETURNING clause in UPDATE",
                    "This dialect does not support RETURNING in UPDATE statements.",
                )
            returning_sql, returning_params = self.format_returning_clause(expr.returning)
            current_sql += f" {returning_sql}"
            all_params.extend(returning_params)
        return current_sql, tuple(all_params)

    def format_delete_statement(self, expr: "DeleteExpression") -> Tuple[str, tuple]:
        from ..exceptions import UnsupportedFeatureError
        from ...expression.statements import QueryExpression
        if self.strict_validation:
            expr.validate(strict=True)
        all_params: List[Any] = []
        table_sql_parts = []
        for table_expr in expr.tables:
            table_sql, table_params = table_expr.to_sql()
            table_sql_parts.append(table_sql)
            all_params.extend(table_params)
        current_sql = f"DELETE FROM {', '.join(table_sql_parts)}"
        if expr.using:
            using_sql_parts = []
            using_params: List[Any] = []

            def _fmt_using(source):
                if isinstance(source, str):
                    return self.format_identifier(source), []
                if isinstance(source, QueryExpression):
                    s_sql, s_params = source.to_sql()
                    return f"({s_sql})", list(s_params)
                if isinstance(source, BaseExpression):
                    s_sql, s_params = source.to_sql()
                    return s_sql, list(s_params)
                return str(source), []

            if isinstance(expr.using, list):
                for source_item in expr.using:
                    item_sql, item_params = _fmt_using(source_item)
                    using_sql_parts.append(item_sql)
                    using_params.extend(item_params)
                current_sql += f" USING {', '.join(using_sql_parts)}"
                all_params.extend(using_params)
            else:
                using_expr_sql, using_expr_params = _fmt_using(expr.using)
                current_sql += f" USING {using_expr_sql}"
                all_params.extend(using_params)
        if expr.where:
            where_sql, where_params = expr.where.to_sql()
            current_sql += f" {where_sql}"
            all_params.extend(where_params)
        if expr.returning:
            if not self.supports_returning_delete():
                raise UnsupportedFeatureError(
                    self.name,
                    "RETURNING clause in DELETE",
                    "This dialect does not support RETURNING in DELETE statements.",
                )
            returning_sql, returning_params = self.format_returning_clause(expr.returning)
            current_sql += f" {returning_sql}"
            all_params.extend(returning_params)
        return current_sql, tuple(all_params)

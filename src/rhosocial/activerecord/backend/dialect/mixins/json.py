# src/rhosocial/activerecord/backend/dialect/mixins/json.py
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from ..exceptions import UnsupportedFeatureError
from ...expression import bases

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.advanced_functions import JSONExpression


class JSONMixin:
    """Mixin for JSON type support."""

    def supports_json_type(self) -> bool:
        """Whether JSON type is supported."""
        return False

    def get_json_access_operator(self) -> str:
        """
        Get JSON access operator.

        Returns:
            '->' (PostgreSQL/MySQL/SQLite) or other dialect-specific operator
        """
        return "->"

    def supports_json_table(self) -> bool:
        """Whether JSON_TABLE function is supported."""
        return False

    def format_json_expression(self, expr: "JSONExpression") -> Tuple[str, Tuple]:
        """Format JSON expression."""
        if isinstance(expr.column, bases.BaseExpression):
            col_sql, col_params = expr.column.to_sql()
        else:
            col_sql, col_params = self.format_identifier(str(expr.column)), ()
        sql = f"({col_sql} {expr.operation} {self.get_parameter_placeholder()})"
        params = col_params + (expr.path,)

        # Apply type casts if any (before alias)
        if expr.cast_types:
            for target_type in expr.cast_types:
                sql, params = self.format_cast_expression(sql, target_type, params, None)

        # Apply alias if any (after type casts)
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"

        return sql, params

    def format_json_table_expression(
        self, json_col_sql: str, path: str, columns: List[Dict[str, Any]], alias: Optional[str], params: tuple
    ) -> Tuple[str, Tuple]:
        """
        Formats a JSON_TABLE expression.

        Args:
            json_col_sql: SQL for the JSON column/expression.
            path: The JSON path expression.
            columns: A list of dictionaries, each defining a column.
            alias: The alias for the resulting table.
            params: Parameters for the JSON column expression.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted expression.
        """
        if not self.supports_json_table():
            raise UnsupportedFeatureError(self.name, "JSON_TABLE function")

        # Escape path to prevent SQL injection.
        escaped_path = self._escape_sql_string(path)

        cols_defs = []
        for col in columns:
            col_name = self.format_identifier(col["name"])
            col_type = col["type"]
            col_path = self._escape_sql_string(col["path"])
            cols_defs.append(f"{col_name} {col_type} PATH '{col_path}'")

        columns_sql = f"COLUMNS({', '.join(cols_defs)})"
        if alias is not None:
            sql = f"JSON_TABLE({json_col_sql}, '{escaped_path}' {columns_sql}) AS {self.format_identifier(alias)}"
        else:
            sql = f"JSON_TABLE({json_col_sql}, '{escaped_path}' {columns_sql})"
        return sql, params

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

    def supports_json_arrow_operators(self) -> bool:
        """Whether JSON arrow operators (-> and ->>) are supported.

        PostgreSQL, MySQL, and SQLite support these operators natively.
        MariaDB, Oracle, SQL Server, Snowflake, and Firebird do NOT support
        them and must use function-based alternatives (e.g., JSON_EXTRACT).

        Returns:
            True if the dialect supports JSON arrow operators.
        """
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

    # ------------------------------------------------------------------
    # Arrow-operator formatting (-> / ->>)
    # ------------------------------------------------------------------

    def format_json_arrow_expression(self, expr: "JSONExpression") -> Tuple[str, Tuple]:
        """Format JSON expression using arrow operators (-> / ->>).

        This method always uses arrow operator syntax. If the dialect does
        not support arrow operators, it raises UnsupportedFeatureError.

        Raises:
            UnsupportedFeatureError: If arrow operators are not supported.
        """
        if not self.supports_json_arrow_operators():
            raise UnsupportedFeatureError(
                self.name,
                "JSON arrow operators (-> / ->>)",
                f"{self.name} does not support JSON arrow operators. "
                "Use function-based JSON extraction instead.",
            )

        if isinstance(expr.column, bases.BaseExpression):
            col_sql, col_params = expr.column.to_sql()
        else:
            col_sql, col_params = self.format_identifier(str(expr.column)), ()

        escaped_path = self._escape_sql_string(expr.path)
        sql = f"{col_sql}{expr.operation}'{escaped_path}'"
        params = col_params

        if expr.cast_types:
            for target_type in expr.cast_types:
                sql, params = self.format_cast_expression(sql, target_type, params, None)

        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"

        return sql, params

    # ------------------------------------------------------------------
    # Function-based formatting (JSON_EXTRACT / JSON_UNQUOTE etc.)
    # ------------------------------------------------------------------

    def format_json_function_expression(self, expr: "JSONExpression") -> Tuple[str, Tuple]:
        """Format JSON expression using function-based equivalents.

        Default implementation uses JSON_EXTRACT for -> and
        JSON_UNQUOTE(JSON_EXTRACT(...)) for ->>.

        Backends without arrow operator support should override this
        method to provide the correct function-based SQL.
        """
        if isinstance(expr.column, bases.BaseExpression):
            col_sql, col_params = expr.column.to_sql()
        else:
            col_sql, col_params = self.format_identifier(str(expr.column)), ()

        escaped_path = self._escape_sql_string(expr.path)

        if expr.operation == "->":
            sql = f"JSON_EXTRACT({col_sql}, '{escaped_path}')"
            params = col_params
        elif expr.operation == "->>":
            sql = f"JSON_UNQUOTE(JSON_EXTRACT({col_sql}, '{escaped_path}'))"
            params = col_params
        else:
            sql = f"{col_sql} {expr.operation} '{escaped_path}'"
            params = col_params

        if expr.cast_types:
            for target_type in expr.cast_types:
                sql, params = self.format_cast_expression(sql, target_type, params, None)

        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"

        return sql, params

    # ------------------------------------------------------------------
    # Dispatch entry point
    # ------------------------------------------------------------------

    def format_json_expression(self, expr: "JSONExpression") -> Tuple[str, Tuple]:
        """Format JSON expression.

        Dispatches to arrow-operator or function-based formatting depending
        on the expression's *mode* and the dialect's capability:

        - ``JSONPathMode.ARROW``:    always use arrow operators (raises if unsupported)
        - ``JSONPathMode.FUNCTION``: always use function-based formatting
        - ``JSONPathMode.AUTO``:     use arrow if supported, else function-based

        The default mode is ``JSONPathMode.AUTO``.
        """
        from ...expression.advanced_functions import JSONPathMode

        mode: JSONPathMode = getattr(expr, "mode", JSONPathMode.AUTO)

        if mode is JSONPathMode.ARROW:
            return self.format_json_arrow_expression(expr)

        if mode is JSONPathMode.FUNCTION:
            return self.format_json_function_expression(expr)

        # auto: prefer arrow if supported, fall back to function
        if self.supports_json_arrow_operators():
            return self.format_json_arrow_expression(expr)
        return self.format_json_function_expression(expr)

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

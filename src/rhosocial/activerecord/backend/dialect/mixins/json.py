# src/rhosocial/activerecord/backend/dialect/mixins/json.py
"""Dialect mixin for JSON expression support.

Provides capability probes for JSON types and operators, and formats JSON
path access using either arrow operators or function-based equivalents.
"""
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from ..exceptions import UnsupportedFeatureError
from ...expression import bases

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.advanced_functions import JSONExpression


class JSONMixin:
    """Mixin for JSON type support.

    Dialects advertise JSON capabilities through the ``supports_json_*``
    probes and control formatting through :meth:`format_json_expression`,
    which dispatches to arrow-operator or function-based SQL.
    """

    def supports_json_type(self) -> bool:
        """Whether JSON type is supported. Defaults to False."""
        return False

    def supports_json_arrow_operators(self) -> bool:
        """Whether JSON arrow operators (-> and ->>) are supported.

        PostgreSQL, MySQL, and SQLite support these operators natively.
        MariaDB, Oracle, SQL Server, Snowflake, and Firebird do NOT support
        them and must use function-based alternatives (e.g., JSON_EXTRACT).

        Returns:
            True if the dialect supports JSON arrow operators. Defaults to False.
        """
        return False

    def get_json_access_operator(self) -> str:
        """Get the JSON access operator used by this dialect.

        Returns:
            '->' (PostgreSQL/MySQL/SQLite) or another dialect-specific operator.
        """
        return "->"

    def supports_json_table(self) -> bool:
        """Whether JSON_TABLE function is supported. Defaults to False."""
        return False

    # ------------------------------------------------------------------
    # Arrow-operator formatting (-> / ->>)
    # ------------------------------------------------------------------

    def format_json_arrow_expression(self, expr: "JSONExpression") -> Tuple[str, Tuple]:
        """Format JSON expression using arrow operators (-> / ->>).

        This method always uses arrow operator syntax. If the dialect does
        not support arrow operators, it raises UnsupportedFeatureError.

        Args:
            expr: The JSONExpression node with column, path, operation, and
                optional alias.

        Returns:
            Tuple of (SQL string, parameters tuple) for the expression.

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

        Args:
            expr: The JSONExpression node with column, path, operation, and
                optional alias.

        Returns:
            Tuple of (SQL string, parameters tuple) for the expression.
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

        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"

        return sql, params

    # ------------------------------------------------------------------
    # Dispatch entry point
    # ------------------------------------------------------------------

    def format_json_expression(self, expr: "JSONExpression") -> Tuple[str, Tuple]:
        """Format JSON expression, dispatching on mode and capability.

        Dispatches to arrow-operator or function-based formatting depending
        on the expression's *mode* and the dialect's capability:

        - ``JSONPathMode.ARROW``:    always use arrow operators (raises if unsupported)
        - ``JSONPathMode.FUNCTION``: always use function-based formatting
        - ``JSONPathMode.AUTO``:     use arrow if supported, else function-based

        The default mode is ``JSONPathMode.AUTO``.

        Args:
            expr: The JSONExpression node to format.

        Returns:
            Tuple of (SQL string, parameters tuple) for the expression.

        Raises:
            UnsupportedFeatureError: If arrow mode is requested but arrow
                operators are not supported.
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

    def format_json_table_expression(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        """Format a :class:`~...expression.query_sources.JSONTableExpression` node.

        Args:
            expr: The JSONTableExpression node with JSON column, path, column
                definitions, and optional alias.

        Returns:
            Tuple of (SQL string, parameters tuple) for the expression.

        Raises:
            UnsupportedFeatureError: If JSON_TABLE is not supported.
        """
        from ...expression import bases as _bases

        if not self.supports_json_table():
            raise UnsupportedFeatureError(self.name, "JSON_TABLE function")

        if isinstance(expr.json_column, _bases.BaseExpression):
            json_col_sql, params = expr.json_column.to_sql()
        else:
            json_col_sql, params = self.format_identifier(str(expr.json_column)), ()

        escaped_path = self._escape_sql_string(expr.path)

        cols_defs = []
        for col in expr.columns:
            col_name = self.format_identifier(col.name)
            if isinstance(col.data_type, _bases.BaseExpression):
                col_type, _ = col.data_type.to_sql()
            else:
                col_type = str(col.data_type)
            col_path = self._escape_sql_string(col.path)
            cols_defs.append(f"{col_name} {col_type} PATH '{col_path}'")

        columns_sql = f"COLUMNS({', '.join(cols_defs)})"
        if expr.alias is not None:
            sql = f"JSON_TABLE({json_col_sql}, '{escaped_path}' {columns_sql}) AS {self.format_identifier(expr.alias)}"
        else:
            sql = f"JSON_TABLE({json_col_sql}, '{escaped_path}' {columns_sql})"
        return sql, params

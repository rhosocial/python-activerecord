# src/rhosocial/activerecord/backend/expression/statements/ddl_function.py
"""Function DDL statement expressions."""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ..bases import BaseExpression, SQLQueryAndParams

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase


class CreateFunctionExpression(BaseExpression):
    """SQL/PSM standard CREATE FUNCTION statement.

    Examples:
        create_func = CreateFunctionExpression(
            dialect,
            function_name="calculate_total",
            parameters=[
                {"name": "price", "type": "DECIMAL(10,2)"},
                {"name": "quantity", "type": "INTEGER"}
            ],
            returns="DECIMAL(10,2)",
            body="RETURN price * quantity;",
            language="plpgsql"
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        function_name: str,
        parameters: Optional[List[Dict[str, str]]] = None,
        returns: Optional[str] = None,
        body: str = "",
        language: str = "plpgsql",
        or_replace: bool = False,
        *,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.function_name = function_name
        self.parameters = parameters or []
        self.returns = returns
        self.body = body
        self.language = language
        self.or_replace = or_replace
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> "SQLQueryAndParams":
        return self.dialect.format_create_function_statement(self)


class DropFunctionExpression(BaseExpression):
    """SQL/PSM standard DROP FUNCTION statement.

    Examples:
        drop_func = DropFunctionExpression(
            dialect,
            function_name="calculate_total",
            if_exists=True
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        function_name: str,
        if_exists: bool = False,
        parameters: Optional[List[str]] = None,
        cascade: bool = False,
        *,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.function_name = function_name
        self.if_exists = if_exists
        self.parameters = parameters
        self.cascade = cascade
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> "SQLQueryAndParams":
        return self.dialect.format_drop_function_statement(self)

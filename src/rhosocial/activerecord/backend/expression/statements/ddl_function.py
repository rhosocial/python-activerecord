# src/rhosocial/activerecord/backend/expression/statements/ddl_function.py
"""Function DDL statement expressions."""

from ..core import _validate_schema_name
from typing import Dict, List, Optional, TYPE_CHECKING

from ..bases import BaseExpression

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

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_create_function_statement"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        function_name: str,
        parameters: Optional[List[Dict[str, str]]] = None,
        returns: Optional[str] = None,
        body: str = "",
        language: str = "plpgsql",
        or_replace: bool = False,
        schema_name: Optional[str] = None,
    ):
        """
        Args:
            schema_name: Namespace to qualify the function with, e.g. ``app``.
                None leaves the name unqualified. An empty string raises
                ValueError, and a dialect with no namespace raises
                UnsupportedFeatureError.
        """
        super().__init__(dialect)
        self.function_name = function_name
        self.schema_name = _validate_schema_name(
            schema_name, type(self).__name__
        )
        self.parameters = parameters or []
        self.returns = returns
        self.body = body
        self.language = language
        self.or_replace = or_replace


class DropFunctionExpression(BaseExpression):
    """SQL/PSM standard DROP FUNCTION statement.

    Examples:
        drop_func = DropFunctionExpression(
            dialect,
            function_name="calculate_total",
            if_exists=True
        )
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_drop_function_statement"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        function_name: str,
        if_exists: bool = False,
        parameters: Optional[List[str]] = None,
        cascade: bool = False,
        schema_name: Optional[str] = None,
    ):
        """
        Args:
            schema_name: Namespace to qualify the function with, e.g. ``app``.
                None leaves the name unqualified. An empty string raises
                ValueError, and a dialect with no namespace raises
                UnsupportedFeatureError.
        """
        super().__init__(dialect)
        self.function_name = function_name
        self.schema_name = _validate_schema_name(
            schema_name, type(self).__name__
        )
        self.if_exists = if_exists
        self.parameters = parameters
        self.cascade = cascade

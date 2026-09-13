# src/rhosocial/activerecord/backend/dialect/mixins/function.py
"""Function-related dialect mixins.

Contains :class:`FunctionCallMixin` for rendering scalar/aggregate function
*call* expressions in queries, and :class:`FunctionMixin` for SQL/PSM
function *DDL* (``CREATE FUNCTION`` / ``DROP FUNCTION``).
"""
import re
from typing import Any, Dict, List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ...expression import bases
    from ...expression.statements import (
        CreateFunctionExpression,
        DropFunctionExpression,
    )


class FunctionCallMixin:
    """Mixin for formatting scalar and aggregate function call expressions.

    Distinct from :class:`FunctionMixin`, which covers SQL/PSM function DDL
    (``CREATE FUNCTION`` / ``DROP FUNCTION``). Call formatting is a query
    expression concern and is therefore composed into
    :class:`~.expression.ExpressionMixin`.
    """

    def format_function_call(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        """Format a scalar or aggregate function call expression.

        Renders ``NAME(args)`` with optional ``DISTINCT`` and a trailing
        ``FILTER (WHERE ...)`` clause. ``COUNT(*)`` is special-cased so that
        a wildcard argument renders as ``*``. Niladic functions with no
        arguments and no ``DISTINCT`` omit the parentheses.

        Args:
            expr: The function call expression to render.

        Returns:
            A ``(sql, params)`` tuple.

        Raises:
            UnsupportedFeatureError: If a ``FILTER`` clause is requested on a
                dialect that does not support it.
        """
        from ...expression import aggregates, core, operators
        from ..protocols import FilterClauseSupport
        from .filter_clause import FilterClauseMixin

        if (
            isinstance(expr, aggregates.AggregateFunctionCall)
            and expr.func_name.upper() == "COUNT"
            and len(expr.args) == 1
            and (
                (isinstance(expr.args[0], operators.RawSQLExpression) and expr.args[0].expression == "*")
                or isinstance(expr.args[0], core.WildcardExpression)
            )
        ):
            args_sql = ["*"]
            args_params = []
        else:
            args_sql = []
            args_params = []
            for arg in expr.args:
                sql_part, params_part = arg.to_sql()
                args_sql.append(sql_part)
                args_params.append(params_part)

        distinct = "DISTINCT " if expr.is_distinct else ""
        args_sql_str = ", ".join(args_sql)

        if getattr(expr, "niladic", False) and not args_sql and not distinct:
            func_call_sql = expr.func_name.upper()
        else:
            func_call_sql = f"{expr.func_name.upper()}({distinct}{args_sql_str})"

        all_params: List[Any] = []
        for param_tuple in args_params:
            all_params.extend(param_tuple)

        filter_predicate = getattr(expr, "filter_predicate", None)
        if filter_predicate:
            if isinstance(self, FilterClauseSupport) and isinstance(self, FilterClauseMixin):
                if self.supports_filter_clause():
                    from ...expression.statements.filter_clause import FilterClauseExpression
                    filter_expr = FilterClauseExpression(self, condition=filter_predicate)
                    filter_clause_sql, filter_clause_params = self.format_filter_clause(filter_expr)
                    func_call_sql += f" {filter_clause_sql}"
                    all_params.extend(filter_clause_params)
                else:
                    from ..exceptions import UnsupportedFeatureError
                    raise UnsupportedFeatureError(
                        self.name,
                        "FILTER clause in aggregate functions",
                        "Use a CASE expression inside the aggregate function instead.",
                    )
            else:
                from ..exceptions import UnsupportedFeatureError
                raise UnsupportedFeatureError(
                    self.name,
                    "FILTER clause in aggregate functions",
                    "Use a CASE expression inside the aggregate function instead.",
                )

        if expr.alias:
            func_call_sql = f"{func_call_sql} AS {self.format_identifier(expr.alias)}"

        return func_call_sql, tuple(all_params)


class FunctionMixin:
    """Format SQL/PSM function DDL statements (CREATE FUNCTION / DROP FUNCTION).

    Capability probes default to ``False`` and are overridden by dialects that
    support user-defined functions.
    """

    def supports_function(self) -> bool:
        """Whether user-defined functions are supported (defaults to False)."""
        return False

    def supports_create_function(self) -> bool:
        """Whether CREATE FUNCTION is supported (defaults to False)."""
        return False

    def supports_drop_function(self) -> bool:
        """Whether DROP FUNCTION is supported (defaults to False)."""
        return False

    def supports_function_or_replace(self) -> bool:
        """Whether CREATE OR REPLACE FUNCTION is supported (defaults to False)."""
        return False

    def supports_function_parameters(self) -> bool:
        """Whether function parameter lists are supported (defaults to False)."""
        return False

    def supports_functions(self) -> Dict[str, bool]:
        """Return supported SQL functions as function_name -> bool mapping.

        Default implementation returns empty dict. Subclasses should override
        to provide actual function list from both core and backend-specific sources.

        Returns:
            Dict mapping function names to True/False. Default: empty dict.
        """
        return {}

    def format_create_function_statement(self, expr: "CreateFunctionExpression") -> Tuple[str, tuple]:
        """Format a CREATE FUNCTION statement per SQL/PSM.

        Args:
            expr: The CreateFunctionExpression to render.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is always empty.

        Raises:
            UnsupportedFeatureError: If the dialect does not support functions.
            ValueError: If a parameter or return type contains invalid
                characters.
        """
        from ..exceptions import UnsupportedFeatureError

        if not self.supports_function():
            raise UnsupportedFeatureError(self.name, "functions")

        parts = ["CREATE FUNCTION"]

        if expr.or_replace and self.supports_function_or_replace():
            parts.insert(1, "OR REPLACE")

        parts.append(self.format_identifier(expr.function_name))

        if expr.parameters and self.supports_function_parameters():
            param_strs = []
            for p in expr.parameters:
                name = p.get("name", "")
                param_type = p.get("type", "")
                if name and param_type:
                    # Validate parameter name and type.
                    param_name = self.format_identifier(name)
                    if not re.fullmatch(r"[A-Za-z0-9\s(),]+", param_type):
                        raise ValueError(f"Invalid parameter type '{param_type}'")
                    param_strs.append(f"{param_name} {param_type}")
                elif param_type:
                    param_strs.append(param_type)
            parts.append(f"({', '.join(param_strs)})")
        else:
            parts.append("()")

        if expr.returns:
            # Validate return type.
            if not re.fullmatch(r"[A-Za-z0-9\s(),]+", expr.returns):
                raise ValueError(f"Invalid return type '{expr.returns}'")
            parts.append(f"RETURNS {expr.returns}")

        if expr.language:
            parts.append(f"LANGUAGE {expr.language}")

        if expr.body:
            parts.append("AS")
            parts.append(f"$${expr.body}$$")

        return " ".join(parts), ()

    def format_drop_function_statement(self, expr: "DropFunctionExpression") -> Tuple[str, tuple]:
        """Format a DROP FUNCTION statement per SQL/PSM.

        Args:
            expr: The DropFunctionExpression to render.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is always empty.

        Raises:
            UnsupportedFeatureError: If the dialect does not support functions.
        """
        from ..exceptions import UnsupportedFeatureError

        if not self.supports_function():
            raise UnsupportedFeatureError(self.name, "functions")

        parts = ["DROP FUNCTION"]

        if expr.if_exists:
            parts.append("IF EXISTS")

        parts.append(self.format_identifier(expr.function_name))

        if expr.parameters:
            param_types = ", ".join(expr.parameters)
            parts.append(f"({param_types})")

        if expr.cascade:
            parts.append("CASCADE")

        return " ".join(parts), ()

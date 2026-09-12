# src/rhosocial/activerecord/backend/dialect/mixins/expression.py
from typing import Any, List, Optional, Tuple

from ...expression import bases


class ExpressionMixin:
    """Mixin for general expression formatting (operators, functions, CAST, CASE, etc.)."""

    def format_literal_expression(self, expr: "bases.SQLValueExpression") -> Tuple[str, Tuple]:
        """Format a :class:`~...expression.core.Literal`.

        The construction-time ``inline_literals`` switch decides between an
        inline (escaped, quoted) SQL atom and a bind-parameter placeholder.
        """
        if expr.inline_literals:
            sql = self.format_literal(expr.value)
            params: tuple = ()
        else:
            sql = self.get_parameter_placeholder()
            params = (expr.value,)

        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"

        return sql, params

    def format_function_call(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        from ...expression import aggregates, core, operators
        from ..protocols import FilterClauseSupport
        from ..mixins import FilterClauseMixin

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

    def format_cast_expression(self, expr) -> Tuple[str, Tuple]:
        """Format a :class:`~...expression.core.CastExpression` node.

        ``CAST(expr AS type)`` is a unary tree node; the wrapped expression
        renders through its own ``to_sql()``.
        """
        expr_sql, params = expr.expression.to_sql()
        if not self._validate_data_type(expr.target_type):
            raise ValueError(
                f"Invalid target type '{expr.target_type}': "
                "must contain only alphanumeric characters, spaces, parentheses, and commas."
            )
        sql = f"CAST({expr_sql} AS {expr.target_type})"
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, params

    def format_sql_operation(self, expr) -> Tuple[str, Tuple]:
        """Format a :class:`~...expression.operators.SQLOperation` (n-ary)."""
        formatted_operands_sql = []
        params: List[Any] = []
        for operand in expr.operands:
            operand_sql, operand_params = operand.to_sql()
            formatted_operands_sql.append(operand_sql)
            params.extend(operand_params)
        if expr.operands:
            return f"{expr.op}({', '.join(formatted_operands_sql)})", tuple(params)
        return f"{expr.op}()", tuple(params)

    def format_binary_operator(self, expr) -> Tuple[str, Tuple]:
        """Format a :class:`~...expression.operators.BinaryExpression`."""
        left_sql, left_params = expr.left.to_sql()
        right_sql, right_params = expr.right.to_sql()
        return f"{left_sql} {expr.op} {right_sql}", left_params + right_params

    def format_unary_operator(self, expr) -> Tuple[str, Tuple]:
        """Format a :class:`~...expression.operators.UnaryExpression`."""
        operand_sql, operand_params = expr.operand.to_sql()
        if expr.pos == "before":
            return f"{expr.op} {operand_sql}", operand_params
        return f"{operand_sql} {expr.op}", operand_params

    def format_binary_arithmetic_expression(self, expr) -> Tuple[str, Tuple]:
        """Format a :class:`~...expression.operators.BinaryArithmeticExpression`.

        Parenthesization follows the operator-precedence table carried on the
        expression class (``OPERATOR_PRECEDENCE``).
        """
        left_sql, left_params = expr.left.to_sql()
        right_sql, right_params = expr.right.to_sql()

        current_precedence = expr.OPERATOR_PRECEDENCE.get(expr.op, 0)
        if self._needs_parens(expr.left, current_precedence):
            left_sql = f"({left_sql})"
        if self._needs_parens(expr.right, current_precedence):
            right_sql = f"({right_sql})"

        sql = f"{left_sql} {expr.op} {right_sql}"
        params = left_params + right_params
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, params

    def _needs_parens(self, operand, current_precedence):
        """Check if an arithmetic operand needs parentheses based on precedence."""
        from ...expression.operators import BinaryArithmeticExpression

        if isinstance(operand, BinaryArithmeticExpression):
            return operand.OPERATOR_PRECEDENCE.get(operand.op, 0) < current_precedence
        return False

    def format_raw_sql(self, expr) -> Tuple[str, Tuple]:
        """Format a :class:`~...expression.operators.RawSQLExpression` / ``RawSQLPredicate``.

        The raw SQL text is embedded verbatim together with its parameters —
        it bypasses the building mechanism by design and is the caller's
        responsibility to keep safe.
        """
        return expr.expression, expr.params

    def format_subquery(self, expr) -> Tuple[str, Tuple]:
        """Format a :class:`~...expression.core.Subquery` (parenthesized query)."""
        sql = f"({expr.query_input})"
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, expr.query_params

    def format_alias(self, expression_sql: str, alias: str, expression_params: tuple) -> Tuple[str, Tuple]:
        return f"{expression_sql} AS {self.format_identifier(alias)}", expression_params

    def format_values_expression(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        """Format a :class:`~...expression.query_sources.ValuesExpression` node."""
        values = expr.values
        alias = expr.alias
        column_names = expr.column_names
        all_params: List[Any] = []
        rows_sql = []
        for row in values:
            placeholders = ", ".join([self.get_parameter_placeholder()] * len(row))
            rows_sql.append(f"({placeholders})")
            all_params.extend(row)
        values_sql = ", ".join(rows_sql)
        cols_sql = ""
        if column_names:
            cols_sql = f"({', '.join(self.format_identifier(name) for name in column_names)})"
        if alias is not None:
            sql = f"(VALUES {values_sql}) AS {self.format_identifier(alias)}{cols_sql}"
        else:
            sql = f"VALUES {values_sql}{cols_sql}"
        return sql, tuple(all_params)

    def format_case_expression(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        """Format a :class:`~...expression.advanced_functions.CaseExpression` node."""
        value_sql = value_params = None
        if expr.value is not None:
            value_sql, value_params = expr.value.to_sql()
        all_params = list(value_params) if value_params else []
        if not expr.cases:
            raise ValueError("CASE expression must have at least one WHEN/THEN condition-result pair.")
        parts = ["CASE"]
        if value_sql:
            parts.append(value_sql)
        for condition, result in expr.cases:
            condition_sql, condition_params = condition.to_sql()
            result_sql, result_params = result.to_sql()
            parts.append(f"WHEN {condition_sql} THEN {result_sql}")
            all_params.extend(condition_params)
            all_params.extend(result_params)
        if expr.else_result is not None:
            else_result_sql, else_result_params = expr.else_result.to_sql()
            parts.append(f"ELSE {else_result_sql}")
            all_params.extend(else_result_params)
        parts.append("END")
        case_sql = " ".join(parts)
        if expr.alias:
            case_sql = f"{case_sql} AS {self.format_identifier(expr.alias)}"
        return case_sql, tuple(all_params)

# src/rhosocial/activerecord/backend/dialect/mixins/expression.py
from typing import Any, List, Optional, Tuple

from ...expression import bases
from ...expression.bases import BaseExpression


class ExpressionMixin:
    """Mixin for general expression formatting (operators, functions, CAST, CASE, etc.)."""

    def _apply_value_expression_modifiers(
        self, sql: str, params: Tuple, expr: "bases.SQLValueExpression"
    ) -> Tuple[str, Tuple]:
        for target_type in expr.cast_types:
            sql, params = self.format_cast_expression(sql, target_type, params, None)
        if getattr(expr, "alias", None):
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, params

    def format_function_call(
        self, expr: "bases.BaseExpression", filter_predicate: Optional["bases.SQLPredicate"] = None
    ) -> Tuple[str, Tuple]:
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

        if filter_predicate:
            if isinstance(self, FilterClauseSupport) and isinstance(self, FilterClauseMixin):
                if self.supports_filter_clause():
                    filter_sql, filter_params = filter_predicate.to_sql()
                    filter_clause_sql, filter_clause_params = self.format_filter_clause(filter_sql, filter_params)
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

        if expr.cast_types:
            for target_type in expr.cast_types:
                func_call_sql, all_params_tuple = self.format_cast_expression(
                    func_call_sql, target_type, tuple(all_params), None
                )
                all_params = list(all_params_tuple)

        if expr.alias:
            func_call_sql = f"{func_call_sql} AS {self.format_identifier(expr.alias)}"

        return func_call_sql, tuple(all_params)

    def format_binary_operator(
        self, op: str, left_sql: str, right_sql: str, left_params: tuple, right_params: tuple
    ) -> Tuple[str, Tuple]:
        return f"{left_sql} {op} {right_sql}", left_params + right_params

    def format_unary_operator(self, op: str, operand_sql: str, pos: str, operand_params: tuple) -> Tuple[str, Tuple]:
        if pos == "before":
            return f"{op} {operand_sql}", operand_params
        return f"{operand_sql} {op}", operand_params

    def format_binary_arithmetic_expression(
        self, op: str, left_sql: str, right_sql: str, left_params: tuple, right_params: tuple
    ) -> Tuple[str, Tuple]:
        return f"{left_sql} {op} {right_sql}", left_params + right_params

    def format_cast_expression(
        self, expr_sql: str, target_type: str, expr_params: tuple, alias: Optional[str] = None
    ) -> Tuple[str, Tuple]:
        from ...dialect.base import SQLDialectBase
        if not SQLDialectBase._validate_data_type(target_type):
            raise ValueError(
                f"Invalid target type '{target_type}': "
                "must contain only alphanumeric characters, spaces, parentheses, and commas."
            )
        sql = f"CAST({expr_sql} AS {target_type})"
        if alias:
            sql = f"{sql} AS {self.format_identifier(alias)}"
        return sql, expr_params

    def format_subquery(self, subquery_sql: str, subquery_params: tuple, alias: str) -> Tuple[str, Tuple]:
        return f"{subquery_sql} AS {self.format_identifier(alias)}", subquery_params

    def format_alias(self, expression_sql: str, alias: str, expression_params: tuple) -> Tuple[str, Tuple]:
        return f"{expression_sql} AS {self.format_identifier(alias)}", expression_params

    def format_values_expression(
        self, values: List[Tuple[Any, ...]], alias: Optional[str], column_names: Optional[List[str]]
    ) -> Tuple[str, Tuple]:
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

    def format_case_expression(
        self,
        value_sql: Optional[str],
        value_params: Optional[tuple],
        conditions_results: List[Tuple[str, str, tuple, tuple]],
        else_result_sql: Optional[str],
        else_result_params: Optional[tuple],
        alias: Optional[str] = None,
    ) -> Tuple[str, Tuple]:
        all_params = list(value_params) if value_params else []
        if not conditions_results:
            raise ValueError("CASE expression must have at least one WHEN/THEN condition-result pair.")
        parts = ["CASE"]
        if value_sql:
            parts.append(value_sql)
        for condition_sql, result_sql, condition_params, result_params in conditions_results:
            parts.append(f"WHEN {condition_sql} THEN {result_sql}")
            all_params.extend(condition_params)
            all_params.extend(result_params)
        if else_result_sql:
            parts.append(f"ELSE {else_result_sql}")
            all_params.extend(else_result_params)
        parts.append("END")
        case_sql = " ".join(parts)
        if alias:
            case_sql = f"{case_sql} AS {self.format_identifier(alias)}"
        return case_sql, tuple(all_params)

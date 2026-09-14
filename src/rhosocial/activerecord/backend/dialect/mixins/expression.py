# src/rhosocial/activerecord/backend/dialect/mixins/expression.py
"""Expression formatting mixin.

Renders query expression tree nodes - identifiers, literals, operators,
casts, CASE, subqueries, VALUES and aliases - to ``(sql, params)`` pairs.
Function-call rendering is inherited from :class:`FunctionCallMixin`.
"""
from typing import Any, List, Tuple

from ...expression import bases
from ...expression.core import (
    CastExpression,
    QualifiedIdentifierExpression,
    Subquery,
    WildcardExpression,
)
from ...expression.literals import Identifier
from ...expression.operators import (
    BinaryArithmeticExpression,
    BinaryExpression,
    RawSQLExpression,
    SQLOperation,
    UnaryExpression,
)
from .function import FunctionCallMixin


class ExpressionMixin(FunctionCallMixin):
    """Format expression tree nodes (columns, tables, functions, operators, etc.).

    Function-call formatting is provided by :class:`FunctionCallMixin`.
    """

    def format_identifier_expression(self, expr: Identifier) -> Tuple[str, tuple]:
        """Format an :class:`~...expression.literals.Identifier` node.

        Args:
            expr: Identifier expression exposing ``name`` and
                ``name_need_quote``.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is empty.
        """
        return self.format_identifier(expr.name, expr.name_need_quote), ()

    def format_wildcard(self, expr: WildcardExpression) -> Tuple[str, tuple]:
        """Format a :class:`~...expression.core.WildcardExpression`.

        Args:
            expr: Wildcard expression optionally carrying a table and schema.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is empty.
        """
        if expr.schema_name and expr.table:
            wildcard_sql = (
                f"{self.format_identifier(expr.schema_name, expr.schema_need_quote)}."
                f"{self.format_identifier(expr.table, expr.table_need_quote)}.*"
            )
        elif expr.table:
            wildcard_sql = f"{self.format_identifier(expr.table, expr.table_need_quote)}.*"
        else:
            wildcard_sql = "*"
        return wildcard_sql, ()

    def format_qualified_identifier(self, expr: QualifiedIdentifierExpression) -> Tuple[str, tuple]:
        """Format a :class:`~...expression.core.QualifiedIdentifierExpression`.

        Args:
            expr: Qualified identifier optionally carrying a schema.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is empty.
        """
        if expr.schema:
            return (
                f"{self.format_identifier(expr.schema, expr.schema_need_quote)}."
                f"{self.format_identifier(expr.name, expr.name_need_quote)}",
                (),
            )
        return self.format_identifier(expr.name, expr.name_need_quote), ()

    def format_literal_expression(self, expr: "bases.SQLValueExpression") -> Tuple[str, tuple]:
        """Format a :class:`~...expression.core.Literal`.

        Args:
            expr: Literal expression exposing ``inline_literals``, ``value``
                and optional ``alias``.

        Returns:
            A ``(sql, params)`` tuple; ``params`` holds the literal value when
            it is rendered as a bind parameter, otherwise it is empty.

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

    def format_cast_expression(self, expr: CastExpression) -> Tuple[str, tuple]:
        """Format a :class:`~...expression.core.CastExpression` node.

        Args:
            expr: Cast expression exposing ``expression``, ``target_type`` and
                optional ``alias``.

        Returns:
            A ``(sql, params)`` tuple carrying the wrapped expression's
            parameters.

        Raises:
            ValueError: If ``target_type`` contains unsupported characters.

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

    def format_sql_operation(self, expr: SQLOperation) -> Tuple[str, tuple]:
        """Format a :class:`~...expression.operators.SQLOperation` (n-ary).

        Args:
            expr: SQL operation exposing ``op`` and ``operands``.

        Returns:
            A ``(sql, params)`` tuple of ``op(arg, ...)``; ``params`` is the
            concatenation of the operands' parameters.
        """
        formatted_operands_sql = []
        params: List[Any] = []
        for operand in expr.operands:
            operand_sql, operand_params = operand.to_sql()
            formatted_operands_sql.append(operand_sql)
            params.extend(operand_params)
        if expr.operands:
            return f"{expr.op}({', '.join(formatted_operands_sql)})", tuple(params)
        return f"{expr.op}()", tuple(params)

    def format_binary_operator(self, expr: BinaryExpression) -> Tuple[str, tuple]:
        """Format a :class:`~...expression.operators.BinaryExpression`.

        Args:
            expr: Binary expression exposing ``left``, ``op`` and ``right``.

        Returns:
            A ``(sql, params)`` tuple of ``left op right``.
        """
        left_sql, left_params = expr.left.to_sql()
        right_sql, right_params = expr.right.to_sql()
        return f"{left_sql} {expr.op} {right_sql}", left_params + right_params

    def format_unary_operator(self, expr: UnaryExpression) -> Tuple[str, tuple]:
        """Format a :class:`~...expression.operators.UnaryExpression`.

        Args:
            expr: Unary expression exposing ``operand``, ``op`` and ``pos``.

        Returns:
            A ``(sql, params)`` tuple with the operator placed before or after
            the operand according to ``pos``.
        """
        operand_sql, operand_params = expr.operand.to_sql()
        if expr.pos == "before":
            return f"{expr.op} {operand_sql}", operand_params
        return f"{operand_sql} {expr.op}", operand_params

    def format_binary_arithmetic_expression(self, expr: BinaryArithmeticExpression) -> Tuple[str, tuple]:
        """Format a :class:`~...expression.operators.BinaryArithmeticExpression`.

        Args:
            expr: Arithmetic expression exposing ``left``, ``op``, ``right``
                and optional ``alias``.

        Returns:
            A ``(sql, params)`` tuple; parentheses are inserted where dictated
            by the operator-precedence table.

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

    def format_raw_sql(self, expr: RawSQLExpression) -> Tuple[str, tuple]:
        """Format a :class:`~...expression.operators.RawSQLExpression` / ``RawSQLPredicate``.

        Args:
            expr: Raw SQL expression exposing ``expression`` and ``params``.

        Returns:
            A ``(sql, params)`` tuple of the raw SQL text and its parameters.

        The raw SQL text is embedded verbatim together with its parameters —
        it bypasses the building mechanism by design and is the caller's
        responsibility to keep safe.
        """
        return expr.expression, expr.params

    def format_subquery(self, expr: Subquery) -> Tuple[str, tuple]:
        """Format a :class:`~...expression.core.Subquery` (parenthesized query).

        Args:
            expr: Subquery exposing ``query_input``, ``query_params`` and
                optional ``alias``.

        Returns:
            A ``(sql, params)`` tuple wrapping the query in parentheses.
        """
        sql = f"({expr.query_input})"
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, expr.query_params

    def format_alias(self, expression_sql: str, alias: str, expression_params: tuple) -> Tuple[str, tuple]:
        """Attach an alias to already-formatted SQL.

        Args:
            expression_sql: The SQL text to alias.
            alias: The alias identifier to append.
            expression_params: Parameters belonging to ``expression_sql``.

        Returns:
            A ``(sql, params)`` tuple of ``<expression_sql> AS <alias>`` with
            the original parameters unchanged.
        """
        return f"{expression_sql} AS {self.format_identifier(alias)}", expression_params

    def format_values_expression(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Format a :class:`~...expression.query_sources.ValuesExpression` node.

        Args:
            expr: VALUES expression exposing ``values``, optional ``alias`` and
                optional ``column_names``.

        Returns:
            A ``(sql, params)`` tuple; each row value becomes a bind parameter.
        """
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

    def format_case_expression(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Format a :class:`~...expression.advanced_functions.CaseExpression` node.

        Args:
            expr: CASE expression exposing optional ``value``, ``cases`` (a
                list of condition/result pairs), optional ``else_result`` and
                optional ``alias``.

        Returns:
            A ``(sql, params)`` tuple of the rendered CASE expression.

        Raises:
            ValueError: If the CASE expression has no WHEN/THEN pairs.
        """
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

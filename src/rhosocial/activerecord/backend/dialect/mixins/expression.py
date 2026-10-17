# src/rhosocial/activerecord/backend/dialect/mixins/expression.py
"""Expression formatting mixin.

Renders query expression tree nodes - identifiers, literals, operators,
casts, CASE, subqueries, VALUES and aliases - to ``(sql, params)`` pairs.
Function-call rendering is inherited from :class:`FunctionCallMixin`.
"""
from typing import Any, List, Optional, Tuple

from ...expression import bases
from ...expression.core import (
    CastExpression,
    QualifiedIdentifier,
    Subquery,
    AllColumnsWildcard,
)
from ...expression.literals import Identifier
from ...expression.mixins import AliasableMixin
from ...expression.operators import (
    ArithmeticOperation,
    BinaryExpression,
    RawSQL,
    SQLOperation,
    ConcatenationOperation,
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

    def format_all_columns_wildcard(self, expr: "AllColumnsWildcard") -> Tuple[str, tuple]:
        """Format a :class:`~...expression.core.AllColumnsWildcard`.

        A bare ``*`` when no relation is set -- the surrounding clause's
        formatter decides what the expansion spans. With a relation, the
        qualifier is the spelling the query itself uses: the alias when the
        reference carries one, the relation's own qualified name otherwise.

        Args:
            expr: The all-columns wildcard being rendered.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is empty.

        Raises:
            TypeError: ``relation`` is set but is not a ``NamedRelationRef``.
        """
        relation = expr.relation
        if relation is None:
            return "*", ()
        from ...expression.sources import NamedRelationRef

        if not isinstance(relation, NamedRelationRef):
            raise TypeError(
                f"AllColumnsWildcard.relation must be a NamedRelationRef, "
                f"got {type(relation).__name__}"
            )
        if relation.alias:
            qualifier = self.format_identifier(relation.alias, relation.alias_need_quote)
        else:
            qualifier, _ = relation.relation.to_sql()
        return f"{qualifier}.*", ()

    def format_row_count_wildcard(self, expr: "RowCountWildcard") -> Tuple[str, tuple]:
        """Format a :class:`~...expression.core.RowCountWildcard`.

        The bare asterisk, and nothing else: the row-count wildcard carries
        no relation by contract.

        Args:
            expr: The row-count wildcard being rendered.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is empty.
        """
        return "*", ()

    def format_qualified_identifier(self, expr: QualifiedIdentifier) -> Tuple[str, tuple]:
        """Format a :class:`~...expression.core.QualifiedIdentifier`.

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

    def format_literal_expression(self, expr: "bases.SQLValue") -> Tuple[str, tuple]:
        """Format a literal value expression (:class:`Literal` family).

        Args:
            expr: Literal expression exposing ``value`` and optional ``alias``.

        Returns:
            A ``(sql, params)`` tuple; ``params`` holds the literal value when
            it is rendered as a bind parameter, otherwise it is empty.

        The node's **class-level** ``inline_params`` strategy decides between
        an inline (escaped, quoted) SQL atom and a bind-parameter placeholder.
        The class attribute is read off the type — never off the instance —
        so the strategy cannot be flipped per node.
        """
        if type(expr).inline_params:
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

        ``CAST(expr AS type)`` is a unary tree node; the wrapped expression
        renders through its own ``to_sql()`` and the target through
        its own ``to_sql()``.
        """
        expr_sql, params = expr.expression.to_sql()
        # The target is an expression, so it renders itself and this
        # concatenates. Interpolating it would have produced
        # `col::IntegerType()` instead of `col::INTEGER`.
        type_sql, _ = expr.target_type.to_sql()
        sql = f"CAST({expr_sql} AS {type_sql})"
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
        sql = f"{left_sql} {expr.op} {right_sql}"
        alias = expr.alias if isinstance(expr, AliasableMixin) else None
        if alias:
            sql = f"{sql} AS {self.format_identifier(alias)}"
        return sql, left_params + right_params

    def format_concatenation_operation(
        self, expr: "ConcatenationOperation"
    ) -> Tuple[str, tuple]:
        """Render a :class:`~...expression.operators.ConcatenationOperation`.

        The node states the *intent* — its kind is ``concatenation_operation``
        and it carries no operator parameter; this formatter states the
        spelling this dialect writes for that intent.

        Args:
            expr: The concatenation node exposing ``left`` and ``right``.

        Returns:
            A ``(sql, params)`` tuple.
        """
        left_sql, left_params = expr.left.to_sql()
        right_sql, right_params = expr.right.to_sql()
        function = self.string_concatenation_function()
        if function is None:
            sql = f"{left_sql} || {right_sql}"
        else:
            sql = f"{function}({left_sql}, {right_sql})"
        alias = expr.alias if isinstance(expr, AliasableMixin) else None
        if alias:
            sql = f"{sql} AS {self.format_identifier(alias)}"
        return sql, left_params + right_params

    #: The function this dialect spells concatenation with, or ``None`` for the
    #: standard's ``||``. Declared so :meth:`string_concatenation_function` can
    #: read it without asking whether it exists.
    STRING_CONCATENATION: Optional[str] = None

    def string_concatenation_function(self) -> Optional[str]:
        """Return the function name this dialect uses for concatenation.

        A dialect where ``||`` means something else declares its own by
        overriding this: MySQL, MariaDB and SQL Server read ``||`` as logical
        OR, and BigQuery does not accept it as concatenation at all.

        Declared on the mixin as ``None`` and overridden by the dialects that
        need it, which is why this reads the attribute rather than looking a
        name up: the field is part of the mixin's shape, so a checker sees it
        and no one has to ask whether a given dialect happens to carry it.

        A dialect that declares its own must be listed **before** this mixin in
        its base list, or the declaration here wins -- the same override-order
        rule as everywhere else, and the reason a backend author controls it by
        ordering rather than by a name lookup.

        A declaration that is not a string is ignored and answered as ``None``,
        which is the same as never having declared one. The value is
        interpolated straight into the statement as a function name, so there is
        nothing safe to do with a value of the wrong type: passing it on would
        put whatever the author wrote into the SQL text. Reading it as "no
        override" keeps the standard's ``||``, which is the answer a dialect
        that never declared one gets.

        Returns:
            The function name, or ``None`` to use the standard's ``||``.
        """
        declared = self.STRING_CONCATENATION
        return declared if isinstance(declared, str) else None

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

    def format_arithmetic_operation(self, expr: ArithmeticOperation) -> Tuple[str, tuple]:
        """Format a :class:`~...expression.operators.ArithmeticOperation`.

        Args:
            expr: Arithmetic operation exposing ``left``, ``op`` and ``right``.

        Returns:
            A ``(sql, params)`` tuple; parentheses are inserted where dictated
            by the operator-precedence table.

        The node's ``op`` is an operation word (``add``/``sub``/``mul``/
        ``div``/``mod``), and the rendered SQL takes the character the word
        maps to in the class's ``OPERATOR_SYMBOLS`` table. Parenthesization
        follows ``OPERATOR_PRECEDENCE``, keyed by the same words.
        """
        left_sql, left_params = expr.left.to_sql()
        right_sql, right_params = expr.right.to_sql()

        current_precedence = expr.OPERATOR_PRECEDENCE.get(expr.op, 0)
        if self._needs_parens(expr.left, current_precedence):
            left_sql = f"({left_sql})"
        if self._needs_parens(expr.right, current_precedence):
            right_sql = f"({right_sql})"

        sql = f"{left_sql} {expr.OPERATOR_SYMBOLS[expr.op]} {right_sql}"
        params = left_params + right_params
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, params

    def _needs_parens(self, operand, current_precedence):
        """Check if an arithmetic operand needs parentheses based on precedence."""
        from ...expression.operators import ArithmeticOperation

        if isinstance(operand, ArithmeticOperation):
            return operand.OPERATOR_PRECEDENCE.get(operand.op, 0) < current_precedence
        return False

    def format_raw_sql(self, expr: RawSQL) -> Tuple[str, tuple]:
        """Format a :class:`~...expression.operators.RawSQL` / ``RawSQLPredicate``.

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

    # region Ordered-Set Aggregation
    # Merged from OrderedSetAggregationMixin: WITHIN GROUP support.

    def supports_ordered_set_aggregation(self) -> bool:
        """Whether ordered-set aggregate functions are supported.

        Defaults to False; dialects that render ``WITHIN GROUP`` override this
        to return True.
        """
        return False

    def format_ordered_set_aggregation(self, aggregation: "bases.BaseExpression") -> Tuple[str, Tuple]:
        """Format an ordered-set aggregate function call.

        Args:
            aggregation: OrderedSetAggregation object to format.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted expression.

        Raises:
            UnsupportedFeatureError: If the dialect does not support ordered-set
                aggregate functions.
        """
        from ..exceptions import UnsupportedFeatureError

        if not self.supports_ordered_set_aggregation():
            raise UnsupportedFeatureError(self.name, "ordered-set aggregate functions")

        # Format function arguments
        func_args_sql, func_args_params = [], []
        for arg in aggregation.args:
            arg_sql, arg_params = arg.to_sql()
            func_args_sql.append(arg_sql)
            func_args_params.extend(arg_params)

        # Get the ORDER BY SQL from the OrderByClause object
        order_by_sql, order_by_params = aggregation.order_by.to_sql()
        sql = f"{aggregation.func_name.upper()}({', '.join(func_args_sql)}) WITHIN GROUP ({order_by_sql})"

        all_params = func_args_params + list(order_by_params)

        if aggregation.alias:
            sql = f"{sql} AS {self.format_identifier(aggregation.alias)}"

        return sql, tuple(all_params)

    # endregion Ordered-Set Aggregation

    # region Filter Clause
    # Merged from FilterClauseMixin: FILTER (WHERE ...) support.

    def supports_filter_clause(self) -> bool:
        """Whether FILTER clause on aggregate functions is supported.

        Defaults to False; dialects that support it override this.
        """
        return False

    def format_filter_clause(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        """Format a FILTER clause.

        Args:
            expr: FilterClause containing the condition.

        Returns:
            Tuple of (SQL string, parameters tuple) for the rendered clause.

        Raises:
            UnsupportedFeatureError: If FILTER clauses are unsupported.
        """
        from ..exceptions import UnsupportedFeatureError

        if not self.supports_filter_clause():
            raise UnsupportedFeatureError(self.name, "FILTER clause")

        condition_sql, condition_params = expr.condition.to_sql()
        return f"FILTER (WHERE {condition_sql})", condition_params

    # endregion Filter Clause

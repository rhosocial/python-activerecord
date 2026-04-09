# src/rhosocial/activerecord/backend/expression/advanced_functions.py
"""
Advanced SQL functions and expressions like CASE, EXISTS, ANY/ALL, Window functions,
JSON operations, and Array operations.
"""

from typing import Any, List, Optional, Union, TYPE_CHECKING, Dict

from .bases import BaseExpression, SQLPredicate, SQLQueryAndParams, SQLValueExpression
from .core import Column, Subquery
from .mixins import (
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    StringMixin,
    TypeCastingMixin,
)
from .query_parts import OrderByClause

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import SQLDialectBase


class CaseExpression(ArithmeticMixin, ComparisonMixin, SQLValueExpression):
    """Represents a CASE expression (e.g., CASE WHEN condition THEN result ELSE result END)."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        value: Optional["BaseExpression"] = None,
        cases: Optional[list] = None,
        else_result: Optional["BaseExpression"] = None,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.value = value
        self.cases = cases or []
        self.else_result = else_result
        self.alias = alias

    def to_sql(self) -> "SQLQueryAndParams":
        value_sql, value_params = self.value.to_sql() if self.value else (None, ())
        conditions_results = []
        all_params = list(value_params) if value_params else []

        # Validate that there is at least one condition-result pair for a valid CASE expression
        if not self.cases:
            raise ValueError("CASE expression must have at least one WHEN/THEN condition-result pair.")

        for condition, result in self.cases:
            condition_sql, condition_params = condition.to_sql()
            result_sql, result_params = result.to_sql()
            conditions_results.append((condition_sql, result_sql, condition_params, result_params))
            all_params.extend(condition_params)
            all_params.extend(result_params)
        else_sql, else_params = self.else_result.to_sql() if self.else_result else (None, ())
        if else_params:
            all_params.extend(else_params)
        return self.dialect.format_case_expression(
            value_sql, value_params, conditions_results, else_sql, else_params, self.alias
        )


class ExistsExpression(SQLPredicate):
    """Represents an EXISTS predicate (e.g., EXISTS(subquery))."""

    def __init__(
        self, dialect: "SQLDialectBase", subquery: Union["Subquery", "BaseExpression"], is_not: bool = False
    ):
        super().__init__(dialect)
        # Automatically wrap BaseExpression in Subquery if needed
        if isinstance(subquery, Subquery):
            self.subquery = subquery
        elif hasattr(subquery, "to_sql"):
            # Create a Subquery from BaseExpression
            self.subquery = Subquery(dialect, subquery)
        else:
            raise TypeError(f"subquery must be Subquery or BaseExpression, got {type(subquery)}")
        self.is_not = is_not

    def to_sql(self) -> "SQLQueryAndParams":
        # Delegate to the dialect's format_exists_expression method
        return self.dialect.format_exists_expression(self.subquery, self.is_not)


class AnyExpression(SQLPredicate):
    """Represents an ANY predicate (e.g., expr = ANY(array_expr) or expr > ANY(subquery))."""

    def __init__(
        self, dialect: "SQLDialectBase", expr: "BaseExpression", op: str, array_expr: "BaseExpression"
    ):
        super().__init__(dialect)
        self.expr = expr
        self.op = op
        self.array_expr = array_expr

    def to_sql(self) -> "SQLQueryAndParams":
        # Delegate to the dialect's format_any_expression method
        return self.dialect.format_any_expression(self.expr, self.op, self.array_expr)


class AllExpression(SQLPredicate):
    """Represents an ALL predicate (e.g., expr > ALL(array_expr) or expr = ALL(subquery))."""

    def __init__(
        self, dialect: "SQLDialectBase", expr: "BaseExpression", op: str, array_expr: "BaseExpression"
    ):
        super().__init__(dialect)
        self.expr = expr
        self.op = op
        self.array_expr = array_expr

    def to_sql(self) -> "SQLQueryAndParams":
        # Delegate to the dialect's format_all_expression method
        return self.dialect.format_all_expression(self.expr, self.op, self.array_expr)


class WindowFrameSpecification(BaseExpression):
    """Window frame specification (frame_type [BETWEEN start_frame AND end_frame])"""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        frame_type: str,  # 'ROWS', 'RANGE', 'GROUPS'
        start_frame: str,  # 'UNBOUNDED PRECEDING', 'N PRECEDING', 'CURRENT ROW', etc.
        end_frame: Optional[str] = None,  # 'UNBOUNDED FOLLOWING', 'N FOLLOWING', etc.
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.frame_type = frame_type
        self.start_frame = start_frame
        self.end_frame = end_frame
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> "SQLQueryAndParams":
        """Delegate to dialect for window frame formatting"""
        return self.dialect.format_window_frame_specification(self)


class WindowSpecification(BaseExpression):
    """Window specification (PARTITION BY ..., ORDER BY ..., frame)"""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        partition_by: Optional[List[Union["BaseExpression", str]]] = None,
        order_by: Optional[Union["OrderByClause", str]] = None,  # Accept only single OrderByClause or str
        frame: Optional[WindowFrameSpecification] = None,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.partition_by = partition_by or []

        # Strictly validate and process order_by parameter
        if order_by is None:
            self.order_by = None
        elif isinstance(order_by, str):
            # Convert string to OrderByClause - create a column expression from the string
            self.order_by = OrderByClause(dialect, [Column(dialect, order_by)])
        elif isinstance(order_by, OrderByClause):
            self.order_by = order_by
        else:
            raise TypeError(f"order_by must be OrderByClause or str, got {type(order_by)}")

        self.frame = frame
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> "SQLQueryAndParams":
        """Delegate to dialect for window specification formatting"""
        return self.dialect.format_window_specification(self)


class WindowDefinition(BaseExpression):
    """Named window definition (name AS window_specification)"""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        name: str,
        specification: WindowSpecification,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.name = name
        self.specification = specification
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> "SQLQueryAndParams":
        """Delegate to dialect for named window definition formatting"""
        return self.dialect.format_window_definition(self)


class WindowClause(BaseExpression):
    """Complete WINDOW clause"""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        definitions: List[WindowDefinition],
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.definitions = definitions
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> "SQLQueryAndParams":
        """Delegate to dialect for WINDOW clause formatting"""
        return self.dialect.format_window_clause(self)


class WindowFunctionCall(
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    TypeCastingMixin,
    SQLValueExpression,
):
    """
    Window function call, supporting inline window specification or named window reference
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        function_name: str,
        args: Optional[List[Union["BaseExpression", Any]]] = None,
        window_spec: Optional[Union[WindowSpecification, str]] = None,
        alias: Optional[str] = None,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.function_name = function_name
        self.args = args or []
        self.window_spec = window_spec
        self.alias = alias
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> "SQLQueryAndParams":
        """Delegate to dialect for window function call formatting"""
        return self.dialect.format_window_function_call(self)


class JSONExpression(
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    StringMixin,
    TypeCastingMixin,
    SQLValueExpression,
):
    """Represents JSON operations like json->, json->>."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        column: Union["BaseExpression", str],
        path: str,
        operation: str = "->",
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.column = column
        self.path = path
        self.operation = operation
        self.alias = alias

    def to_sql(self) -> "SQLQueryAndParams":
        # Delegate to the dialect's format_json_expression method
        return self.dialect.format_json_expression(self)


class ArrayExpression(
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    TypeCastingMixin,
    SQLValueExpression,
):
    """Represents array operations like ANY, ALL, and array access."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        operation: str,
        base_expr: Optional["BaseExpression"] = None,
        index_expr: Optional["BaseExpression"] = None,
        elements: Optional[List["BaseExpression"]] = None,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.operation = operation
        self.base_expr = base_expr
        self.index_expr = index_expr
        self.elements = elements
        self.alias = alias

    def to_sql(self) -> "SQLQueryAndParams":
        # Delegate to the dialect's format_array_expression method
        return self.dialect.format_array_expression(self)


class OrderedSetAggregation(
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    TypeCastingMixin,
    SQLValueExpression,
):
    """Represents an ordered-set aggregate function call with WITHIN GROUP (ORDER BY ...)."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        func_name: str,
        args: List["BaseExpression"],
        order_by: Union["OrderByClause", str],
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.func_name = func_name
        self.args = args

        # Strictly validate and process order_by parameter - accept OrderByClause or str
        if isinstance(order_by, str):
            self.order_by = OrderByClause(dialect, [Column(dialect, order_by)])
        elif isinstance(order_by, OrderByClause):
            self.order_by = order_by
        else:
            raise TypeError(f"order_by must be OrderByClause or str, got {type(order_by)}")

        self.alias = alias

    def to_sql(self) -> "SQLQueryAndParams":
        return self.dialect.format_ordered_set_aggregation(self)

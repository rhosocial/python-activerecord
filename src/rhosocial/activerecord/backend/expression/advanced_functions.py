# src/rhosocial/activerecord/backend/expression/advanced_functions.py
"""
Advanced SQL functions and expressions like CASE, CAST, EXISTS, ANY/ALL, Window functions,
JSON operations, and Array operations.
"""
from typing import Tuple, Any, List, Optional, Union, TYPE_CHECKING, Dict
from dataclasses import dataclass

from . import bases
from . import mixins
from . import core

# if TYPE_CHECKING:
#     from ..dialect import SQLDialectBase


class CaseExpression(mixins.ArithmeticMixin, mixins.ComparisonMixin, bases.SQLValueExpression):
    """Represents a CASE expression (e.g., CASE WHEN condition THEN result ELSE result END)."""
    def __init__(self, dialect: "SQLDialectBase",
                 value: Optional["bases.BaseExpression"] = None,
                 cases: Optional[list] = None,
                 else_result: Optional["bases.BaseExpression"] = None,
                 alias: Optional[str] = None):
        super().__init__(dialect)
        self.value = value
        self.cases = cases or []
        self.else_result = else_result
        self.alias = alias

    def to_sql(self) -> Tuple[str, tuple]:
        value_sql, value_params = self.value.to_sql() if self.value else (None, None)
        conditions_results = []
        all_params = list(value_params) if value_params else []
        for condition, result in self.cases:
            condition_sql, condition_params = condition.to_sql()
            result_sql, result_params = result.to_sql()
            conditions_results.append((condition_sql, result_sql, condition_params, result_params))
            all_params.extend(condition_params)
            all_params.extend(result_params)
        else_sql, else_params = self.else_result.to_sql() if self.else_result else (None, None)
        if else_params:
            all_params.extend(else_params)
        return self.dialect.format_case_expression(value_sql, value_params, conditions_results, else_sql, else_params, self.alias)


class CastExpression(mixins.ArithmeticMixin, mixins.ComparisonMixin, bases.SQLValueExpression):
    """Represents a CAST expression (e.g., CAST(expr AS type))."""
    def __init__(self, dialect: "SQLDialectBase", expr: "bases.BaseExpression", target_type: str):
        super().__init__(dialect)
        self.expr = expr
        self.target_type = target_type

    def to_sql(self) -> Tuple[str, tuple]:
        expr_sql, expr_params = self.expr.to_sql()
        return self.dialect.format_cast_expression(expr_sql, self.target_type, expr_params)


class ExistsExpression(mixins.LogicalMixin, bases.SQLPredicate):
    """Represents an EXISTS predicate (e.g., EXISTS(subquery))."""
    def __init__(self, dialect: "SQLDialectBase", subquery: "core.Subquery", is_not: bool = False):
        super().__init__(dialect)
        self.subquery = subquery
        self.is_not = is_not

    def to_sql(self) -> Tuple[str, tuple]:
        subquery_sql, subquery_params = self.subquery.to_sql()
        exists_clause = "NOT EXISTS" if self.is_not else "EXISTS"
        sql = f"{exists_clause} {subquery_sql}"
        return sql, subquery_params


class AnyExpression(mixins.LogicalMixin, bases.SQLPredicate):
    """Represents an ANY predicate (e.g., expr = ANY(array_expr) or expr > ANY(subquery))."""
    def __init__(self, dialect: "SQLDialectBase", expr: "bases.BaseExpression", op: str, array_expr: "bases.BaseExpression"):
        super().__init__(dialect)
        self.expr = expr
        self.op = op
        self.array_expr = array_expr

    def to_sql(self) -> Tuple[str, tuple]:
        expr_sql, expr_params = self.expr.to_sql()
        if isinstance(self.array_expr, core.Literal) and isinstance(self.array_expr.value, (list, tuple)):
            array_sql = self.dialect.get_placeholder()
            array_params = (tuple(self.array_expr.value),)
        else:
            array_sql, array_params = self.array_expr.to_sql()
        sql = f"({expr_sql} {self.op} ANY{array_sql})"
        return sql, tuple(list(expr_params) + list(array_params))


class AllExpression(mixins.LogicalMixin, bases.SQLPredicate):
    """Represents an ALL predicate (e.g., expr > ALL(array_expr) or expr = ALL(subquery))."""
    def __init__(self, dialect: "SQLDialectBase", expr: "bases.BaseExpression", op: str, array_expr: "bases.BaseExpression"):
        super().__init__(dialect)
        self.expr = expr
        self.op = op
        self.array_expr = array_expr

    def to_sql(self) -> Tuple[str, tuple]:
        expr_sql, expr_params = self.expr.to_sql()
        if isinstance(self.array_expr, core.Literal) and isinstance(self.array_expr.value, (list, tuple)):
            array_sql = self.dialect.get_placeholder()
            array_params = (tuple(self.array_expr.value),)
        else:
            array_sql, array_params = self.array_expr.to_sql()
        sql = f"({expr_sql} {self.op} ALL{array_sql})"
        return sql, tuple(list(expr_params) + list(array_params))


class WindowFrameSpecification(bases.BaseExpression):
    """Window frame specification (frame_type [BETWEEN start_frame AND end_frame])"""
    def __init__(self, dialect: "SQLDialectBase",
                 frame_type: str,  # 'ROWS', 'RANGE', 'GROUPS'
                 start_frame: str,  # 'UNBOUNDED PRECEDING', 'N PRECEDING', 'CURRENT ROW', etc.
                 end_frame: Optional[str] = None,  # 'UNBOUNDED FOLLOWING', 'N FOLLOWING', etc.
                 dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect)
        self.frame_type = frame_type
        self.start_frame = start_frame
        self.end_frame = end_frame
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> Tuple[str, tuple]:
        """Delegate to dialect for window frame formatting"""
        return self.dialect.format_window_frame_specification(self)


class WindowSpecification(bases.BaseExpression):
    """Window specification (PARTITION BY ..., ORDER BY ..., frame)"""
    def __init__(self, dialect: "SQLDialectBase",
                 partition_by: Optional[List[Union["bases.BaseExpression", str]]] = None,
                 order_by: Optional[List[Union["bases.BaseExpression", str]]] = None,  # Each element can be (expr, direction) or expr
                 frame: Optional[WindowFrameSpecification] = None,
                 dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect)
        self.partition_by = partition_by or []
        self.order_by = order_by or []
        self.frame = frame
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> Tuple[str, tuple]:
        """Delegate to dialect for window specification formatting"""
        return self.dialect.format_window_specification(self)


class WindowDefinition(bases.BaseExpression):
    """Named window definition (name AS window_specification)"""
    def __init__(self, dialect: "SQLDialectBase",
                 name: str,
                 specification: WindowSpecification,
                 dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect)
        self.name = name
        self.specification = specification
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> Tuple[str, tuple]:
        """Delegate to dialect for named window definition formatting"""
        return self.dialect.format_window_definition(self)


class WindowClause(bases.BaseExpression):
    """Complete WINDOW clause"""
    def __init__(self, dialect: "SQLDialectBase",
                 definitions: List[WindowDefinition],
                 dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect)
        self.definitions = definitions
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> Tuple[str, tuple]:
        """Delegate to dialect for WINDOW clause formatting"""
        return self.dialect.format_window_clause(self)


class WindowFunctionCall(mixins.ArithmeticMixin, mixins.ComparisonMixin, bases.SQLValueExpression):
    """
    Window function call, supporting inline window specification or named window reference
    """
    def __init__(self, dialect: "SQLDialectBase",
                 function_name: str,
                 args: Optional[List[Union["bases.BaseExpression", Any]]] = None,
                 window_spec: Optional[Union[WindowSpecification, str]] = None,  # Window spec or named window reference
                 alias: Optional[str] = None,
                 dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect)
        self.function_name = function_name
        self.args = args or []
        self.window_spec = window_spec  # Can be WindowSpecification object or str (named window reference)
        self.alias = alias
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> Tuple[str, tuple]:
        """Delegate to dialect for window function call formatting"""
        return self.dialect.format_window_function_call(self)


class JSONExpression(mixins.ArithmeticMixin, mixins.ComparisonMixin, mixins.StringMixin, bases.SQLValueExpression):
    """Represents JSON operations like json->, json->>."""
    def __init__(self, dialect: "SQLDialectBase",
                 column: Union["bases.BaseExpression", str],
                 path: str,
                 operation: str = "->"):
        super().__init__(dialect)
        self.column = column
        self.path = path
        self.operation = operation

    def to_sql(self) -> Tuple[str, tuple]:
        if isinstance(self.column, bases.BaseExpression):
            col_sql, col_params = self.column.to_sql()
        else:
            col_sql, col_params = self.dialect.format_identifier(str(self.column)), ()
        sql = f"({col_sql} {self.operation} ?)"
        return sql, col_params + (self.path,)


class ArrayExpression(mixins.ArithmeticMixin, mixins.ComparisonMixin, bases.SQLValueExpression):
    """Represents array operations like ANY, ALL, and array access."""
    def __init__(self, dialect: "SQLDialectBase",
                 operation: str,
                 base_expr: Optional["bases.BaseExpression"] = None,
                 index_expr: Optional["bases.BaseExpression"] = None,
                 elements: Optional[List["bases.BaseExpression"]] = None):
        super().__init__(dialect)
        self.operation = operation
        self.base_expr = base_expr
        self.index_expr = index_expr
        self.elements = elements

    def to_sql(self) -> Tuple[str, tuple]:
        if self.operation.upper() == "CONSTRUCTOR" and self.elements is not None:
            element_parts, all_params = [], []
            for elem in self.elements:
                elem_sql, elem_params = elem.to_sql()
                element_parts.append(elem_sql)
                all_params.extend(elem_params)
            return f"ARRAY[{', '.join(element_parts)}]", tuple(all_params)
        elif self.operation.upper() == "ACCESS" and self.base_expr and self.index_expr:
            base_sql, base_params = self.base_expr.to_sql()
            index_sql, index_params = self.index_expr.to_sql()
            return f"({base_sql}[{index_sql}])", base_params + index_params
        return "ARRAY[]", ()


class OrderedSetAggregation(mixins.ArithmeticMixin, mixins.ComparisonMixin, bases.SQLValueExpression):
    """Represents an ordered-set aggregate function call with WITHIN GROUP (ORDER BY ...)."""
    def __init__(self, dialect: "SQLDialectBase",
                 func_name: str,
                 args: List["bases.BaseExpression"],
                 order_by: List["bases.BaseExpression"],
                 alias: Optional[str] = None):
        super().__init__(dialect)
        self.func_name = func_name
        self.args = args
        self.order_by = order_by
        self.alias = alias

    def to_sql(self) -> Tuple[str, tuple]:
        func_args_sql, func_args_params = [], []
        for arg in self.args:
            arg_sql, arg_params = arg.to_sql()
            func_args_sql.append(arg_sql)
            func_args_params.extend(arg_params)
        order_by_sql, order_by_params = [], []
        for expr in self.order_by:
            expr_sql, expr_params = expr.to_sql()
            order_by_sql.append(expr_sql)
            order_by_params.extend(expr_params)
        return self.dialect.format_ordered_set_aggregation(
            self.func_name, func_args_sql, tuple(func_args_params),
            order_by_sql, tuple(order_by_params), self.alias
        )

"""SQL expression system for query building."""
from typing import Any, List, Optional, Union, Tuple


class SQLExpression:
    """Base class for SQL expressions"""

    def __init__(self, alias: Optional[str] = None):
        self.alias = alias

    def as_sql(self) -> str:
        """Convert to SQL string"""
        raise NotImplementedError()


class Column(SQLExpression):
    """Represents a column reference"""

    def __init__(self, name: str, alias: Optional[str] = None):
        super().__init__(alias)
        self.name = name

    def as_sql(self) -> str:
        if self.alias:
            return f"{self.name} as {self.alias}"
        return self.name


class AggregateExpression(SQLExpression):
    """Aggregate function expression"""

    def __init__(self, func: str, column: Union[str, SQLExpression],
                 distinct: bool = False, alias: Optional[str] = None):
        super().__init__(alias)
        self.func = func
        self.column = column if isinstance(column, SQLExpression) else Column(column)
        self.distinct = distinct

    def as_sql(self) -> str:
        col_sql = self.column.as_sql()
        distinct_sql = "DISTINCT " if self.distinct else ""
        expr = f"{self.func}({distinct_sql}{col_sql})"
        if self.alias:
            return f"{expr} as {self.alias}"
        return expr


class ArithmeticExpression(SQLExpression):
    """Arithmetic operations"""
    OPERATORS = {'+', '-', '*', '/', '%'}

    def __init__(self, left: Union[str, SQLExpression], operator: str,
                 right: Union[str, SQLExpression], alias: Optional[str] = None):
        super().__init__(alias)
        self.left = left if isinstance(left, SQLExpression) else Column(left)
        self.right = right if isinstance(right, SQLExpression) else Column(right)
        if operator not in self.OPERATORS:
            raise ValueError(f"Invalid operator: {operator}")
        self.operator = operator

    def as_sql(self) -> str:
        expr = f"{self.left.as_sql()} {self.operator} {self.right.as_sql()}"
        if self.alias:
            return f"{expr} as {self.alias}"
        return expr


class FunctionExpression(SQLExpression):
    """SQL function call"""

    def __init__(self, func: str, *args: Union[str, SQLExpression],
                 alias: Optional[str] = None):
        super().__init__(alias)
        self.func = func
        self.args = [arg if isinstance(arg, SQLExpression) else Column(arg)
                     for arg in args]

    def as_sql(self) -> str:
        args_sql = ", ".join(arg.as_sql() for arg in self.args)
        expr = f"{self.func}({args_sql})"
        if self.alias:
            return f"{expr} as {self.alias}"
        return expr


class WindowExpression(SQLExpression):
    """Window function expression"""

    def __init__(self, expr: SQLExpression,
                 partition_by: Optional[List[str]] = None,
                 order_by: Optional[List[str]] = None,
                 alias: Optional[str] = None):
        super().__init__(alias)
        self.expr = expr
        self.partition_by = partition_by
        self.order_by = order_by

    def as_sql(self) -> str:
        window_parts = []
        if self.partition_by:
            window_parts.append(f"PARTITION BY {', '.join(self.partition_by)}")
        if self.order_by:
            window_parts.append(f"ORDER BY {', '.join(self.order_by)}")

        window_sql = " ".join(window_parts)
        expr = f"{self.expr.as_sql()} OVER ({window_sql})"
        if self.alias:
            return f"{expr} as {self.alias}"
        return expr


class CaseExpression(SQLExpression):
    """CASE expression"""

    def __init__(self, conditions: List[Tuple[str, Any]],
                 else_result: Optional[Any] = None,
                 alias: Optional[str] = None):
        super().__init__(alias)
        self.conditions = conditions
        self.else_result = else_result

    def as_sql(self) -> str:
        parts = ["CASE"]
        for condition, result in self.conditions:
            parts.append(f"WHEN {condition} THEN {result}")
        if self.else_result is not None:
            parts.append(f"ELSE {self.else_result}")
        parts.append("END")
        expr = " ".join(parts)
        if self.alias:
            return f"{expr} as {self.alias}"
        return expr
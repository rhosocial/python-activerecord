# src/rhosocial/activerecord/base/expression.py
"""
This module provides classes for building and representing SQL expressions
in an object-oriented way.
"""
from typing import Any, Tuple, Union, List, Generic, TypeVar, Optional, Dict

from ..backend.expression import SQLExpression, Literal
from ..backend.dialect import SQLDialectBase

T = TypeVar("T")

class Column(SQLExpression, Generic[T]):
    """Represents a database column in an expression."""
    def __init__(self, name: str, table: Optional[str] = None):
        self.name = name
        self.table = table
    def to_sql(self, dialect: SQLDialectBase) -> Tuple[str, tuple]:
        name = dialect.format_identifier(self.name)
        if self.table:
            table = dialect.format_identifier(self.table)
            return f"{table}.{name}", ()
        return name, ()
    def __repr__(self) -> str: return f"Column({self.name!r})"

class SQLOperation(SQLExpression):
    """Represents a SQL operation, forming a node in the expression tree."""
    def __init__(self, left: SQLExpression, op: str, right: Optional[SQLExpression] = None, is_unary: bool = False, unary_pos: str = 'before'):
        self.left = left
        self.op = op.strip().upper()
        self.right = right
        self.is_unary = is_unary
        self.unary_pos = unary_pos
    def to_sql(self, dialect: SQLDialectBase) -> Tuple[str, tuple]:
        params: List[Any] = []
        left_sql, left_params = self.left.to_sql(dialect)
        params.extend(left_params)
        if self.is_unary:
            sql = f"{self.op} {left_sql}" if self.unary_pos == 'before' else f"{left_sql} {self.op}"
            return sql, tuple(params)
        if self.right is None: raise ValueError("Binary operation must have a right side")
        right_sql, right_params = self.right.to_sql(dialect)
        params.extend(right_params)
        return f"({left_sql} {self.op} {right_sql})", tuple(params)
    def __repr__(self) -> str:
        return f"SQLOperation({self.left!r}, '{self.op}', {self.right!r})" if not self.is_unary else f"SQLOperation({self.left!r}, '{self.op}')"

# --- Refactored Classes from old expression.py ---

class AggregateExpression(SQLExpression):
    """Represents an aggregate function call like COUNT(), SUM(), etc."""
    def __init__(self, func: str, column: Union[str, SQLExpression], distinct: bool = False):
        self.func = func.upper()
        self.column = column if isinstance(column, SQLExpression) else Column(column)
        self.distinct = distinct
    def to_sql(self, dialect: SQLDialectBase) -> Tuple[str, tuple]:
        col_sql, col_params = self.column.to_sql(dialect)
        distinct_sql = "DISTINCT " if self.distinct else ""
        sql = f"{self.func}({distinct_sql}{col_sql})"
        return sql, col_params
    def __repr__(self) -> str: return f"AggregateExpression('{self.func}', {self.column!r}, distinct={self.distinct})"

class FunctionExpression(SQLExpression):
    """Represents a general SQL function call."""
    def __init__(self, func: str, *args: Any):
        self.func = func
        self.args = [arg if isinstance(arg, SQLExpression) else Literal(arg) for arg in args]
    def to_sql(self, dialect: SQLDialectBase) -> Tuple[str, tuple]:
        all_params: List[Any] = []
        args_sql: List[str] = []
        for arg in self.args:
            sql_part, params_part = arg.to_sql(dialect)
            args_sql.append(sql_part)
            all_params.extend(params_part)
        sql = f"{self.func}({', '.join(args_sql)})"
        return sql, tuple(all_params)
    def __repr__(self) -> str: return f"FunctionExpression('{self.func}', *{self.args!r})"

class WindowExpression(SQLExpression):
    """Represents a window function expression like `SUM(...) OVER (...)`."""
    def __init__(self, expr: SQLExpression, partition_by: Optional[List[str]] = None, order_by: Optional[List[str]] = None, frame_spec: Optional[str] = None, window_name: Optional[str] = None):
        self.expr = expr
        self.partition_by = partition_by or []
        self.order_by = order_by or []
        self.frame_spec = frame_spec
        self.window_name = window_name
    def to_sql(self, dialect: SQLDialectBase) -> Tuple[str, tuple]:
        expr_sql, expr_params = self.expr.to_sql(dialect)
        window_parts = []
        if self.partition_by:
            partitions = ', '.join([dialect.format_identifier(p) for p in self.partition_by])
            window_parts.append(f"PARTITION BY {partitions}")
        if self.order_by:
            orders = ', '.join([dialect.format_identifier(o) for o in self.order_by])
            window_parts.append(f"ORDER BY {orders}")
        if self.frame_spec: window_parts.append(self.frame_spec)
        if window_parts:
            window_sql = f"OVER ({' '.join(window_parts)})"
        elif self.window_name:
            window_sql = f"OVER {dialect.format_identifier(self.window_name)}"
        else: window_sql = "OVER ()"
        sql = f"{expr_sql} {window_sql}"
        return sql, expr_params
    def __repr__(self) -> str: return f"WindowExpression({self.expr!r}, partition_by={self.partition_by}, order_by={self.order_by})"


class ConditionalExpression(FunctionExpression):
    """Represents SQL conditional expressions like COALESCE, NULLIF."""
    pass


class SubqueryExpression(SQLExpression):
    """Represents a subquery expression, e.g., IN (SELECT ...)."""
    def __init__(self, subquery: str, params: Optional[tuple] = None):
        self.subquery = subquery
        self.params = params or ()

    def to_sql(self, dialect: SQLDialectBase) -> Tuple[str, tuple]:
        # The subquery is treated as a raw SQL string, and its params are passed through.
        return f"({self.subquery})", self.params

    def __repr__(self) -> str:
        return f"SubqueryExpression('{self.subquery}', {self.params!r})"


class JsonExpression(SQLExpression):
    """
    Represents a JSON-specific operation.
    
    This is a simplified implementation. A full implementation would rely more
    heavily on the dialect to generate correct syntax for different backends
    (e.g., `->>` for PostgreSQL vs `JSON_UNQUOTE(JSON_EXTRACT(...))` for MySQL).
    """
    def __init__(self, column: Union[str, SQLExpression], *path_or_ops: Any):
        self.column = column if isinstance(column, SQLExpression) else Column(column)
        self.ops = []
        # This allows chaining like: JsonExpression('data', '->', 'a', '->>', 'b')
        for op in path_or_ops:
            # Operators are strings, paths/keys are literals
            if isinstance(op, str) and op in ('->', '->>', '#>', '#>>', '@>', '<@', '?', '?|', '?&'):
                self.ops.append(op)
            else:
                self.ops.append(Literal(op))

    def to_sql(self, dialect: SQLDialectBase) -> Tuple[str, tuple]:
        # This is a generic implementation, mainly for PostgreSQL syntax.
        # A real dialect would override this logic.
        sql_parts = []
        params: List[Any] = []
        
        # Start with the base column
        col_sql, col_params = self.column.to_sql(dialect)
        sql_parts.append(col_sql)
        params.extend(col_params)

        op_iter = iter(self.ops)
        for op in op_iter:
            if isinstance(op, str):
                sql_parts.append(op)
                # The next item in the iterator should be the operand
                try:
                    operand = next(op_iter)
                    operand_sql, operand_params = operand.to_sql(dialect)
                    sql_parts.append(operand_sql)
                    params.extend(operand_params)
                except StopIteration:
                    raise ValueError(f"JSON operator '{op}' expects an operand.")
            else:
                # Should not happen with the current logic, but as a fallback
                op_sql, op_params = op.to_sql(dialect)
                sql_parts.append(op_sql)
                params.extend(op_params)

        return " ".join(sql_parts), tuple(params)

    def __repr__(self) -> str:
        return f"JsonExpression({self.column!r}, *{self.ops!r})"


class GroupingSetExpression(SQLExpression):
    """
    Represents advanced grouping operations like CUBE, ROLLUP, and GROUPING SETS.
    """
    CUBE = "CUBE"
    ROLLUP = "ROLLUP"
    GROUPING_SETS = "GROUPING SETS"

    def __init__(self, group_type: str, columns: List[Union[str, List[str], SQLExpression]]):
        if group_type.upper() not in (self.CUBE, self.ROLLUP, self.GROUPING_SETS):
            raise ValueError(f"Unsupported grouping type: {group_type}")
        self.group_type = group_type.upper()
        
        self.columns = []
        for col in columns:
            if isinstance(col, SQLExpression):
                self.columns.append(col)
            elif isinstance(col, str):
                self.columns.append(Column(col))
            elif isinstance(col, (list, tuple)):
                # For GROUPING SETS, columns can be grouped in tuples/lists
                self.columns.append([Column(c) for c in col])
            else:
                raise TypeError(f"Unsupported column type in GroupingSetExpression: {type(col)}")

    def to_sql(self, dialect: SQLDialectBase) -> Tuple[str, tuple]:
        params: List[Any] = []
        
        def process_col(col):
            if isinstance(col, SQLExpression):
                sql, col_params = col.to_sql(dialect)
                params.extend(col_params)
                return sql
            return "" # Should have been converted in __init__

        if self.group_type == self.GROUPING_SETS:
            # For GROUPING SETS ( (a), (b, c) )
            set_sqls = []
            for item in self.columns:
                if isinstance(item, list):
                    group_cols = [process_col(c) for c in item]
                    set_sqls.append(f"({', '.join(group_cols)})")
                else: # Should be a single Column/SQLExpression
                    set_sqls.append(process_col(item))
            columns_sql = ", ".join(set_sqls)
        else:
            # For CUBE (a, b, c) and ROLLUP (a, b, c)
            col_sqls = [process_col(c) for c in self.columns]
            columns_sql = ", ".join(col_sqls)

        sql = f"{self.group_type}({columns_sql})"
        return sql, tuple(params)

    def __repr__(self) -> str:
        return f"GroupingSetExpression('{self.group_type}', {self.columns!r})"

class CaseExpression(SQLExpression):
    """Represents a CASE expression."""
    def __init__(self, conditions: List[Tuple[SQLExpression, Any]], else_result: Optional[Any] = None):
        self.conditions = [(cond, res if isinstance(res, SQLExpression) else Literal(res)) for cond, res in conditions]
        self.else_result = else_result if (else_result is None or isinstance(else_result, SQLExpression)) else Literal(else_result)
    def to_sql(self, dialect: SQLDialectBase) -> Tuple[str, tuple]:
        all_params: List[Any] = []
        parts = ["CASE"]
        for cond, res in self.conditions:
            cond_sql, cond_params = cond.to_sql(dialect)
            res_sql, res_params = res.to_sql(dialect)
            parts.append(f"WHEN {cond_sql} THEN {res_sql}")
            all_params.extend(cond_params)
            all_params.extend(res_params)
        if self.else_result is not None:
            else_sql, else_params = self.else_result.to_sql(dialect)
            parts.append(f"ELSE {else_sql}")
            all_params.extend(else_params)
        parts.append("END")
        return " ".join(parts), tuple(all_params)
    def __repr__(self) -> str: return f"CaseExpression({self.conditions!r}, else_result={self.else_result!r})"


class AliasedExpression(SQLExpression):
    """Wraps an expression to give it an alias."""
    def __init__(self, expr: SQLExpression, alias: str):
        self.expr = expr
        self.alias = alias

    def to_sql(self, dialect: SQLDialectBase) -> Tuple[str, tuple]:
        sql, params = self.expr.to_sql(dialect)
        aliased_sql = f"({sql}) AS {dialect.format_identifier(self.alias)}"
        return aliased_sql, params

    def __repr__(self) -> str:
        return f"AliasedExpression({self.expr!r}, alias={self.alias!r})"

# src/rhosocial/activerecord/backend/expression/advanced_functions.py
"""
Advanced SQL functions and expressions like CASE, CAST, EXISTS, ANY/ALL, Window functions,
JSON operations, and Array operations.
"""
from typing import Tuple, Any, List, Optional, Union
from .base import BaseExpression, SQLValueExpression, SQLPredicate, Literal
from .core import FunctionCall, Subquery
from ..dialect import SQLDialectBase


class CaseExpression(SQLValueExpression):
    """
    Represents a CASE expression (e.g., CASE WHEN condition THEN result ELSE result END).
    Supports both simple CASE (with value) and searched CASE (with conditions).
    """
    def __init__(self, dialect: SQLDialectBase,
                 value: Optional[BaseExpression] = None,
                 cases: Optional[list] = None,
                 else_result: Optional[BaseExpression] = None):
        """
        Initializes a CASE expression.

        Args:
            dialect: The SQL dialect instance.
            value: Optional. The value for simple CASE expression.
            cases: List of tuples (condition, result) for the WHEN clauses.
            else_result: Optional. The result for ELSE clause.
        """
        super().__init__(dialect)
        self.value = value
        self.cases = cases or []
        self.else_result = else_result

    def to_sql(self) -> Tuple[str, tuple]:
        # Process CASE value if present
        if self.value:
            value_sql, value_params = self.value.to_sql()
        else:
            value_sql, value_params = None, None

        # Process WHEN clauses
        conditions_results = []
        all_params = []
        for condition, result in self.cases:
            condition_sql, condition_params = condition.to_sql()
            result_sql, result_params = result.to_sql()
            conditions_results.append((condition_sql, result_sql, condition_params, result_params))
            all_params.extend(condition_params)
            all_params.extend(result_params)

        # Process ELSE clause if present
        if self.else_result:
            else_sql, else_params = self.else_result.to_sql()
            all_params.extend(else_params)
        else:
            else_sql, else_params = None, None

        # Delegate to dialect for CASE formatting
        return self.dialect.format_case_expression(value_sql, value_params, conditions_results, else_sql, else_params)


class CastExpression(SQLValueExpression):
    """
    Represents a CAST expression (e.g., CAST(expr AS type)).
    """
    def __init__(self, dialect: SQLDialectBase, expr: BaseExpression, target_type: str):
        """
        Initializes a CAST expression.

        Args:
            dialect: The SQL dialect instance.
            expr: The expression to cast.
            target_type: The target SQL type as string (e.g., "INTEGER", "VARCHAR(255)").
        """
        super().__init__(dialect)
        self.expr = expr
        self.target_type = target_type

    def to_sql(self) -> Tuple[str, tuple]:
        expr_sql, expr_params = self.expr.to_sql()

        # Delegate to dialect for CAST formatting
        return self.dialect.format_cast_expression(expr_sql, self.target_type, expr_params)


class ExistsExpression(SQLPredicate):
    """
    Represents an EXISTS predicate (e.g., EXISTS(subquery)).
    """
    def __init__(self, dialect: SQLDialectBase, subquery: Subquery, is_not: bool = False):
        """
        Initializes an EXISTS predicate.

        Args:
            dialect: The SQL dialect instance.
            subquery: The subquery to check existence for.
            is_not: If True, formats as NOT EXISTS.
        """
        super().__init__(dialect)
        self.subquery = subquery
        self.is_not = is_not

    def to_sql(self) -> Tuple[str, tuple]:
        subquery_sql, subquery_params = self.subquery.to_sql()

        exists_clause = "NOT EXISTS" if self.is_not else "EXISTS"
        sql = f"{exists_clause} ({subquery_sql})"

        return sql, subquery_params


class AnyExpression(SQLPredicate):
    """
    Represents an ANY predicate (e.g., expr = ANY(array_expr) or expr > ANY(subquery)).
    """
    def __init__(self, dialect: SQLDialectBase, expr: BaseExpression, op: str, array_expr: BaseExpression):
        """
        Initializes an ANY expression.

        Args:
            dialect: The SQL dialect instance.
            expr: The expression to compare.
            op: The comparison operator (e.g., "=", ">", "<").
            array_expr: The array or subquery to compare against.
        """
        super().__init__(dialect)
        self.expr = expr
        self.op = op
        self.array_expr = array_expr

    def to_sql(self) -> Tuple[str, tuple]:
        expr_sql, expr_params = self.expr.to_sql()
        
        # Special handling for Literal lists/tuples
        if isinstance(self.array_expr, Literal) and isinstance(self.array_expr.value, (list, tuple)):
            array_sql = self.dialect.get_placeholder()
            array_params = (tuple(self.array_expr.value),) # Convert to tuple
        else:
            array_sql, array_params = self.array_expr.to_sql()

        sql = f"({expr_sql} {self.op} ANY({array_sql}))"
        params = list(expr_params)
        params.extend(array_params)
        return sql, tuple(params)


class AllExpression(SQLPredicate):
    """
    Represents an ALL predicate (e.g., expr > ALL(array_expr) or expr = ALL(subquery)).
    """
    def __init__(self, dialect: SQLDialectBase, expr: BaseExpression, op: str, array_expr: BaseExpression):
        """
        Initializes an ALL expression.

        Args:
            dialect: The SQL dialect instance.
            expr: The expression to compare.
            op: The comparison operator (e.g., "=", ">", "<").
            array_expr: The array or subquery to compare against.
        """
        super().__init__(dialect)
        self.expr = expr
        self.op = op
        self.array_expr = array_expr

    def to_sql(self) -> Tuple[str, tuple]:
        expr_sql, expr_params = self.expr.to_sql()

        # Special handling for Literal lists/tuples
        if isinstance(self.array_expr, Literal) and isinstance(self.array_expr.value, (list, tuple)):
            array_sql = self.dialect.get_placeholder()
            array_params = (tuple(self.array_expr.value),) # Convert to tuple
        else:
            array_sql, array_params = self.array_expr.to_sql()

        sql = f"({expr_sql} {self.op} ALL({array_sql}))"
        params = list(expr_params)
        params.extend(array_params)
        return sql, tuple(params)


class WindowExpression(SQLValueExpression):
    """
    Represents a window function call (e.g., ROW_NUMBER() OVER (PARTITION BY col ORDER BY col2)).
    """
    def __init__(self, dialect: SQLDialectBase,
                 function_call: FunctionCall,
                 partition_by: Optional[List[Union[BaseExpression, str]]] = None,
                 order_by: Optional[List[Union[BaseExpression, str]]] = None,
                 frame_type: Optional[str] = None,
                 frame_start: Optional[str] = None,
                 frame_end: Optional[str] = None,
                 alias: Optional[str] = None):
        """
        Initializes a window function expression.

        Args:
            dialect: The SQL dialect instance.
            function_call: The function call to be used as window function.
            partition_by: List of expressions for PARTITION BY clause.
            order_by: List of expressions for ORDER BY clause.
            frame_type: Type of frame ('ROWS', 'RANGE', 'GROUPS').
            frame_start: Start of frame definition.
            frame_end: End of frame definition.
            alias: Optional. The alias for the window expression result.
        """
        super().__init__(dialect)
        self.function_call = function_call
        self.partition_by = partition_by or []
        self.order_by = order_by or []
        self.frame_type = frame_type
        self.frame_start = frame_start
        self.frame_end = frame_end
        self.alias = alias

    def to_sql(self) -> Tuple[str, tuple]:
        # Get function call SQL
        func_sql, func_params = self.function_call.to_sql()

        # Build WINDOW clause components
        over_parts = []

        # Partition by
        all_params = list(func_params) # Initialize with function params
        if self.partition_by:
            partition_parts = []
            for part in self.partition_by:
                if isinstance(part, BaseExpression):
                    part_sql, part_param = part.to_sql()
                    partition_parts.append(part_sql)
                    all_params.extend(part_param)
                else:
                    partition_parts.append(str(part))
            over_parts.append("PARTITION BY " + ", ".join(partition_parts))

        # Order by
        if self.order_by:
            order_parts = []
            for order in self.order_by:
                if isinstance(order, BaseExpression):
                    order_sql, order_param = order.to_sql()
                    order_parts.append(order_sql)
                    all_params.extend(order_param)
                else:
                    order_parts.append(str(order))
            over_parts.append("ORDER BY " + ", ".join(order_parts))

        # Frame specification
        if self.frame_type:
            frame_parts = [self.frame_type]
            if self.frame_start and self.frame_end:
                frame_parts.append(f"BETWEEN {self.frame_start} AND {self.frame_end}")
            elif self.frame_start:
                frame_parts.append(self.frame_start)
            # else: no frame_start but frame_end exists alone, which is usually invalid or implies a default.
            over_parts.append(" ".join(frame_parts))

        sql = f"{func_sql} OVER ({' '.join(over_parts)})"
        
        if self.alias:
            sql = f"{sql} AS {self.dialect.format_identifier(self.alias)}"

        return sql, tuple(all_params)


class JSONExpression(BaseExpression):
    """
    Represents JSON operations like json->, json->> in PostgreSQL or other JSON functions.
    """
    def __init__(self, dialect: SQLDialectBase,
                 column: Union[BaseExpression, str],
                 path: str,
                 operation: str = "->"):  # "->" for JSON object access, "->>" for text
        """
        Initializes a JSON expression.

        Args:
            dialect: The SQL dialect instance.
            column: The column containing JSON data.
            path: The JSON path to access.
            operation: The JSON operation type.
        """
        super().__init__(dialect)
        self.column = column
        self.path = path
        self.operation = operation

    def to_sql(self) -> Tuple[str, tuple]:
        if isinstance(self.column, BaseExpression):
            col_sql, col_params = self.column.to_sql()
        else:
            col_sql = self.dialect.format_identifier(self.column)
            col_params = ()

        # Format JSON path access: column->'path' or column->>'path'
        sql = f"({col_sql} {self.operation} ?)"
        params = col_params + (self.path,)

        return sql, params


class ArrayExpression(BaseExpression):
    """
    Represents array operations like ANY, ALL, and array access.
    """
    def __init__(self, dialect: SQLDialectBase,
                 operation: str,  # "ACCESS" for array access [n], "CONSTRUCTOR" for array creation, etc.
                 base_expr: Optional[BaseExpression] = None,
                 index_expr: Optional[BaseExpression] = None,
                 elements: Optional[List[BaseExpression]] = None):
        """
        Initializes an array expression.

        Args:
            dialect: The SQL dialect instance.
            operation: The array operation type.
            base_expr: The base array expression (for access operations).
            index_expr: The index expression (for access operations).
            elements: List of elements (for constructor operations).
        """
        super().__init__(dialect)
        self.operation = operation
        self.base_expr = base_expr
        self.index_expr = index_expr
        self.elements = elements

    def to_sql(self) -> Tuple[str, tuple]:
        if self.operation.upper() == "CONSTRUCTOR":
            # Array constructor like ARRAY[1, 2, 3]
            element_parts = []
            all_params: List[Any] = []
            for elem in self.elements if self.elements is not None else []:
                elem_sql, elem_params = elem.to_sql()
                element_parts.append(elem_sql)
                all_params.extend(elem_params)
            sql = f"ARRAY[{', '.join(element_parts)}]"
            return sql, tuple(all_params)

        elif self.operation.upper() == "ACCESS" and self.base_expr and self.index_expr:
            # Array access like array[expression]
            base_sql, base_params = self.base_expr.to_sql()
            index_sql, index_params = self.index_expr.to_sql()
            sql = f"({base_sql}[{index_sql}])"
            return sql, base_params + index_params

        # Default fallback
        return "ARRAY[]", ()


class OrderedSetAggregation(SQLValueExpression):
    """
    Represents an ordered-set aggregate function call with WITHIN GROUP (ORDER BY ...).
    Examples: PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY salary)
    """
    def __init__(self, dialect: SQLDialectBase,
                 func_name: str,
                 args: List[BaseExpression],
                 order_by: List[BaseExpression],
                 alias: Optional[str] = None):
        """
        Initializes an ordered-set aggregate function expression.

        Args:
            dialect: The SQL dialect instance.
            func_name: The name of the aggregate function (e.g., "PERCENTILE_CONT", "LISTAGG").
            args: Arguments for the aggregate function (e.g., 0.5 for PERCENTILE_CONT).
            order_by: List of expressions for the ORDER BY clause within WITHIN GROUP.
            alias: Optional. The alias for the expression result.
        """
        super().__init__(dialect)
        self.func_name = func_name
        self.args = args
        self.order_by = order_by
        self.alias = alias

    def to_sql(self) -> Tuple[str, tuple]:
        # Process function arguments
        func_args_sql = []
        func_args_params: List[Any] = []
        for arg in self.args:
            arg_sql, arg_params = arg.to_sql()
            func_args_sql.append(arg_sql)
            func_args_params.extend(arg_params)

        # Process ORDER BY expressions
        order_by_sql = []
        order_by_params: List[Any] = []
        for expr in self.order_by:
            expr_sql, expr_params = expr.to_sql()
            order_by_sql.append(expr_sql)
            order_by_params.extend(expr_params)

        # Delegate to dialect for formatting
        return self.dialect.format_ordered_set_aggregation(
            self.func_name,
            func_args_sql,
            tuple(func_args_params),
            order_by_sql,
            tuple(order_by_params),
            self.alias
        )


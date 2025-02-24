"""Aggregate query implementation with SQL expression support."""
import logging
from typing import List, Optional, Union, Any, Dict, Type, Tuple

from .base import BaseQueryMixin
from .expression import (
    SQLExpression, AggregateExpression,
    WindowExpression, CaseExpression
)
from ..interface import ModelT


class AggregateQueryMixin(BaseQueryMixin[ModelT]):
    """Aggregate query implementation with SQL expression capabilities.

    This mixin extends BaseQueryMixin to provide:
    - Group by and having clauses for aggregation
    - Expression-based column selection
    - Complex aggregate calculations
    - Window functions

    It inherits query building capabilities from BaseQueryMixin:
    - WHERE conditions
    - ORDER BY
    - LIMIT/OFFSET
    - Query execution
    """

    def __init__(self, model_class: Type[ModelT]):
        super().__init__(model_class)
        self._group_columns: List[str] = []
        self._having_conditions: List[Tuple[str, Tuple]] = []
        self._expressions: List[SQLExpression] = []

    def group_by(self, *columns: str) -> 'AggregateQueryMixin':
        """Add GROUP BY columns

        Args:
            *columns: Columns to group by

        Returns:
            Self for method chaining
        """
        self._group_columns.extend(columns)
        self._log(logging.DEBUG, f"Added GROUP BY columns: {columns}")
        return self

    def having(self, condition: str, params: Optional[tuple] = None) -> 'AggregateQueryMixin':
        """Add HAVING condition

        Args:
            condition: HAVING condition expression
            params: Query parameters

        Returns:
            Self for method chaining
        """
        if params is None:
            params = tuple()
        self._having_conditions.append((condition, params))
        self._log(logging.DEBUG, f"Added HAVING condition: {condition}, parameters: {params}")
        return self

    def select_expr(self, expr: SQLExpression) -> 'AggregateQueryMixin':
        """Add expression to select list

        Args:
            expr: SQL expression to select

        Returns:
            Self for method chaining
        """
        self._expressions.append(expr)
        self._log(logging.DEBUG, f"Added SELECT expression: {expr.as_sql()}")
        return self

    # Advanced expression builders
    def window(self, expr: SQLExpression,
               partition_by: Optional[List[str]] = None,
               order_by: Optional[List[str]] = None,
               alias: Optional[str] = None) -> 'AggregateQueryMixin':
        """Add window function expression

        Args:
            expr: Base expression for window function
            partition_by: PARTITION BY columns
            order_by: ORDER BY columns
            alias: Optional alias for the result

        Returns:
            Self for method chaining
        """
        window_expr = WindowExpression(expr, partition_by, order_by, alias)
        self._log(logging.DEBUG,
                  f"Added WINDOW function: {window_expr.as_sql()}",
                  extra={
                      'partition_by': partition_by,
                      'order_by': order_by
                  })
        return self.select_expr(window_expr)

    def case(self, conditions: List[Tuple[str, Any]],
             else_result: Optional[Any] = None,
             alias: Optional[str] = None) -> 'AggregateQueryMixin':
        """Add CASE expression

        Args:
            conditions: List of (condition, result) pairs
            else_result: Optional ELSE result
            alias: Optional alias for the result

        Returns:
            Self for method chaining
        """
        case_expr = CaseExpression(conditions, else_result, alias)
        self._log(logging.DEBUG,
                  f"Added CASE expression: {case_expr.as_sql()}",
                  extra={
                      'conditions': conditions,
                      'else_result': else_result
                  })
        return self.select_expr(case_expr)

    def _is_aggregate_query(self) -> bool:
        """Check if this is an aggregate query.

        Returns:
            bool: True if query contains any aggregate expressions or grouping
        """
        return bool(self._expressions or self._group_columns)

    def _execute_simple_aggregate(self, func: str, column: str,
                                distinct: bool = False) -> Optional[Any]:
        """Execute a simple aggregate function without grouping.

        This internal method handles both normal execution and explain mode for
        simple aggregate functions (COUNT, SUM, AVG, etc.).

        Args:
            func: Aggregate function name (COUNT, SUM, etc.)
            column: Column to aggregate
            distinct: Whether to use DISTINCT

        Returns:
            Optional[Any]: Single aggregate result value
            Union[str, List[Dict]]: Execution plan if explain is enabled
        """
        # Save original state
        original_select = self.select_columns
        original_exprs = self._expressions

        self._log(logging.DEBUG, f"Executing simple aggregate: {func}({column})", extra={"distinct": distinct}, offset=2)

        # Clear any existing expressions
        self._expressions = []

        # Add single aggregate expression
        expr = AggregateExpression(func, column, distinct, "result")
        self.select_columns = [expr.as_sql()]

        # Execute query
        sql, params = super().build()
        self._log(logging.INFO, f"Executing simple aggregate: {sql}, parameters: {params}", offset=2)

        # Handle explain if enabled
        if self._explain_enabled:
            return self._execute_with_explain(sql, params)

        result = self.model_class.backend().fetch_one(sql, params)

        # Restore original state
        self.select_columns = original_select
        self._expressions = original_exprs

        return result["result"] if result else None

    def _build_select(self) -> str:
        """Override _build_select to handle expressions."""
        if not self._is_aggregate_query():
            return super()._build_select()

        dialect = self.model_class.backend().dialect
        table = dialect.format_identifier(self.model_class.table_name())

        # Build select parts
        select_parts = []

        # Add group columns with proper quoting
        for col in self._group_columns:
            select_parts.append(dialect.format_identifier(col))

        # Add expressions (they handle their own formatting)
        for expr in self._expressions:
            select_parts.append(expr.as_sql())

        return f"SELECT {', '.join(select_parts)} FROM {table}"

    def _build_group_by(self) -> Tuple[Optional[str], List[Any]]:
        """Build GROUP BY and HAVING clauses."""
        if not self._group_columns and not self._having_conditions:
            return None, []

        query_parts = []
        params = []

        # Add GROUP BY
        if self._group_columns:
            dialect = self.model_class.backend().dialect
            quoted_columns = [dialect.format_identifier(col) for col in self._group_columns]
            query_parts.append(f"GROUP BY {', '.join(quoted_columns)}")

        # Add HAVING
        if self._having_conditions:
            having_parts = []
            for condition, condition_params in self._having_conditions:
                having_parts.append(condition)
                params.extend(condition_params)
            query_parts.append(f"HAVING {' AND '.join(having_parts)}")

        return " ".join(query_parts), params

    def _build_aggregate_query(self) -> Tuple[str, Tuple]:
        """Build complete aggregate query SQL and parameters.

        This method is shared by both to_sql() and aggregate() to ensure consistency.
        Follows standard SQL clause order:
        SELECT ... FROM ... [JOIN] ... WHERE ... GROUP BY ... HAVING ... ORDER BY ... LIMIT/OFFSET

        Returns:
            Tuple of (sql_query, params)
        """
        if not self._is_aggregate_query():
            return super().build()

        query_parts = [self._build_select()]
        all_params = []

        # Add JOIN clauses
        join_parts = self._build_joins()
        if join_parts:
            query_parts.extend(join_parts)

        # Add WHERE clause
        where_sql, where_params = self._build_where()
        if where_sql:
            query_parts.append(where_sql)
            all_params.extend(where_params)

        # Add GROUP BY and HAVING clauses
        group_sql, group_params = self._build_group_by()
        if group_sql:
            query_parts.append(group_sql)
            all_params.extend(group_params)

        # Add ORDER BY clause
        order_sql = self._build_order()
        if order_sql:
            query_parts.append(order_sql)

        # Add LIMIT/OFFSET clause
        limit_offset_sql = self._build_limit_offset()
        if limit_offset_sql:
            query_parts.append(limit_offset_sql)

        return " ".join(query_parts), tuple(all_params)

    def to_sql(self) -> Tuple[str, Tuple]:
        """Get complete SQL query with parameters for debugging.

        Returns:
            Tuple of (sql_query, params) where:
            - sql_query: Complete SQL string with placeholders and expressions
            - params: Tuple of parameter values

        Example:
            sql, params = query.group_by("type")\\
                              .sum("amount", "total")\\
                              .having("COUNT(*) > ?", (100,))\\
                              .to_sql()
            print(f"SQL: {sql}")
            print(f"Params: {params}")
        """
        sql, params = self._build_aggregate_query()
        self._log(logging.DEBUG, f"Generated aggregate SQL: {sql}")
        self._log(logging.DEBUG, f"SQL parameters: {params}")
        return sql, params

    # Aggregate function shortcuts
    def count(self, column: str = "*", alias: Optional[str] = None,
             distinct: bool = False) -> Union['AggregateQueryMixin', int]:
        """Add COUNT expression or execute simple count.

        This method has two behaviors:
        1. When used in aggregate query (with GROUP BY or other aggregates):
           Returns query instance with COUNT expression added
        2. When used alone:
           - In normal mode: Executes COUNT immediately and returns the result
           - In explain mode: Returns the execution plan for the COUNT query

        Args:
            column: Column to count
            alias: Optional alias for grouped results
            distinct: Whether to count distinct values

        Returns:
            Query instance for chaining if in aggregate query
            Count result if simple count
            Execution plan if explain is enabled

        Examples:
            # Simple count (immediate execution)
            total = User.query().count()

            # With execution plan
            plan = User.query()\\
                .explain()\\
                .count()

            # As part of aggregate query
            result = User.query()\\
                .group_by('type')\\
                .count('id', 'total')\\
                .explain()\\
                .aggregate()
        """
        expr = AggregateExpression("COUNT", column, distinct, alias)
        if self._is_aggregate_query():
            return self.select_expr(expr)

        # Simple count
        return self._execute_simple_aggregate("COUNT", column, distinct) or 0

    def sum(self, column: str, alias: Optional[str] = None) -> Union['AggregateQueryMixin', Optional[Union[int, float]]]:
        """Add SUM expression or execute simple sum."""
        expr = AggregateExpression("SUM", column, alias=alias)
        if self._is_aggregate_query():
            return self.select_expr(expr)
        return self._execute_simple_aggregate("SUM", column)

    def avg(self, column: str, alias: Optional[str] = None) -> Union['AggregateQueryMixin', Optional[float]]:
        """Add AVG expression or execute simple average."""
        expr = AggregateExpression("AVG", column, alias=alias)
        if self._is_aggregate_query():
            return self.select_expr(expr)
        return self._execute_simple_aggregate("AVG", column)

    def min(self, column: str, alias: Optional[str] = None) -> Union['AggregateQueryMixin', Optional[Any]]:
        """Add MIN expression or execute simple min."""
        expr = AggregateExpression("MIN", column, alias=alias)
        if self._is_aggregate_query():
            return self.select_expr(expr)
        return self._execute_simple_aggregate("MIN", column)

    def max(self, column: str, alias: Optional[str] = None) -> Union['AggregateQueryMixin', Optional[Any]]:
        """Add MAX expression or execute simple max."""
        expr = AggregateExpression("MAX", column, alias=alias)
        if self._is_aggregate_query():
            return self.select_expr(expr)
        return self._execute_simple_aggregate("MAX", column)

    def aggregate(self) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """Execute aggregate query with all configured expressions and groupings.

        Executes the query with all configured expressions and groupings.
        Inherits WHERE conditions, ORDER BY, and LIMIT/OFFSET from base query.

        If explain() has been called on the query, this method will return
        the execution plan instead of the actual results. The format of the
        plan depends on the options provided to explain().

        Returns:
            - Single dict if no GROUP BY
            - List of dicts if GROUP BY specified
            - Execution plan if explain is enabled

        Each dict contains expression results with their aliases as keys
        (in normal execution mode).

        Examples:
            # Normal execution with grouping
            result = User.query()\\
                .group_by('department')\\
                .count('id', 'total')\\
                .aggregate()

            # With execution plan
            plan = User.query()\\
                .group_by('department')\\
                .explain(type=ExplainType.QUERYPLAN)\\
                .having('COUNT(*) > ?', (100,))\\
                .aggregate()
        """
        sql, params = self._build_aggregate_query()
        self._log(logging.INFO, f"Executing aggregate query: {sql}")

        # Handle explain if enabled
        if self._explain_enabled:
            return self._execute_with_explain(sql, params)

        # Execute query
        result = self.model_class.backend().fetch_all(sql, params)

        # Return results
        return result if self._group_columns else result[0] if result else {}
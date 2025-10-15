# src/rhosocial/activerecord/query/aggregate.py
"""Enhanced aggregate query implementation with SQL expression support."""
import logging
from typing import List, Optional, Union, Any, Dict, Type, Tuple

from .base import BaseQueryMixin
from .expression import (
    SQLExpression, AggregateExpression,
    WindowExpression, CaseExpression,
    FunctionExpression, ArithmeticExpression,
    ConditionalExpression, SubqueryExpression,
    JsonExpression, GroupingSetExpression
)
from ..interface import ModelT


class AggregateQueryMixin(BaseQueryMixin[ModelT]):
    """Aggregate query implementation with SQL expression capabilities.

    This mixin extends BaseQueryMixin to provide:
    - Group by and having clauses for aggregation
    - Expression-based column selection
    - Complex aggregate calculations
    - Window functions
    - Advanced SQL expressions (CASE, subqueries, JSON, etc.)
    - SQL standard grouping operations (CUBE, ROLLUP, GROUPING SETS)

    Important SQL standard behaviors:
    - GROUP BY clauses should use original column names, not aliases
    - HAVING clauses can use aggregate functions but cannot reference column aliases
    - When using JOINs, columns should be qualified with table names to avoid ambiguity

    Examples:
        # Correct: Using original column name in GROUP BY
        User.query()\\
            .select('department as dept')\\
            .group_by('department')\\
            .aggregate()

        # Correct: Using qualified column names with JOINs
        Order.query()\\
            .join('JOIN order_items ON orders.id = order_items.order_id')\\
            .select('orders.customer_id', 'SUM(order_items.amount) as total')\\
            .group_by('orders.customer_id')\\
            .having('SUM(order_items.amount) > ?', (1000,))\\
            .aggregate()
    """

    def __init__(self, model_class: Type[ModelT]):
        super().__init__(model_class)
        self._group_columns: List[str] = []
        self._having_conditions: List[Tuple[str, Tuple]] = []
        self._expressions: List[SQLExpression] = []
        self._window_definitions: Dict[str, Dict] = {}  # Named window definitions
        self._grouping_sets: Optional[GroupingSetExpression] = None

    def group_by(self, *columns: str) -> 'AggregateQueryMixin':
        """Add GROUP BY columns

        Handles various column formats:
        - Simple columns: "status"
        - Table qualified columns: "orders.status"
        - Columns with aliases: "status AS status_code" (aliases will be stripped)

        Args:
            *columns: Columns to group by

        Returns:
            Self for method chaining
        """
        for col in columns:
            # Extract base column without alias part if present
            if ' AS ' in col.upper():
                base_col = col.split(' AS ' if ' AS ' in col else ' as ')[0].strip()
                # Log warning about alias removal
                self._log(logging.WARNING,
                          f"Stripped alias from GROUP BY column: '{col}' → '{base_col}'")
            else:
                base_col = col

            self._group_columns.append(base_col)

        self._log(logging.DEBUG, f"Added GROUP BY columns: {columns}")
        return self

    def having(self, condition: str, params: Optional[tuple] = None) -> 'AggregateQueryMixin':
        """Add HAVING condition

        Args:
            condition: HAVING condition expression
            params: Query parameters

        Returns:
            Self for method chaining

        Note:
            - HAVING conditions can reference aggregate functions
            - Column aliases from SELECT cannot be used in HAVING
            - Table qualified columns (table.column) are supported
        """
        if params is None:
            params = ()

        # Check for potential alias usage in common patterns
        if " AS " in condition.upper() or " as " in condition:
            self._log(logging.WARNING,
                      "HAVING condition contains 'AS' which might indicate alias usage. "
                      "Note that column aliases cannot be used in HAVING clauses.",
                      extra={"condition": condition})

        self._having_conditions.append((condition, params))
        self._log(logging.DEBUG, f"Added HAVING condition: {condition}, parameters: {params}")
        return self

    def select_expr(self, expr: SQLExpression) -> 'AggregateQueryMixin':
        """Add expression to select list

        Automatically clears the default SELECT * behavior unless
        the user has explicitly selected columns.

        Args:
            expr: SQL expression to select

        Returns:
            Self for method chaining
        """
        self._expressions.append(expr)

        # Clear default SELECT * if no explicit columns were selected
        # This preserves any explicit selections the user has made
        if self.select_columns is None:
            self.select_columns = []
        elif self.select_columns == ["*"]:
            # If user has only selected "*" (not other columns), clear it
            self.select_columns = []

        self._log(logging.DEBUG, f"Added SELECT expression: {expr.as_sql()}")
        return self

    # Advanced expression builders
    def window(self, expr: SQLExpression,
               partition_by: Optional[List[str]] = None,
               order_by: Optional[List[str]] = None,
               alias: Optional[str] = None,
               frame_type: Optional[str] = None,
               frame_start: Optional[str] = None,
               frame_end: Optional[str] = None,
               exclude_option: Optional[str] = None,
               window_name: Optional[str] = None) -> 'AggregateQueryMixin':
        """Add window function expression with advanced frame specifications

        Args:
            expr: Base expression for window function
            partition_by: PARTITION BY columns
            order_by: ORDER BY columns
            alias: Optional alias for the result
            frame_type: Window frame type (ROWS/RANGE/GROUPS)
            frame_start: Frame start specification
            frame_end: Frame end specification
            exclude_option: Frame exclusion option
            window_name: Reference to a named window definition

        Returns:
            Self for method chaining
        """
        window_expr = WindowExpression(
            expr, partition_by, order_by, alias,
            frame_type, frame_start, frame_end,
            exclude_option, window_name
        )

        self._log(logging.DEBUG,
                  f"Added WINDOW function: {window_expr.as_sql()}",
                  extra={
                      'partition_by': partition_by,
                      'order_by': order_by,
                      'frame_type': frame_type
                  })
        return self.select_expr(window_expr)

    def define_window(self, name: str,
                      partition_by: Optional[List[str]] = None,
                      order_by: Optional[List[str]] = None) -> 'AggregateQueryMixin':
        """Define a named window specification for reuse

        Args:
            name: Window name
            partition_by: PARTITION BY columns
            order_by: ORDER BY columns

        Returns:
            Self for method chaining
        """
        self._window_definitions[name] = {
            'partition_by': partition_by,
            'order_by': order_by
        }
        self._log(logging.DEBUG, f"Defined named window: {name}")
        return self

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

    def function(self, func: str, *args: Union[str, SQLExpression],
                 alias: Optional[str] = None) -> 'AggregateQueryMixin':
        """Add a general SQL function expression

        Args:
            func: Function name
            *args: Function arguments
            alias: Optional alias for the result

        Returns:
            Self for method chaining
        """
        func_expr = FunctionExpression(func, *args, alias=alias)
        self._log(logging.DEBUG, f"Added function expression: {func_expr.as_sql()}")
        return self.select_expr(func_expr)

    def arithmetic(self, left: Union[str, SQLExpression],
                   operator: str,
                   right: Union[str, SQLExpression],
                   alias: Optional[str] = None) -> 'AggregateQueryMixin':
        """Add an arithmetic expression

        Args:
            left: Left operand (column or expression)
            operator: Arithmetic operator (+, -, *, /, %)
            right: Right operand (column or expression)
            alias: Optional alias for the result

        Returns:
            Self for method chaining
        """
        arith_expr = ArithmeticExpression(left, operator, right, alias)
        self._log(logging.DEBUG, f"Added arithmetic expression: {arith_expr.as_sql()}")
        return self.select_expr(arith_expr)

    def coalesce(self, *args: Union[str, SQLExpression, Any],
                 alias: Optional[str] = None) -> 'AggregateQueryMixin':
        """Add COALESCE expression to return first non-null value

        Args:
            *args: List of expressions to check
            alias: Optional alias for the result

        Returns:
            Self for method chaining
        """
        coalesce_expr = ConditionalExpression("COALESCE", *args, alias=alias)
        self._log(logging.DEBUG, f"Added COALESCE expression: {coalesce_expr.as_sql()}")
        return self.select_expr(coalesce_expr)

    def nullif(self, expr1: Union[str, SQLExpression],
               expr2: Union[str, SQLExpression, Any],
               alias: Optional[str] = None) -> 'AggregateQueryMixin':
        """Add NULLIF expression (returns NULL if expr1 = expr2)

        Args:
            expr1: First expression
            expr2: Second expression
            alias: Optional alias for the result

        Returns:
            Self for method chaining
        """
        nullif_expr = ConditionalExpression("NULLIF", expr1, expr2, alias=alias)
        self._log(logging.DEBUG, f"Added NULLIF expression: {nullif_expr.as_sql()}")
        return self.select_expr(nullif_expr)

    def subquery(self, subquery: str,
                 type: Optional[str] = None,
                 column: Optional[Union[str, SQLExpression]] = None,
                 params: Optional[tuple] = None,
                 alias: Optional[str] = None) -> 'AggregateQueryMixin':
        """Add a subquery expression

        Args:
            subquery: Subquery SQL string
            type: Subquery type (EXISTS, IN, NOT IN, ALL, ANY)
            column: Column for comparison (required for IN, ALL, ANY)
            params: Query parameters
            alias: Optional alias for the result

        Returns:
            Self for method chaining
        """
        subq_expr = SubqueryExpression(subquery, type, column, params, alias)
        self._log(logging.DEBUG, f"Added subquery expression: {subq_expr.as_sql()}")
        return self.select_expr(subq_expr)

    def json_expr(self, column: Union[str, SQLExpression],
                  path: str,
                  operation: str = "extract",
                  value: Any = None,
                  alias: Optional[str] = None) -> 'AggregateQueryMixin':
        """Add a JSON expression with specified operation.

        This is the core method for all JSON operations, providing database-agnostic
        access to JSON functionality. Other JSON methods call this method internally.

        Args:
            column: JSON column name or expression
            path: JSON path string (e.g. '$.name', '$.addresses[0].city')
            operation: Operation type (extract, contains, exists, etc.)
            value: Value for operations that need it (contains, insert, etc.)
            alias: Optional alias for the result

        Returns:
            Self for method chaining

        Example:
            User.query()\
                .json_expr('settings', '$.theme', 'extract', alias='theme_setting')\
                .where('active = ?', (True,))\
                .all()

        Raises:
            JsonOperationNotSupportedError: If database doesn't support JSON operations
        """
        # Check if JSON operations are supported by the database
        if not self.model_class.backend().dialect.json_operation_handler.supports_json_operations:
            self._log(logging.WARNING, "JSON operations are not supported by the current database")

        json_expr = JsonExpression(column, path, operation, value, alias)
        self._log(logging.DEBUG, f"Added JSON expression: {json_expr.as_sql()}")
        return self.select_expr(json_expr)

    def json(self, column: Union[str, SQLExpression],
             path: Optional[str] = None,
             alias: Optional[str] = None) -> 'AggregateQueryMixin':
        """Add JSON extract expression (using -> operator when available).

        This method adds an expression to extract a value from a JSON column.
        The exact SQL syntax will be determined by the database dialect.

        Args:
            column: JSON column
            path: JSON path
            alias: Optional result alias

        Returns:
            Self for method chaining

        Example:
            User.query()\
                .json('settings', '$.theme', 'user_theme')\
                .where('status = ?', ('active',))\
                .all()

        Raises:
            JsonOperationNotSupportedError: If database doesn't support JSON operations
        """
        return self.json_expr(column, path, JsonExpression.EXTRACT, alias=alias)

    def json_text(self, column: Union[str, SQLExpression],
                  path: Optional[str] = None,
                  alias: Optional[str] = None) -> 'AggregateQueryMixin':
        """Add JSON extract as text expression (using ->> operator when available).

        This method adds an expression to extract a value from a JSON column as text.
        The exact SQL syntax will be determined by the database dialect.

        Args:
            column: JSON column
            path: JSON path
            alias: Optional result alias

        Returns:
            Self for method chaining

        Example:
            User.query()\
                .json_text('settings', '$.theme', 'user_theme')\
                .where('status = ?', ('active',))\
                .all()

        Raises:
            JsonOperationNotSupportedError: If database doesn't support JSON operations
        """
        return self.json_expr(column, path, JsonExpression.EXTRACT_TEXT, alias=alias)

    def json_type(self, column: Union[str, SQLExpression],
                  path: Optional[str] = None,
                  alias: Optional[str] = None) -> 'AggregateQueryMixin':
        """Add JSON type expression.

        Gets the type of a JSON value (object, array, string, number, etc.).

        Args:
            column: JSON column
            path: JSON path
            alias: Optional result alias

        Returns:
            Self for method chaining

        Example:
            User.query()\
                .json_type('settings', '$.preferences', 'pref_type')\
                .all()

        Raises:
            JsonOperationNotSupportedError: If database doesn't support JSON operations
        """
        return self.json_expr(column, path, JsonExpression.TYPE, alias=alias)

    def json_contains(self, column: Union[str, SQLExpression],
                      path: Optional[str],
                      value: Any,
                      alias: Optional[str] = None) -> 'AggregateQueryMixin':
        """Add JSON contains expression.

        Checks if a JSON value contains a specific value.

        Note: SQLite doesn't have a native json_contains function. For SQLite backends,
        this method uses json_extract with comparison operators to simulate similar
        functionality. The exact behavior may differ from databases with native
        json_contains functions (like MySQL or PostgreSQL).

        Args:
            column: JSON column
            path: JSON path to check
            value: Value to check for
            alias: Optional result alias

        Returns:
            Self for method chaining

        Example:
            User.query()\
                .json_contains('settings', '$.roles', 'admin', 'is_admin')\
                .all()

        Raises:
            JsonOperationNotSupportedError: If database doesn't support any JSON operations
        """
        return self.json_expr(column, path, JsonExpression.CONTAINS, value, alias)

    def json_exists(self, column: Union[str, SQLExpression],
                    path: str,
                    alias: Optional[str] = None) -> 'AggregateQueryMixin':
        """Add JSON exists expression.

        Checks if a path exists in a JSON document.
        Note: Some databases like SQLite implement this through json_extract() IS NOT NULL

        Args:
            column: JSON column
            path: JSON path to check
            alias: Optional result alias

        Returns:
            Self for method chaining

        Example:
            User.query()\
                .json_exists('settings', '$.address', 'has_address')\
                .all()

        Raises:
            JsonOperationNotSupportedError: If database doesn't support JSON operations
        """
        return self.json_expr(column, path, JsonExpression.EXISTS, alias=alias)

    def json_set(self, column: Union[str, SQLExpression],
                 path: str, value: Any,
                 alias: Optional[str] = None) -> 'AggregateQueryMixin':
        """Add JSON set expression.

        Sets a value in a JSON document (insert if not exists, replace if exists).

        Args:
            column: JSON column
            path: JSON path
            value: Value to set
            alias: Optional result alias

        Returns:
            Self for method chaining

        Example:
            User.query()\
                .json_set('settings', '$.theme', 'dark', 'updated_settings')\
                .all()

        Raises:
            JsonOperationNotSupportedError: If database doesn't support JSON operations
        """
        return self.json_expr(column, path, JsonExpression.SET, value, alias)

    def json_insert(self, column: Union[str, SQLExpression],
                    path: str, value: Any,
                    alias: Optional[str] = None) -> 'AggregateQueryMixin':
        """Add JSON insert expression (only inserts if path doesn't exist).

        Args:
            column: JSON column
            path: JSON path
            value: Value to insert
            alias: Optional result alias

        Returns:
            Self for method chaining

        Example:
            User.query()\
                .json_insert('settings', '$.new_field', 'value', 'inserted_settings')\
                .all()

        Raises:
            JsonOperationNotSupportedError: If database doesn't support JSON operations
        """
        return self.json_expr(column, path, JsonExpression.INSERT, value, alias)

    def json_replace(self, column: Union[str, SQLExpression],
                     path: str, value: Any,
                     alias: Optional[str] = None) -> 'AggregateQueryMixin':
        """Add JSON replace expression (only replaces if path exists).

        Args:
            column: JSON column
            path: JSON path
            value: Value to replace with
            alias: Optional result alias

        Returns:
            Self for method chaining

        Example:
            User.query()\
                .json_replace('settings', '$.theme', 'light', 'replaced_settings')\
                .all()

        Raises:
            JsonOperationNotSupportedError: If database doesn't support JSON operations
        """
        return self.json_expr(column, path, JsonExpression.REPLACE, value, alias)

    def json_remove(self, column: Union[str, SQLExpression],
                    path: str,
                    alias: Optional[str] = None) -> 'AggregateQueryMixin':
        """Add JSON remove expression.

        Args:
            column: JSON column
            path: JSON path to remove
            alias: Optional result alias

        Returns:
            Self for method chaining

        Example:
            User.query()\
                .json_remove('settings', '$.theme', 'removed_settings')\
                .all()

        Raises:
            JsonOperationNotSupportedError: If database doesn't support JSON operations
        """
        return self.json_expr(column, path, JsonExpression.REMOVE, alias=alias)

    def cube(self, *columns: str) -> 'AggregateQueryMixin':
        """Add CUBE grouping for multi-dimensional analysis

        Args:
            *columns: Columns to include in CUBE

        Returns:
            Self for method chaining
        """
        self._grouping_sets = GroupingSetExpression(
            GroupingSetExpression.CUBE,
            list(columns)
        )
        self._log(logging.DEBUG, f"Added CUBE grouping: {columns}")
        return self

    def rollup(self, *columns: str) -> 'AggregateQueryMixin':
        """Add ROLLUP grouping for hierarchical analysis

        Args:
            *columns: Columns to include in ROLLUP

        Returns:
            Self for method chaining
        """
        self._grouping_sets = GroupingSetExpression(
            GroupingSetExpression.ROLLUP,
            list(columns)
        )
        self._log(logging.DEBUG, f"Added ROLLUP grouping: {columns}")
        return self

    def grouping_sets(self, *column_groups: List[str]) -> 'AggregateQueryMixin':
        """Add GROUPING SETS for custom grouping combinations

        Args:
            *column_groups: Groups of columns for different aggregation levels

        Returns:
            Self for method chaining
        """
        self._grouping_sets = GroupingSetExpression(
            GroupingSetExpression.GROUPING_SETS,
            list(column_groups)
        )
        self._log(logging.DEBUG, f"Added GROUPING SETS: {column_groups}")
        return self

    def _is_aggregate_query(self) -> bool:
        """Check if this is an aggregate query.

        Returns:
            bool: True if query contains any aggregate expressions or grouping
        """
        return bool(self._expressions or self._group_columns or self._grouping_sets)

    def _build_scalar_aggregate_query(self, func: str, column: str,
                                      distinct: bool = False) -> Tuple[str, tuple]:
        """Build a scalar aggregate query for execution.

        This method creates an SQL query for scalar aggregate functions like COUNT, SUM, etc.
        It's designed as a hook that derived classes can override to modify query generation.

        Args:
            func: Aggregate function name (COUNT, SUM, etc.)
            column: Column to aggregate
            distinct: Whether to use DISTINCT

        Returns:
            Tuple of (sql_query, params)
        """
        # Clear any existing expressions
        self._expressions = []

        # Add single aggregate expression
        expr = AggregateExpression(func, column, distinct, "result")

        # Save original state and set new selection
        original_select = self.select_columns
        self.select_columns = [expr.as_sql()]

        # Build query
        sql, params = super().build()

        # Restore original state
        self.select_columns = original_select

        return sql, params

    def _execute_scalar_aggregate(self, func: str, column: str,
                                  distinct: bool = False) -> Optional[Any]:
        """Execute a scalar aggregate function without grouping.

        This internal method handles both normal execution and explain mode for
        scalar aggregate functions (COUNT, SUM, AVG, etc.).

        Args:
            func: Aggregate function name (COUNT, SUM, etc.)
            column: Column to aggregate
            distinct: Whether to use DISTINCT

        Returns:
            Optional[Any]: Single aggregate result value or
            Union[str, List[Dict]]: Execution plan if explain is enabled
        """
        # Save original state
        original_select = self.select_columns
        original_exprs = self._expressions

        self._log(logging.DEBUG, f"Executing scalar aggregate: {func}({column})", extra={"distinct": distinct},
                  offset=2)

        # Build the query using the hook method
        sql, params = self._build_scalar_aggregate_query(func, column, distinct)

        self._log(logging.INFO, f"Executing scalar aggregate: {sql}, parameters: {params}", offset=2)

        # Handle explain if enabled
        if self._explain_enabled:
            result = self._execute_with_explain(sql, params)

            # Restore original state
            self.select_columns = original_select
            self._expressions = original_exprs

            return result

        result = self.model_class.backend().fetch_one(sql, params)

        # Restore original state
        self.select_columns = original_select
        self._expressions = original_exprs

        return result["result"] if result else None

    def _build_select(self) -> str:
        """Override _build_select to handle expressions.

        This method builds the SELECT clause for aggregate queries.
        It includes:
        1. Explicitly selected columns from select_columns
        2. Group by columns if not already included in select_columns
        3. SQL expressions added via aggregate methods

        For non-aggregate queries, it delegates to the parent implementation.
        """
        if not self._is_aggregate_query():
            return super()._build_select()

        dialect = self.model_class.backend().dialect
        table = dialect.format_identifier(self.model_class.table_name())

        # Build select parts
        select_parts = []

        # First add explicitly selected columns from select_columns
        selected_columns = set()
        if self.select_columns:
            for col in self.select_columns:
                select_parts.append(col)
                # Extract column name for tracking (handle "column as alias" format)
                base_col = col.split(' as ')[0].strip() if ' as ' in col else col
                base_col = base_col.strip('"').strip('`')  # Remove quotes if present
                selected_columns.add(base_col)
        elif not self._expressions:  # Only use * if no expressions
            # Default SELECT *
            select_parts.append("*")

        # Add group columns with proper quoting if not already included
        for col in self._group_columns:
            # Check if column exists in expressions with same name
            col_exists_in_expr = any(
                expr.alias == col.split('.')[-1]  # Handle table.column format
                for expr in self._expressions
                if hasattr(expr, 'alias') and expr.alias
            )
            
            if col not in selected_columns and not col_exists_in_expr:
                select_parts.append(dialect.format_identifier(col))
                selected_columns.add(col)

        # Add expressions (they handle their own formatting)
        for expr in self._expressions:
            select_parts.append(expr.as_sql())

        return f"SELECT {', '.join(select_parts)} FROM {table}"

    def _build_group_by(self) -> Tuple[Optional[str], List[Any]]:
        """Build GROUP BY and HAVING clauses.

        Uses the parent class's _format_identifier method to ensure consistent
        identifier formatting across all query parts.

        Properly formats identifiers including:
        - Simple column names
        - Table qualified column names (table.column)
        - Quoted identifiers according to dialect rules
        """
        if not self._group_columns and not self._having_conditions and not self._grouping_sets:
            return None, []

        query_parts = []
        params = []

        # Add GROUP BY
        if self._group_columns or self._grouping_sets:
            if self._grouping_sets:
                # Use specialized grouping (CUBE, ROLLUP, GROUPING SETS)
                query_parts.append(f"GROUP BY {self._grouping_sets.as_sql()}")
            else:
                # Standard grouping with proper identifier quoting
                # Reuse the _format_identifier method from BaseQueryMixin
                quoted_columns = [self._format_identifier(col) for col in self._group_columns]
                query_parts.append(f"GROUP BY {', '.join(quoted_columns)}")

        # Add HAVING
        if self._having_conditions:
            having_parts = []
            for condition, condition_params in self._having_conditions:
                having_parts.append(condition)
                params.extend(condition_params)
            query_parts.append(f"HAVING {' AND '.join(having_parts)}")

        return " ".join(query_parts), params

    def _build_window_defs(self) -> Optional[str]:
        """Build WINDOW clause for named window definitions.

        Returns:
            Optional[str]: WINDOW clause or None if no definitions
        """
        if not self._window_definitions:
            return None

        window_parts = []

        for name, definition in self._window_definitions.items():
            window_spec = []

            if definition.get('partition_by'):
                window_spec.append(f"PARTITION BY {', '.join(definition['partition_by'])}")

            if definition.get('order_by'):
                window_spec.append(f"ORDER BY {', '.join(definition['order_by'])}")

            window_parts.append(f"{name} AS ({' '.join(window_spec)})")

        if window_parts:
            return f"WINDOW {', '.join(window_parts)}"

        return None

    def _build_aggregate_query(self) -> Tuple[str, Tuple]:
        """Build complete aggregate query SQL and parameters.

        This method is shared by both to_sql() and aggregate() to ensure consistency.
        Follows standard SQL clause order:
        SELECT ... FROM ... [JOIN] ... WHERE ... GROUP BY ... HAVING ... WINDOW ... ORDER BY ... LIMIT/OFFSET

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

        # Add WINDOW definitions if any
        window_sql = self._build_window_defs()
        if window_sql:
            query_parts.append(window_sql)

        # Add ORDER BY clause
        order_sql = self._build_order()
        if order_sql:
            query_parts.append(order_sql)

        # Add LIMIT/OFFSET clause
        limit_offset_sql = self._build_limit_offset()
        if limit_offset_sql:
            query_parts.append(limit_offset_sql)

        raw_sql = " ".join(query_parts)
        params = tuple(all_params)

        # Get the target database placeholder
        backend = self.model_class.backend()
        placeholder = backend.dialect.get_placeholder()

        # Only replace if the placeholder is not a question mark
        if placeholder != '?':
            # Replace all question marks with the correct placeholder
            processed_sql = super()._replace_question_marks(raw_sql, placeholder)
        else:
            processed_sql = raw_sql

        return processed_sql, params

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
        """Add COUNT expression or execute scalar count.

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
            Count result if scalar count
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
        return self._execute_scalar_aggregate("COUNT", column, distinct) or 0

    def sum(self, column: str, alias: Optional[str] = None) -> Union['AggregateQueryMixin', Optional[Union[int, float]]]:
        """Add SUM expression or execute scalar sum."""
        expr = AggregateExpression("SUM", column, alias=alias)
        if self._is_aggregate_query():
            return self.select_expr(expr)
        return self._execute_scalar_aggregate("SUM", column)

    def avg(self, column: str, alias: Optional[str] = None) -> Union['AggregateQueryMixin', Optional[float]]:
        """Add AVG expression or execute scalar average."""
        expr = AggregateExpression("AVG", column, alias=alias)
        if self._is_aggregate_query():
            return self.select_expr(expr)
        return self._execute_scalar_aggregate("AVG", column)

    def min(self, column: str, alias: Optional[str] = None) -> Union['AggregateQueryMixin', Optional[Any]]:
        """Add MIN expression or execute scalar min."""
        expr = AggregateExpression("MIN", column, alias=alias)
        if self._is_aggregate_query():
            return self.select_expr(expr)
        return self._execute_scalar_aggregate("MIN", column)

    def max(self, column: str, alias: Optional[str] = None) -> Union['AggregateQueryMixin', Optional[Any]]:
        """Add MAX expression or execute scalar max."""
        expr = AggregateExpression("MAX", column, alias=alias)
        if self._is_aggregate_query():
            return self.select_expr(expr)
        return self._execute_scalar_aggregate("MAX", column)

    def aggregate(self) -> List[Dict[str, Any]]:
        """Execute aggregate query with all configured expressions and groupings.

        Executes the query with all configured expressions and groupings.
        Inherits WHERE conditions, ORDER BY, and LIMIT/OFFSET from base query.

        Returns a list of result dictionaries. The list may contain a single item
        or multiple items depending on the query definition (GROUP BY, etc.).

        If explain() has been called on the query, this method will return
        the execution plan instead of the actual results.

        Returns:
            List[Dict[str, Any]]: Results as a list of dictionaries
            Union[str, List[Dict]]: Execution plan if explain is enabled

        Examples:
            # With grouping (returns multiple rows)
            result = User.query()\\
                .group_by('department')\\
                .count('id', 'total')\\
                .aggregate()

            # Scalar aggregate (returns a single row in a list)
            result = User.query()\\
                .count('id', 'total')\\
                .aggregate()
            total = result[0]['total'] if result else 0
        """
        sql, params = self._build_aggregate_query()
        self._log(logging.INFO, f"Executing aggregate query: {sql}")

        # Handle explain if enabled
        if self._explain_enabled:
            return self._execute_with_explain(sql, params)

        # Execute query
        result = self.model_class.backend().fetch_all(sql, params)

        # Always return a list, even if empty
        return result

    def __copy__(self):
        """Implement shallow copy protocol for aggregate queries.

        Extends the BaseQueryMixin.__copy__ implementation to include
        aggregate-specific properties.

        Returns:
            A new instance of the aggregate query with properties copied.
        """
        # Start with the base copy
        result = super().__copy__()

        # Copy aggregate-specific properties
        if hasattr(self, '_group_columns'):
            result._group_columns = self._group_columns.copy()
        else:
            result._group_columns = []

        if hasattr(self, '_having_conditions'):
            result._having_conditions = self._having_conditions.copy()
        else:
            result._having_conditions = []

        if hasattr(self, '_expressions'):
            # Note: Expressions might need deep copying,
            # but we'll handle it in __deepcopy__
            result._expressions = self._expressions.copy() if self._expressions else []
        else:
            result._expressions = []

        if hasattr(self, '_window_definitions'):
            # Shallow copy of the window definitions dict
            result._window_definitions = self._window_definitions.copy() if self._window_definitions else {}
        else:
            result._window_definitions = {}

        # For _grouping_sets, we'll just do a reference copy here
        # and handle deep copying in __deepcopy__
        if hasattr(self, '_grouping_sets'):
            result._grouping_sets = self._grouping_sets
        else:
            result._grouping_sets = None

        return result

    def __deepcopy__(self, memo):
        """Implement deep copy protocol for aggregate queries.

        Extends the BaseQueryMixin.__deepcopy__ implementation to ensure
        all aggregate-specific nested objects are also deeply copied.

        Args:
            memo: Dictionary of already copied objects to avoid infinite recursion

        Returns:
            A completely independent copy of the aggregate query
        """
        import copy

        # If this object has already been copied, return the copy
        if id(self) in memo:
            return memo[id(self)]

        # Start with a shallow copy
        result = self.__copy__()

        # Track the copied object to avoid infinite recursion
        memo[id(self)] = result

        # Call parent's __deepcopy__ to handle base properties
        super().__deepcopy__(memo)

        # Deep copy complex objects
        if hasattr(self, '_expressions') and self._expressions:
            result._expressions = copy.deepcopy(self._expressions, memo)

        if hasattr(self, '_window_definitions') and self._window_definitions:
            result._window_definitions = copy.deepcopy(self._window_definitions, memo)

        if hasattr(self, '_grouping_sets') and self._grouping_sets:
            result._grouping_sets = copy.deepcopy(self._grouping_sets, memo)

        return result
# src/rhosocial/activerecord/query/expression.py
"""Enhanced SQL expression system for query building."""
from typing import Any, List, Optional, Union, Tuple, Dict


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
    """Window function expression with enhanced frame specifications"""

    # Frame types
    ROWS = "ROWS"
    RANGE = "RANGE"
    GROUPS = "GROUPS"  # SQL:2011 feature

    # Frame bounds
    CURRENT_ROW = "CURRENT ROW"
    UNBOUNDED_PRECEDING = "UNBOUNDED PRECEDING"
    UNBOUNDED_FOLLOWING = "UNBOUNDED FOLLOWING"

    # Exclude options (SQL:2011 feature)
    EXCLUDE_NONE = "EXCLUDE NO OTHERS"
    EXCLUDE_CURRENT_ROW = "EXCLUDE CURRENT ROW"
    EXCLUDE_GROUP = "EXCLUDE GROUP"
    EXCLUDE_TIES = "EXCLUDE TIES"

    def __init__(self, expr: SQLExpression,
                 partition_by: Optional[List[str]] = None,
                 order_by: Optional[List[str]] = None,
                 alias: Optional[str] = None,
                 frame_type: Optional[str] = None,
                 frame_start: Optional[str] = None,
                 frame_end: Optional[str] = None,
                 exclude_option: Optional[str] = None,
                 window_name: Optional[str] = None):
        super().__init__(alias)
        self.expr = expr
        self.partition_by = partition_by
        self.order_by = order_by
        self.frame_type = frame_type
        self.frame_start = frame_start
        self.frame_end = frame_end
        self.exclude_option = exclude_option
        self.window_name = window_name

    def expand_window_name(self, window_definitions: Dict[str, Dict]) -> str:
        """Expand a window name to its full definition if available.

        Args:
            window_definitions: Dictionary of window definitions

        Returns:
            str: Window specification or the original window name
        """
        if self.window_name not in window_definitions:
            # If window name is not defined, just return the name
            # This will likely cause a SQL error, but at least we're consistent
            return self.window_name

        definition = window_definitions[self.window_name]
        window_parts = []

        if 'partition_by' in definition and definition['partition_by']:
            window_parts.append(f"PARTITION BY {', '.join(definition['partition_by'])}")

        if 'order_by' in definition and definition['order_by']:
            window_parts.append(f"ORDER BY {', '.join(definition['order_by'])}")

        return " ".join(window_parts)

    def as_sql(self, window_definitions: Optional[Dict[str, Dict]] = None) -> str:
        """Convert to SQL string with window definitions support

        Args:
            window_definitions: Optional dictionary of window definitions to expand named windows

        Returns:
            str: SQL representation of the window expression
        """
        # If a named window is provided, use it
        if self.window_name:
            if window_definitions and self.window_name in window_definitions:
                # Expand window name to full specification if we have definitions
                window_sql = self.expand_window_name(window_definitions)
            else:
                # Just use the name (handled by WINDOW clause in query)
                window_sql = self.window_name
        else:
            # Build window specification
            window_parts = []

            if self.partition_by:
                window_parts.append(f"PARTITION BY {', '.join(self.partition_by)}")

            if self.order_by:
                window_parts.append(f"ORDER BY {', '.join(self.order_by)}")

            # Add frame specification if defined
            if self.frame_type:
                frame_spec = self.frame_type

                # Add frame bounds
                if self.frame_start:
                    if self.frame_end:
                        frame_spec += f" BETWEEN {self.frame_start} AND {self.frame_end}"
                    else:
                        frame_spec += f" {self.frame_start}"

                # Add exclude option if specified
                if self.exclude_option:
                    frame_spec += f" {self.exclude_option}"

                window_parts.append(frame_spec)

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
            parts.append(f"WHEN {condition} THEN '{result}'")
        if self.else_result is not None:
            parts.append(f"ELSE '{self.else_result}'")
        parts.append("END")
        expr = " ".join(parts)
        if self.alias:
            return f"{expr} as {self.alias}"
        return expr


class ConditionalExpression(SQLExpression):
    """Represents SQL conditional expressions like COALESCE, NULLIF, etc."""

    def __init__(self, func: str, *args: Union[str, SQLExpression, Any],
                 alias: Optional[str] = None):
        super().__init__(alias)
        self.func = func
        # Handle literal values and expressions
        self.args = []
        for arg in args:
            if isinstance(arg, SQLExpression):
                self.args.append(arg)
            elif isinstance(arg, str) and not arg.isdigit() and arg[0] != "'" and arg[0] != '"':
                # Assume it's a column if it's not clearly a string literal
                self.args.append(Column(arg))
            else:
                # Treat as literal value
                self.args.append(arg)

    def as_sql(self) -> str:
        args_sql = []
        for arg in self.args:
            if isinstance(arg, SQLExpression):
                args_sql.append(arg.as_sql())
            else:
                # Handle literal values
                args_sql.append(str(arg))

        expr = f"{self.func}({', '.join(args_sql)})"
        if self.alias:
            return f"{expr} as {self.alias}"
        return expr


class SubqueryExpression(SQLExpression):
    """Represents a subquery expression"""

    # Subquery types
    EXISTS = "EXISTS"
    IN = "IN"
    NOT_IN = "NOT IN"
    ALL = "ALL"
    ANY = "ANY"
    SOME = "SOME"  # Same as ANY

    def __init__(self,
                 subquery: str,
                 type: Optional[str] = None,
                 column: Optional[Union[str, SQLExpression]] = None,
                 params: Optional[tuple] = None,
                 alias: Optional[str] = None):
        super().__init__(alias)
        self.subquery = subquery
        self.type = type
        self.params = params or ()
        self.column = column if isinstance(column, SQLExpression) else Column(column) if column else None

    def as_sql(self) -> str:
        if self.type in (self.EXISTS, None):
            # EXISTS subquery or plain subquery
            expr = f"{self.type + ' ' if self.type else ''}({self.subquery})"
        else:
            # Other comparison subqueries (IN, ALL, ANY)
            expr = f"{self.column.as_sql()} {self.type} ({self.subquery})"

        if self.alias:
            return f"{expr} as {self.alias}"
        return expr


class JsonExpression(SQLExpression):
    """JSON expression for database-agnostic JSON operations.

    This class defines JSON operations in a database-agnostic way, with the actual
    SQL generation delegated to the database dialect implementation.

    Operations:
    - EXTRACT: Get value at path
    - EXTRACT_TEXT: Get value at path as text (unquoted)
    - CONTAINS: Check if JSON contains value (note: SQLite implements this with json_extract)
    - EXISTS: Check if path exists (note: SQLite implements this with json_extract IS NOT NULL)
    - TYPE: Get JSON type
    - REMOVE: Remove element at path
    - INSERT: Insert element at path if doesn't exist
    - REPLACE: Replace element at path if exists
    - SET: Set value at path (insert or replace)
    """

    # JSON operation types
    EXTRACT = "extract"  # Get value at path
    EXTRACT_TEXT = "text"  # Get value at path as text (unquoted)
    CONTAINS = "contains"  # Check if contains value
    EXISTS = "exists"  # Check if path exists
    TYPE = "type"  # Get JSON type
    REMOVE = "remove"  # Remove element at path
    INSERT = "insert"  # Insert at path if doesn't exist
    REPLACE = "replace"  # Replace at path if exists
    SET = "set"  # Set value at path (insert or replace)

    def __init__(self,
                 column: Union[str, SQLExpression],
                 path: str,
                 operation: str = "extract",  # extract, contains, exists
                 value: Any = None,
                 alias: Optional[str] = None):
        """Initialize JSON expression.

        Args:
            column: JSON column or expression
            path: JSON path (e.g. '$.name', '$.addresses[0].city')
            operation: Operation type (extract, text, contains, exists, etc.)
            value: Value for operations that need it (contains, insert, etc.)
            alias: Optional result alias
        """
        super().__init__(alias)
        self.column = column if isinstance(column, SQLExpression) else Column(column)
        self.path = path
        self.operation = operation
        self.value = value

    def as_sql(self) -> str:
        """Convert to SQL string using a generic placeholder format.

        This method creates a generic representation of the JSON operation.
        The actual SQL will be determined by the database dialect when the query
        is executed. This method is used primarily for debugging and logging.

        For actual SQL generation, the database dialect will be asked to format
        this expression appropriately based on the specific JSON capabilities
        of that database.

        Returns:
            str: Generic SQL representation of the JSON expression
        """
        # Generate a generic representation for display/logging purposes
        # The actual SQL will be determined by the dialect handler

        # Format column
        col_str = self.column.as_sql() if isinstance(self.column, SQLExpression) else str(self.column)

        # Basic format based on operation
        if self.operation == self.EXTRACT:
            expr = f"JSON_EXTRACT({col_str}, '{self.path}')"
        elif self.operation == self.EXTRACT_TEXT:
            expr = f"JSON_EXTRACT_TEXT({col_str}, '{self.path}')"
        elif self.operation == self.CONTAINS:
            expr = f"JSON_CONTAINS({col_str}, '{self.value}', '{self.path}')"
        elif self.operation == self.EXISTS:
            expr = f"JSON_EXISTS({col_str}, '{self.path}')"
        elif self.operation == self.TYPE:
            expr = f"JSON_TYPE({col_str}, '{self.path}')"
        elif self.operation == self.REMOVE:
            expr = f"JSON_REMOVE({col_str}, '{self.path}')"
        elif self.operation == self.INSERT:
            expr = f"JSON_INSERT({col_str}, '{self.path}', '{self.value}')"
        elif self.operation == self.REPLACE:
            expr = f"JSON_REPLACE({col_str}, '{self.path}', '{self.value}')"
        elif self.operation == self.SET:
            expr = f"JSON_SET({col_str}, '{self.path}', '{self.value}')"
        else:
            expr = f"JSON_EXTRACT({col_str}, '{self.path}')"

        # Add alias if specified
        if self.alias:
            return f"{expr} as {self.alias}"
        return expr

    def get_parameters(self):
        """Get expression parameters for dialect formatting.

        Returns:
            dict: Parameters needed for dialect-specific formatting
        """
        return {
            'column': self.column,
            'path': self.path,
            'operation': self.operation,
            'value': self.value,
            'alias': self.alias
        }


class GroupingSetExpression(SQLExpression):
    """Represents advanced grouping operations (CUBE, ROLLUP, GROUPING SETS)"""

    # Grouping types
    CUBE = "CUBE"
    ROLLUP = "ROLLUP"
    GROUPING_SETS = "GROUPING SETS"

    def __init__(self,
                 type: str,
                 columns: List[Union[str, List[str]]],
                 alias: Optional[str] = None):
        super().__init__(alias)
        self.type = type
        self.columns = columns

    def as_sql(self) -> str:
        if isinstance(self.columns[0], list):
            # For GROUPING SETS with multiple sets
            column_groups = []
            for group in self.columns:
                if isinstance(group, list):
                    column_groups.append(f"({', '.join(group)})")
                else:
                    column_groups.append(group)
            columns_sql = ", ".join(column_groups)
        else:
            # For CUBE and ROLLUP
            columns_sql = ", ".join(self.columns)

        expr = f"{self.type}({columns_sql})"

        if self.alias:
            return f"{expr} as {self.alias}"
        return expr

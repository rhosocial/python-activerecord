# src/rhosocial/activerecord/backend/impl/sqlite/dialect.py
import sqlite3
import sys
from typing import Optional, List, Set, Union, Dict, Tuple, Any

from .config import SQLiteConnectionConfig
from ...dialect import SQLExpressionBase, SQLDialectBase, ReturningClauseHandler, \
    ExplainOptions, ExplainType, ExplainFormat, AggregateHandler, JsonOperationHandler, CTEHandler
from ...errors import ReturningNotSupportedError, WindowFunctionNotSupportedError, \
    GroupingSetNotSupportedError, JsonOperationNotSupportedError

if sys.version_info >= (3, 9):
    TupleType = tuple
else:
    TupleType = Tuple


class SQLiteExpression(SQLExpressionBase):
    """SQLite expression implementation"""

    def format(self, dialect: SQLDialectBase) -> str:
        """Format SQLite expression"""
        return self.expression


class SQLiteDialect(SQLDialectBase):
    """SQLite dialect implementation"""

    def __init__(self, config):
        """Initialize SQLite dialect

        Args:
            config: SQLite database connection configuration
        """
        # Ensure we're working with a SQLiteConnectionConfig
        if not isinstance(config, SQLiteConnectionConfig):
            from ...config import ConnectionConfig
            # If it's a generic ConnectionConfig, convert it
            if isinstance(config, ConnectionConfig):
                # Extract any SQLite-specific options from the generic config
                pragmas = getattr(config, 'pragmas', {}) if hasattr(config, 'pragmas') else {}
                delete_on_close = getattr(config, 'delete_on_close', False) if hasattr(config,
                                                                                       'delete_on_close') else False

                # Create new SQLite config
                sqlite_config = SQLiteConnectionConfig(
                    host=config.host,
                    port=config.port,
                    database=config.database,
                    username=config.username,
                    password=config.password,
                    driver_type=config.driver_type,
                    pragmas=pragmas,
                    delete_on_close=delete_on_close,
                    options=config.options
                )

        version = tuple(map(int, sqlite3.sqlite_version.split('.')))
        super().__init__(version)

        # Initialize handlers
        self._returning_handler = SQLiteReturningHandler(version)
        self._aggregate_handler = SQLiteAggregateHandler(version)
        self._json_operation_handler = SQLiteJsonHandler(version)
        self._cte_handler = SQLiteCTEHandler(version)

    def format_expression(self, expr: SQLExpressionBase) -> str:
        """Format SQLite expression"""
        if not isinstance(expr, SQLiteExpression):
            raise ValueError(f"Unsupported expression type: {type(expr)}")
        return expr.format(self)

    def get_placeholder(self) -> str:
        """Get SQLite parameter placeholder"""
        return "?"

    def format_string_literal(self, value: str) -> str:
        # SQLite accepts both single and double quotes
        # We choose single quotes for consistency
        escaped = value.replace("'", "''")
        return f"'{escaped}'"

    def format_identifier(self, identifier: str) -> str:
        # SQLite allows double quotes or backticks for identifiers
        # We choose double quotes as it's more standard SQL
        if '"' in identifier:
            # If identifier contains double quotes, switch to backticks
            # to avoid complex escaping
            escaped = identifier.replace('`', '``')
            return f"`{escaped}`"
        return f'"{identifier}"'

    def format_limit_offset(self, limit: Optional[int] = None,
                            offset: Optional[int] = None) -> str:
        # SQLite requires LIMIT when using OFFSET
        # Use -1 as LIMIT to indicate "no limit"
        if limit is None and offset is not None:
            return f"LIMIT -1 OFFSET {offset}"
        elif limit is not None:
            if offset is not None:
                return f"LIMIT {limit} OFFSET {offset}"
            return f"LIMIT {limit}"
        return ""

    def get_parameter_placeholder(self, position: int) -> str:
        """Get SQLite parameter placeholder

        SQLite uses ? for all parameters regardless of position
        """
        return "?"

    def format_explain(self, sql: str, options: Optional[ExplainOptions] = None) -> str:
        """Format SQLite EXPLAIN statement

        Args:
            sql: SQL to explain
            options: EXPLAIN options

        Returns:
            str: Formatted EXPLAIN statement
        """
        if not options:
            options = ExplainOptions()

        # SQLite supports two types of EXPLAIN
        if options.type == ExplainType.QUERYPLAN:
            return f"EXPLAIN QUERY PLAN {sql}"
        return f"EXPLAIN {sql}"

    @property
    def supported_formats(self) -> Set[ExplainFormat]:
        return {ExplainFormat.TEXT}

    def create_expression(self, expression: str) -> SQLiteExpression:
        """Create SQLite expression"""
        return SQLiteExpression(expression)


class SQLiteReturningHandler(ReturningClauseHandler):
    """SQLite RETURNING clause handler implementation"""

    def __init__(self, version: tuple):
        """
        Initialize SQLite RETURNING handler with version information.

        Args:
            version: SQLite version tuple (major, minor, patch)
        """
        self._version = version

    @property
    def is_supported(self) -> bool:
        """
        Check if RETURNING clause is supported.

        RETURNING clause was added in SQLite 3.35.0.

        Returns:
            bool: True if supported, False otherwise
        """
        return self._version >= (3, 35, 0)

    def format_clause(self, columns: Optional[List[str]] = None) -> str:
        """
        Format RETURNING clause.

        Args:
            columns: Column names to return. None means all columns (*).

        Returns:
            str: Formatted RETURNING clause

        Raises:
            ReturningNotSupportedError: If RETURNING not supported by SQLite version
        """
        if not self.is_supported:
            raise ReturningNotSupportedError(
                f"RETURNING clause not supported in SQLite {'.'.join(map(str, self._version))}. "
                f"Version 3.35.0 or higher is required."
            )

        if not columns:
            return "RETURNING *"

        # Validate and escape each column name
        safe_columns = [self._validate_column_name(col) for col in columns]
        return f"RETURNING {', '.join(safe_columns)}"

    def format_advanced_clause(self,
                               columns: Optional[List[str]] = None,
                               expressions: Optional[List[Dict[str, Any]]] = None,
                               aliases: Optional[Dict[str, str]] = None,
                               dialect_options: Optional[Dict[str, Any]] = None) -> str:
        """
        Format advanced RETURNING clause for SQLite.

        SQLite supports expressions in RETURNING clause since 3.35.0.

        Args:
            columns: List of column names to return
            expressions: List of expressions to return
            aliases: Dictionary mapping column/expression names to aliases
            dialect_options: SQLite-specific options

        Returns:
            str: Formatted RETURNING clause

        Raises:
            ReturningNotSupportedError: If RETURNING not supported
        """
        if not self.is_supported:
            raise ReturningNotSupportedError(
                f"RETURNING clause not supported in SQLite {'.'.join(map(str, self._version))}. "
                f"Version 3.35.0 or higher is required."
            )

        # Process returning clause components
        items = []

        # Add columns with potential aliases
        if columns:
            for col in columns:
                alias = aliases.get(col) if aliases else None
                if alias:
                    items.append(f"{self._validate_column_name(col)} AS {self._validate_column_name(alias)}")
                else:
                    items.append(self._validate_column_name(col))

        # Add expressions with potential aliases
        if expressions:
            for expr in expressions:
                expr_text = expr.get("expression", "")
                expr_alias = expr.get("alias")
                if expr_alias:
                    items.append(f"{expr_text} AS {self._validate_column_name(expr_alias)}")
                else:
                    items.append(expr_text)

        # If no items specified, return all columns
        if not items:
            return "RETURNING *"

        return f"RETURNING {', '.join(items)}"

    def _validate_column_name(self, column: str) -> str:
        """
        Validate and escape column name for SQLite.

        SQLite uses double quotes or backticks for identifiers.
        We choose double quotes as it's more standard SQL.

        Args:
            column: Column name to validate

        Returns:
            str: Validated and properly quoted column name

        Raises:
            ValueError: If column name is invalid
        """
        # Remove any quotes first
        clean_name = column.strip('"').strip('`')

        # Basic validation
        if not clean_name or clean_name.isspace():
            raise ValueError("Empty column name")

        # Check for common SQL injection patterns
        dangerous_patterns = [';', '--', 'union', 'select', 'drop', 'delete', 'update']
        lower_name = clean_name.lower()
        if any(pattern in lower_name for pattern in dangerous_patterns):
            raise ValueError(f"Invalid column name: {column}")

        # If name contains special chars, wrap in quotes
        if ' ' in clean_name or '.' in clean_name or '"' in clean_name:
            return f'"{clean_name}"'

        return clean_name

    def supports_feature(self, feature: str) -> bool:
        """
        Check if a specific RETURNING feature is supported by SQLite.

        SQLite supports basic expressions and aliases in RETURNING.

        Args:
            feature: Feature name, such as "expressions", "aliases"

        Returns:
            bool: True if feature is supported, False otherwise
        """
        if not self.is_supported:
            return False

        # SQLite supports basic expressions and aliases
        supported_features = {"columns", "expressions", "aliases"}
        return feature in supported_features


class SQLiteAggregateHandler(AggregateHandler):
    """SQLite-specific aggregate functionality handler."""

    def __init__(self, version: tuple):
        """Initialize with SQLite version.

        Args:
            version: SQLite version tuple (major, minor, patch)
        """
        super().__init__(version)

    @property
    def supports_window_functions(self) -> bool:
        """Check if SQLite supports window functions.

        SQLite supports window functions from version 3.25.0
        """
        return self._version >= (3, 25, 0)

    @property
    def supports_advanced_grouping(self) -> bool:
        """Check if SQLite supports advanced grouping.

        SQLite does not support CUBE, ROLLUP, or GROUPING SETS.
        """
        return False

    def format_window_function(self,
                               expr: str,
                               partition_by: Optional[List[str]] = None,
                               order_by: Optional[List[str]] = None,
                               frame_type: Optional[str] = None,
                               frame_start: Optional[str] = None,
                               frame_end: Optional[str] = None,
                               exclude_option: Optional[str] = None) -> str:
        """Format window function SQL for SQLite.

        Args:
            expr: Base expression for window function
            partition_by: PARTITION BY columns
            order_by: ORDER BY columns
            frame_type: Window frame type (ROWS/RANGE only, GROUPS not supported)
            frame_start: Frame start specification
            frame_end: Frame end specification
            exclude_option: Frame exclusion option (not supported in SQLite)

        Returns:
            str: Formatted window function SQL

        Raises:
            WindowFunctionNotSupportedError: If window functions not supported or using unsupported features
        """
        if not self.supports_window_functions:
            raise WindowFunctionNotSupportedError(
                f"Window functions not supported in SQLite {'.'.join(map(str, self._version))}"
            )

        window_parts = []

        if partition_by:
            window_parts.append(f"PARTITION BY {', '.join(partition_by)}")

        if order_by:
            window_parts.append(f"ORDER BY {', '.join(order_by)}")

        # Build frame clause
        frame_clause = []
        if frame_type:
            if frame_type == "GROUPS":
                raise WindowFunctionNotSupportedError("GROUPS frame type not supported in SQLite")

            frame_clause.append(frame_type)

            if frame_start:
                if frame_end:
                    frame_clause.append(f"BETWEEN {frame_start} AND {frame_end}")
                else:
                    frame_clause.append(frame_start)

        if frame_clause:
            window_parts.append(" ".join(frame_clause))

        if exclude_option:
            raise WindowFunctionNotSupportedError("EXCLUDE options not supported in SQLite")

        window_clause = " ".join(window_parts)
        return f"{expr} OVER ({window_clause})"

    def format_grouping_sets(self,
                             type_name: str,
                             columns: List[Union[str, List[str]]]) -> str:
        """Format grouping sets SQL for SQLite.

        SQLite does not support CUBE, ROLLUP, or GROUPING SETS.

        Args:
            type_name: Grouping type (CUBE, ROLLUP, GROUPING SETS)
            columns: Columns to group by

        Raises:
            GroupingSetNotSupportedError: Always raised as SQLite doesn't support these
        """
        raise GroupingSetNotSupportedError(
            f"{type_name} not supported in SQLite. Consider using basic GROUP BY instead."
        )


class SQLiteJsonHandler(JsonOperationHandler):
    """SQLite-specific implementation of JSON operations."""

    def __init__(self, version: tuple):
        """Initialize handler with SQLite version info.

        Args:
            version: SQLite version as (major, minor, patch) tuple
        """
        self._version = version

        # Cache capability detection results
        self._json_supported = None
        self._arrows_supported = None
        self._function_support = {}

    @property
    def supports_json_operations(self) -> bool:
        """Check if SQLite version supports JSON1 extension.

        SQLite includes JSON1 extension in most builds from version 3.9.0

        Returns:
            bool: True if JSON operations are supported
        """
        if self._json_supported is None:
            self._json_supported = self._version >= (3, 9, 0)
        return self._json_supported

    @property
    def supports_json_arrows(self) -> bool:
        """Check if SQLite version supports -> and ->> operators.

        SQLite added -> and ->> operators in version 3.38.0 (2022-02-22)

        Returns:
            bool: True if JSON arrow operators are supported
        """
        if self._arrows_supported is None:
            self._arrows_supported = self._version >= (3, 38, 0)
        return self._arrows_supported

    def format_json_operation(self,
                              column: Union[str, Any],
                              path: Optional[str] = None,
                              operation: str = "extract",
                              value: Any = None,
                              alias: Optional[str] = None) -> str:
        """Format JSON operation according to SQLite syntax.

        This method converts abstract JSON operations into SQLite-specific syntax,
        handling version differences and using alternatives for unsupported functions.

        Args:
            column: JSON column name or expression
            path: JSON path (e.g. '$.name')
            operation: Operation type (extract, text, contains, exists, etc.)
            value: Value for operations that need it (contains, insert, etc.)
            alias: Optional alias for the result

        Returns:
            str: Formatted SQLite JSON operation

        Raises:
            JsonOperationNotSupportedError: If JSON operations not supported by SQLite version
        """
        if not self.supports_json_operations:
            raise JsonOperationNotSupportedError(
                f"JSON operations are not supported in SQLite {'.'.join(map(str, self._version))}"
            )

        # Handle column formatting
        col = str(column)

        # Use shorthand operators if available for extract operations
        if self.supports_json_arrows and path:
            if operation == "extract":
                expr = f"{col}->'{path}'"
                return f"{expr} as {alias}" if alias else expr
            elif operation == "text":
                expr = f"{col}->>'{path}'"
                return f"{expr} as {alias}" if alias else expr

        # Function-based approach for other operations or when arrows not supported
        if operation == "extract":
            expr = f"json_extract({col}, '{path}')" if path else col

        elif operation == "text":
            # There's no direct text extraction in SQLite, so we use json_extract
            expr = f"json_extract({col}, '{path}')" if path else col

        elif operation == "contains":
            # SQLite doesn't have json_contains function, use json_extract with comparison
            if path:
                # For checking if a value exists at specific path
                expr = f"json_extract({col}, '{path}') = '{value}'"
            else:
                # For checking in entire JSON document
                # Note: This is simplified and may not work for complex contains logic
                expr = f"json_extract({col}, ') LIKE '%{value}%'"

        elif operation == "exists":
            # SQLite doesn't have json_exists, use IS NOT NULL with json_extract instead
            expr = f"json_extract({col}, '{path}') IS NOT NULL"

        elif operation == "type":
            if self.supports_json_function("json_type"):
                path_part = f", '{path}'" if path else ""
                expr = f"json_type({col}{path_part})"
            else:
                # Fall back to typeof with json_extract if json_type not available
                expr = f"typeof(json_extract({col}, '{path}'))"

        elif operation == "remove":
            expr = f"json_remove({col}, '{path}')"

        elif operation == "insert":
            expr = f"json_insert({col}, '{path}', '{value}')"

        elif operation == "replace":
            expr = f"json_replace({col}, '{path}', '{value}')"

        elif operation == "set":
            expr = f"json_set({col}, '{path}', '{value}')"

        else:
            # Default to extract if operation not recognized
            raise JsonOperationNotSupportedError(
                f"JSON operation '{operation}' is not supported in SQLite {'.'.join(map(str, self._version))}"
            )

        if alias:
            return f"{expr} as {alias}"
        return expr

    def supports_json_function(self, function_name: str) -> bool:
        """Check if specific JSON function is supported in this SQLite version.

        Args:
            function_name: Name of JSON function to check (e.g., "json_extract")

        Returns:
            bool: True if function is supported
        """
        # Cache results for performance
        if function_name in self._function_support:
            return self._function_support[function_name]

        # All functions require JSON1 extension
        if not self.supports_json_operations:
            self._function_support[function_name] = False
            return False

        # Define version requirements for each function
        function_versions = {
            # Core JSON1 functions (all available since 3.9.0)
            "json_extract": (3, 9, 0),
            "json_insert": (3, 9, 0),
            "json_replace": (3, 9, 0),
            "json_set": (3, 9, 0),
            "json_remove": (3, 9, 0),
            "json_type": (3, 9, 0),
            "json_valid": (3, 9, 0),
            "json_quote": (3, 9, 0),
            "json_each": (3, 9, 0),
            "json_tree": (3, 9, 0),
            "json_array": (3, 9, 0),
            "json_object": (3, 9, 0),
            "json_array_length": (3, 9, 0),

            # JSON5 extension functions (some versions added later)
            "json_patch": (3, 18, 0),  # Added in 3.18.0
            "json_group_array": (3, 13, 0),  # Added in 3.13.0
            "json_group_object": (3, 13, 0),  # Added in 3.13.0

            # Note: SQLite doesn't have native json_contains function
            "json_contains": (99, 0, 0),  # Set to impossible version to indicate never supported

            # Arrow operators
            "->": (3, 38, 0),  # Added in 3.38.0
            "->>": (3, 38, 0)  # Added in 3.38.0
        }

        # Check if function is supported based on version
        required_version = function_versions.get(function_name.lower())
        if required_version:
            is_supported = self._version >= required_version
        else:
            # Unknown function, assume not supported
            is_supported = False

        # Cache result
        self._function_support[function_name] = is_supported
        return is_supported


class SQLiteCTEHandler(CTEHandler):
    """SQLite-specific CTE handler."""

    def __init__(self, version: tuple):
        self._version = version

    @property
    def is_supported(self) -> bool:
        # CTEs are supported in SQLite 3.8.3+
        return self._version >= (3, 8, 3)

    @property
    def supports_recursive(self) -> bool:
        # Basic recursive CTEs supported since 3.8.3
        return self.is_supported

    @property
    def supports_compound_recursive(self) -> bool:
        # Compound queries in recursive CTEs supported in SQLite 3.34.0+
        # (UNION, UNION ALL, EXCEPT, INTERSECT in recursive part)
        return self._version >= (3, 34, 0)

    @property
    def supports_multiple_ctes(self) -> bool:
        # Multiple CTEs supported since 3.8.3
        return self.is_supported

    @property
    def supports_cte_in_dml(self) -> bool:
        # SQLite supports CTEs in DML statements from version 3.8.3
        return self.is_supported

    @property
    def supports_materialized_hint(self) -> bool:
        # SQLite supports materialization hints from version 3.35.0
        return self._version >= (3, 35, 0)

    def format_cte(self,
                   name: str,
                   query: str,
                   columns: Optional[List[str]] = None,
                   recursive: bool = False,
                   materialized: Optional[bool] = None) -> str:
        """Format SQLite CTE syntax.

        This method only formats the CTE syntax according to SQLite's rules
        without checking if the feature is supported by the current SQLite version.
        Users should check support properties before executing the formatted SQL.

        Args:
            name: CTE name
            query: CTE query
            columns: Optional column names for the CTE
            recursive: Whether this is a recursive CTE (informational only)
            materialized: Materialization hint (only affects output if SQLite version supports it)

        Returns:
            str: Formatted CTE definition
        """
        name = self.validate_cte_name(name)

        # Add column definitions if provided
        column_def = ""
        if columns:
            column_def = f"({', '.join(columns)})"

        # Handle materialization hints if supported by SQLite version
        if materialized is not None and self.supports_materialized_hint:
            materialized_hint = "MATERIALIZED " if materialized else "NOT MATERIALIZED "
            return f"{name}{column_def} AS {materialized_hint}({query})"

        return f"{name}{column_def} AS ({query})"

    def format_with_clause(self, ctes: List[Dict[str, Any]]) -> str:
        """Format SQLite WITH clause syntax.

        This method accepts CTE definitions and generates a complete WITH clause
        according to SQLite syntax rules, handling recursive CTEs and other
        SQLite-specific features.

        Args:
            ctes: List of CTE definitions, each a dict with keys:
                 - name: CTE name
                 - query: CTE query
                 - columns: Optional column names
                 - recursive: Whether this is a recursive CTE
                 - materialized: Materialization hint

        Returns:
            str: Formatted WITH clause
        """
        if not ctes:
            return ""

        # Check if any CTE is recursive
        any_recursive = any(cte.get('recursive', False) for cte in ctes)
        recursive_keyword = "RECURSIVE " if any_recursive else ""

        formatted_ctes = []
        for cte in ctes:
            formatted_ctes.append(self.format_cte(
                name=cte['name'],
                query=cte['query'],
                columns=cte.get('columns'),
                recursive=cte.get('recursive', False),
                materialized=cte.get('materialized')
            ))

        return f"WITH {recursive_keyword}{', '.join(formatted_ctes)}"

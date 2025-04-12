import sqlite3
import sys
import uuid
from datetime import datetime, date, time
from decimal import Decimal
from typing import Optional, List, Set, Union, Dict
from typing import Tuple, Any

from ...dialect import TypeMapper, ValueMapper, DatabaseType, SQLExpressionBase, SQLDialectBase, ReturningClauseHandler, \
    ExplainOptions, ExplainType, ExplainFormat, AggregateHandler, JsonOperationHandler, TypeMapping
from ...errors import TypeConversionError, ReturningNotSupportedError, WindowFunctionNotSupportedError, \
    GroupingSetNotSupportedError, JsonOperationNotSupportedError
from ...helpers import safe_json_dumps, parse_datetime, convert_datetime, array_converter, safe_json_loads
from ...typing import ConnectionConfig

if sys.version_info >= (3, 9):
    TupleType = tuple
else:
    TupleType = Tuple


class SQLiteTypeMapper(TypeMapper):
    """
    SQLite type mapper implementation

    SQLite has a flexible type system with only a few storage classes:
    NULL, INTEGER, REAL, TEXT, and BLOB.

    This mapper handles the mapping from the unified DatabaseType enum to
    SQLite-specific type definitions.
    """

    def __init__(self, version: tuple = None):
        """
        Initialize SQLite type mapper

        Args:
            version: Optional SQLite version tuple (major, minor, patch)
        """
        super().__init__()

        # Store the SQLite version
        self._version = version

        # Define SQLite type mappings
        self._type_mappings = {
            # Numbers - all map to INTEGER or REAL
            DatabaseType.TINYINT: TypeMapping("INTEGER"),
            DatabaseType.SMALLINT: TypeMapping("INTEGER"),
            DatabaseType.INTEGER: TypeMapping("INTEGER"),
            DatabaseType.BIGINT: TypeMapping("INTEGER"),
            DatabaseType.FLOAT: TypeMapping("REAL"),
            DatabaseType.DOUBLE: TypeMapping("REAL"),
            DatabaseType.DECIMAL: TypeMapping("NUMERIC"),
            DatabaseType.NUMERIC: TypeMapping("NUMERIC"),
            DatabaseType.REAL: TypeMapping("REAL"),

            # Strings - all map to TEXT
            DatabaseType.CHAR: TypeMapping("TEXT", self.format_with_length),
            DatabaseType.VARCHAR: TypeMapping("TEXT", self.format_with_length),
            DatabaseType.TEXT: TypeMapping("TEXT"),
            DatabaseType.TINYTEXT: TypeMapping("TEXT"),
            DatabaseType.MEDIUMTEXT: TypeMapping("TEXT"),
            DatabaseType.LONGTEXT: TypeMapping("TEXT"),

            # Date and time - stored as TEXT, REAL (Julian day), or INTEGER (Unix time)
            DatabaseType.DATE: TypeMapping("TEXT"),  # ISO8601 string ("YYYY-MM-DD")
            DatabaseType.TIME: TypeMapping("TEXT"),  # ISO8601 string ("HH:MM:SS.SSS")
            DatabaseType.DATETIME: TypeMapping("TEXT"),  # ISO8601 string ("YYYY-MM-DD HH:MM:SS.SSS")
            DatabaseType.TIMESTAMP: TypeMapping("TEXT"),  # ISO8601 string with timezone

            # Binary data
            DatabaseType.BLOB: TypeMapping("BLOB"),
            DatabaseType.TINYBLOB: TypeMapping("BLOB"),
            DatabaseType.MEDIUMBLOB: TypeMapping("BLOB"),
            DatabaseType.LONGBLOB: TypeMapping("BLOB"),
            DatabaseType.BYTEA: TypeMapping("BLOB"),

            # Boolean - SQLite has no native boolean, uses INTEGER 0/1
            DatabaseType.BOOLEAN: TypeMapping("INTEGER"),

            # Other types - map to TEXT or BLOB
            DatabaseType.UUID: TypeMapping("TEXT"),  # Stored as text string
            DatabaseType.JSON: TypeMapping("TEXT"),  # JSON stored as text
            DatabaseType.ARRAY: TypeMapping("TEXT"),  # Arrays stored as JSON text

            # Advanced types - some may be supported in newer SQLite versions
            # Most map to TEXT or BLOB
            DatabaseType.XML: TypeMapping("TEXT"),
            DatabaseType.ENUM: TypeMapping("TEXT"),
            DatabaseType.MONEY: TypeMapping("NUMERIC"),

            # Custom type - map to TEXT by default
            DatabaseType.CUSTOM: TypeMapping("TEXT"),
        }

        # Add JSONB support for SQLite 3.45.0+
        if self._version and self._version >= (3, 45, 0):
            self._type_mappings[DatabaseType.JSONB] = TypeMapping("JSONB")
        else:
            self._type_mappings[DatabaseType.JSONB] = TypeMapping("TEXT")  # Fallback to TEXT

        # Set of supported types
        self._supported_types = set(self._type_mappings.keys())

    def get_column_type(self, db_type: DatabaseType, **params) -> str:
        """
        Get SQLite column type definition

        Args:
            db_type: Generic database type
            **params: Type parameters (length, precision, etc.)
                      These are mostly ignored for SQLite as it has a flexible type system

        Returns:
            str: SQLite column type definition

        Raises:
            ValueError: If type is not supported
        """
        if db_type not in self._type_mappings:
            raise ValueError(f"Unsupported type for SQLite: {db_type}")

        mapping = self._type_mappings[db_type]
        base_type = mapping.db_type

        # Apply any type-specific formatting
        if mapping.format_func:
            formatted_type = mapping.format_func(base_type, params)
        else:
            formatted_type = base_type

        # Apply common modifiers (PRIMARY KEY, NOT NULL, etc.)
        if params:
            return self.format_type_with_modifiers(formatted_type, **params)

        return formatted_type

    def get_placeholder(self, db_type: Optional[DatabaseType] = None) -> str:
        """
        Get parameter placeholder

        SQLite uses ? for all parameter types

        Args:
            db_type: Ignored in SQLite, as all placeholders use the same syntax

        Returns:
            str: Parameter placeholder for SQLite (?)
        """
        return "?"

    def reset_placeholders(self) -> None:
        return

    def supports_jsonb(self) -> bool:
        """
        Check if JSONB is supported in this SQLite version

        JSONB support was added in SQLite 3.45.0

        Returns:
            bool: True if JSONB is supported
        """
        return self._version and self._version >= (3, 45, 0)


class SQLiteValueMapper(ValueMapper):
    """SQLite value mapper implementation"""

    def __init__(self, config: ConnectionConfig):
        self.config = config
        # Define basic type converters
        self._base_converters = {
            int: int,
            float: float,
            Decimal: str,
            bool: lambda x: 1 if x else 0,
            uuid.UUID: str,
            date: convert_datetime,
            time: convert_datetime,
            datetime: convert_datetime,
            dict: safe_json_dumps,
            list: array_converter,
            tuple: array_converter,
        }
        # Define database type converters
        self._db_type_converters = {
            DatabaseType.BOOLEAN: lambda v: 1 if v else 0,
            DatabaseType.DATE: lambda v: convert_datetime(v, timezone=self.config.timezone),
            DatabaseType.TIME: lambda v: convert_datetime(v, timezone=self.config.timezone),
            DatabaseType.DATETIME: lambda v: convert_datetime(v, timezone=self.config.timezone),
            DatabaseType.TIMESTAMP: lambda v: convert_datetime(v, timezone=self.config.timezone),
            DatabaseType.JSON: safe_json_dumps,
            DatabaseType.ARRAY: array_converter,
            DatabaseType.UUID: str,
            DatabaseType.DECIMAL: str,
        }
        # Define Python type to target type converters - for conversion after database read
        self._from_python_converters = {
            DatabaseType.BOOLEAN: {
                int: bool,
                str: lambda v: v.lower() in ('true', '1', 'yes', 'on'),
                bool: lambda v: v,
            },
            DatabaseType.DATE: {
                str: lambda v: v,
                datetime: lambda v: v.date(),
                date: lambda v: v,
            },
            DatabaseType.TIME: {
                str: lambda v: v,
                datetime: lambda v: v.time(),
                time: lambda v: v,
            },
            DatabaseType.DATETIME: {
                str: lambda v: parse_datetime(v),
                int: lambda v: datetime.fromtimestamp(v),
                float: lambda v: datetime.fromtimestamp(v),
                datetime: lambda v: v,
            },
            DatabaseType.TIMESTAMP: {
                str: lambda v: parse_datetime(v),
                int: lambda v: datetime.fromtimestamp(v),
                float: lambda v: datetime.fromtimestamp(v),
                datetime: lambda v: v,
            },
            DatabaseType.JSON: {
                str: safe_json_loads,
                dict: lambda v: v,
                list: lambda v: v,
            },
            DatabaseType.ARRAY: {
                str: safe_json_loads,
                list: lambda v: v,
                tuple: list,
            },
            DatabaseType.UUID: {
                str: uuid.UUID,
                uuid.UUID: lambda v: v,
            },
            DatabaseType.DECIMAL: {
                str: Decimal,
                int: Decimal,
                float: Decimal,
                Decimal: lambda v: v,
            },
            DatabaseType.INTEGER: {
                str: int,
                float: int,
                bool: int,
                int: lambda v: v,
            },
            DatabaseType.FLOAT: {
                str: float,
                int: float,
                float: lambda v: v,
            },
            DatabaseType.TEXT: {
                str: lambda v: v,
                int: str,
                float: str,
                bool: str,
                datetime: str,
                date: str,
                time: str,
                uuid.UUID: str,
                Decimal: str,
            },
            DatabaseType.BLOB: {
                str: lambda v: v,
                bytes: lambda v: v,
            }
        }

    def to_database(self, value: Any, db_type: Optional[DatabaseType] = None) -> Any:
        """Convert Python value to SQLite storage value

        Args:
            value: Python value
            db_type: Target database type

        Returns:
            Converted value

        Raises:
            TypeConversionError: If type conversion fails
        """
        if value is None:
            return None

        try:
            # First try basic type conversion
            if db_type is None:
                value_type = type(value)
                if value_type in self._base_converters:
                    return self._base_converters[value_type](value)

            # Then try database type conversion
            if db_type in self._db_type_converters:
                return self._db_type_converters[db_type](value)

            # Special handling for numeric types
            if db_type in (DatabaseType.TINYINT, DatabaseType.SMALLINT,
                         DatabaseType.INTEGER, DatabaseType.BIGINT):
                return int(value)
            if db_type in (DatabaseType.FLOAT, DatabaseType.DOUBLE):
                return float(value)

            # Default to original value
            return value

        except Exception as e:
            raise TypeConversionError(
                f"Failed to convert {type(value)} to {db_type}: {str(e)}"
            )

    def from_database(self, value: Any, db_type: DatabaseType) -> Any:
        """Convert SQLite storage value to Python value

        Args:
            value: SQLite storage value
            db_type: Source database type

        Returns:
            Converted Python value

        Raises:
            TypeConversionError: If type conversion fails
        """
        if value is None:
            return None

        try:
            # Get current Python type
            current_type = type(value)

            # Get converter mapping for target type
            type_converters = self._from_python_converters.get(db_type)
            if type_converters:
                # Find converter for current Python type
                converter = type_converters.get(current_type)
                if converter:
                    return converter(value)

                # If no direct converter, try indirect conversion via string
                if current_type != str and str in type_converters:
                    return type_converters[str](str(value))

            # Return original value if no converter found
            return value

        except Exception as e:
            raise TypeConversionError(
                f"Failed to convert Python value {value} ({type(value)}) to {db_type}: {str(e)}"
            )

    def is_expression(self, value: Any) -> bool:
        """Check if value is a SQL expression"""
        return isinstance(value, SQLiteExpression)

    def format_param(self, value: Any) -> TupleType[Any, bool]:
        """Format parameter value

        Args:
            value: Parameter value

        Returns:
            tuple: (Processed value, is_expression flag)
        """
        if self.is_expression(value):
            return value.expression, True
        return self.to_database(value, None), False


class SQLiteExpression(SQLExpressionBase):
    """SQLite expression implementation"""

    def format(self, dialect: SQLDialectBase) -> str:
        """Format SQLite expression"""
        return self.expression


class SQLiteDialect(SQLDialectBase):
    """SQLite dialect implementation"""

    def __init__(self, config: ConnectionConfig):
        """Initialize SQLite dialect

        Args:
            config: Database connection configuration
        """
        version = tuple(map(int, sqlite3.sqlite_version.split('.')))
        super().__init__(version)

        # Initialize handlers
        self._type_mapper = SQLiteTypeMapper()
        self._value_mapper = SQLiteValueMapper(config)
        self._returning_handler = SQLiteReturningHandler(version)
        self._aggregate_handler = SQLiteAggregateHandler(version)
        self._json_operation_handler = SQLiteJsonHandler(version)

    def format_expression(self, expr: SQLExpressionBase) -> str:
        """Format SQLite expression"""
        if not isinstance(expr, SQLiteExpression):
            raise ValueError(f"Unsupported expression type: {type(expr)}")
        return expr.format(self)

    def get_placeholder(self) -> str:
        """Get SQLite parameter placeholder"""
        return self._type_mapper.get_placeholder(None)

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
                expr = f"json_extract({col}, '$') LIKE '%{value}%'"

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
            expr = f"json_extract({col}, '{path}')" if path else col

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
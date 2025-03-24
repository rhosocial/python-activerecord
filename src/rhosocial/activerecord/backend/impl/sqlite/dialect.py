import sqlite3
import sys
import uuid
from datetime import datetime, date, time
from decimal import Decimal
from typing import Optional, List, Set, Union
from typing import Tuple, Any

from .types import SQLITE_TYPE_MAPPINGS
from ...dialect import TypeMapper, ValueMapper, DatabaseType, SQLExpressionBase, SQLDialectBase, ReturningClauseHandler, \
    ExplainOptions, ExplainType, ExplainFormat, AggregateHandler
from ...errors import TypeConversionError, ReturningNotSupportedError, WindowFunctionNotSupportedError, \
    GroupingSetNotSupportedError
from ...helpers import safe_json_dumps, parse_datetime, convert_datetime, array_converter, safe_json_loads
from ...typing import ConnectionConfig

if sys.version_info >= (3, 9):
    TupleType = tuple
else:
    TupleType = Tuple

class SQLiteTypeMapper(TypeMapper):
    """SQLite type mapper implementation"""

    def get_column_type(self, db_type: DatabaseType, **params) -> str:
        """Get SQLite column type definition

        Args:
            db_type: Generic database type
            **params: Type parameters (length, precision, etc.)

        Returns:
            str: SQLite column type definition

        Raises:
            ValueError: If type is not supported
        """
        if db_type not in SQLITE_TYPE_MAPPINGS:
            raise ValueError(f"Unsupported type: {db_type}")

        mapping = SQLITE_TYPE_MAPPINGS[db_type]
        if mapping.format_func:
            return mapping.format_func(mapping.db_type, params)
        return mapping.db_type

    def get_placeholder(self, db_type: Optional[DatabaseType] = None) -> str:
        """Get parameter placeholder"""
        return "?"


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
        self._aggregate_handler = SQLiteAggregateHandler(version)  # Add aggregate handler

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
        """Initialize SQLite RETURNING handler

        Args:
            version: SQLite version tuple
        """
        self._version = version

    @property
    def is_supported(self) -> bool:
        """Check if RETURNING clause is supported"""
        return self._version >= (3, 35, 0)

    def format_clause(self, columns: Optional[List[str]] = None) -> str:
        """Format RETURNING clause

        Args:
            columns: Column names to return. None means all columns.

        Returns:
            str: Formatted RETURNING clause

        Raises:
            ReturningNotSupportedError: If RETURNING not supported
        """
        if not self.is_supported:
            raise ReturningNotSupportedError("SQLite version does not support RETURNING")

        if not columns:
            return "RETURNING *"

        # Validate and escape each column name
        safe_columns = [self._validate_column_name(col) for col in columns]
        return f"RETURNING {', '.join(safe_columns)}"

    def _validate_column_name(self, column: str) -> str:
        """Validate and escape column name

        Args:
            column: Column name to validate

        Returns:
            str: Escaped column name

        Raises:
            ValueError: If column name is invalid
        """
        # Remove any quotes first
        clean_name = column.strip('"')

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
    def supports_json_operations(self) -> bool:
        """Check if SQLite supports JSON operations.

        SQLite supports JSON1 extension in most builds,
        but we cannot reliably detect it at runtime.
        """
        # Assume JSON1 extension is available
        return True

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

    def format_json_operation(self,
                              column: str,
                              path: str,
                              operation: str = "extract",
                              value: Any = None) -> str:
        """Format JSON operation SQL for SQLite.

        Args:
            column: JSON column name
            path: JSON path string
            operation: Operation type (extract, contains, exists)
            value: Value for contains operation

        Returns:
            str: Formatted JSON operation SQL

        Raises:
            JsonOperationNotSupportedError: If JSON operations not supported
            ValueError: For unsupported operations
        """
        # SQLite uses json_extract, json_each, etc.
        if operation == "extract":
            return f"json_extract({column}, '{path}')"
        elif operation == "contains":
            if value is None:
                raise ValueError("Value is required for 'contains' operation")
            # For string comparison of JSON values
            if isinstance(value, str):
                return f"json_extract({column}, '{path}') = '{value}'"
            # For numeric/boolean comparison
            return f"json_extract({column}, '{path}') = {value}"
        elif operation == "exists":
            return f"json_extract({column}, '{path}') IS NOT NULL"
        else:
            raise ValueError(f"Unsupported JSON operation: {operation}")

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
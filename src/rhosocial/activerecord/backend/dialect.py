import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, date, time
from decimal import Decimal
from enum import Enum, auto
from typing import Any, Callable, Dict, Optional, Union, List, Tuple, Set, get_origin

from .errors import ReturningNotSupportedError

class DatabaseType(Enum):
    """
    Unified database type definitions across various database systems.

    This enum provides a standard set of database column types that can be
    mapped to specific implementations in each database backend.
    """

    # --- Standard numeric types ---
    TINYINT = auto()  # Small integer (usually 1 byte)
    SMALLINT = auto()  # Small integer (usually 2 bytes)
    INTEGER = auto()  # Standard integer (usually 4 bytes)
    BIGINT = auto()  # Large integer (usually 8 bytes)
    FLOAT = auto()  # Single-precision floating point
    DOUBLE = auto()  # Double-precision floating point
    DECIMAL = auto()  # Fixed-precision decimal number
    NUMERIC = auto()  # Generic numeric type
    REAL = auto()  # Real number type

    # --- Standard string types ---
    CHAR = auto()  # Fixed-length character string
    VARCHAR = auto()  # Variable-length character string with limit
    TEXT = auto()  # Variable-length character string without limit
    TINYTEXT = auto()  # Very small text (max 255 chars)
    MEDIUMTEXT = auto()  # Medium-sized text
    LONGTEXT = auto()  # Large text

    # --- Standard date and time types ---
    DATE = auto()  # Date only (year, month, day)
    TIME = auto()  # Time only (hour, minute, second)
    DATETIME = auto()  # Date and time without timezone
    TIMESTAMP = auto()  # Date and time with timezone
    INTERVAL = auto()  # Time interval

    # --- Standard binary types ---
    BLOB = auto()  # Binary large object
    TINYBLOB = auto()  # Small binary object
    MEDIUMBLOB = auto()  # Medium binary object
    LONGBLOB = auto()  # Large binary object
    BYTEA = auto()  # Binary data

    # --- Standard boolean type ---
    BOOLEAN = auto()  # Boolean (true/false)

    # --- Common extended types ---
    UUID = auto()  # Universally unique identifier

    # --- JSON types ---
    JSON = auto()  # JSON document
    JSONB = auto()  # Binary JSON

    # --- Array types ---
    ARRAY = auto()  # Array of values

    # --- XML type ---
    XML = auto()  # XML document

    # --- Key-value type ---
    HSTORE = auto()  # Key-value store

    # --- Network address types ---
    INET = auto()  # IPv4 or IPv6 host address
    CIDR = auto()  # IPv4 or IPv6 network address
    MACADDR = auto()  # MAC address
    MACADDR8 = auto()  # MAC address (EUI-64 format)

    # --- Geometric types ---
    POINT = auto()  # Point on a plane (x,y)
    LINE = auto()  # Infinite line
    LSEG = auto()  # Line segment
    BOX = auto()  # Rectangular box
    PATH = auto()  # Closed and open paths
    POLYGON = auto()  # Polygon (similar to closed path)
    CIRCLE = auto()  # Circle
    GEOMETRY = auto()  # Generic geometry type
    GEOGRAPHY = auto()  # Geographic data type

    # --- Range types ---
    INT4RANGE = auto()  # Range of integers
    INT8RANGE = auto()  # Range of bigints
    NUMRANGE = auto()  # Range of numerics
    TSRANGE = auto()  # Range of timestamps without time zone
    TSTZRANGE = auto()  # Range of timestamps with time zone
    DATERANGE = auto()  # Range of dates

    # --- Full text search types ---
    TSVECTOR = auto()  # Text search document
    TSQUERY = auto()  # Text search query

    # --- Money type ---
    MONEY = auto()  # Currency amount

    # --- Bit string types ---
    BIT = auto()  # Fixed-length bit string
    VARBIT = auto()  # Variable-length bit string

    # --- Enumeration and set types ---
    ENUM = auto()  # Enumeration of string values
    SET = auto()  # Set of string values

    # --- Large object types ---
    CLOB = auto()  # Character large object
    NCLOB = auto()  # National character large object

    # --- Unicode types ---
    NCHAR = auto()  # Unicode fixed-length character data
    NVARCHAR = auto()  # Unicode variable-length character data
    NTEXT = auto()  # Unicode variable-length character data

    # --- Row identifier types ---
    ROWID = auto()  # Physical row address
    UROWID = auto()  # Universal row id

    # --- Hierarchical type ---
    HIERARCHYID = auto()  # Tree hierarchy position

    # --- Extensible custom type ---
    CUSTOM = auto()  # For database-specific types not covered above

@dataclass
class TypeMapping:
    """Type mapping rules between DatabaseType and specific database implementation"""
    db_type: str
    format_func: Optional[Callable[[str, Dict[str, Any]], str]] = None


class TypeMapper(ABC):
    """
    Abstract base class for database type mapping.

    This class defines the interface for mapping between unified DatabaseType
    enum values and specific database column type definitions. Each database
    backend should implement a concrete TypeMapper that handles its specific
    type syntax and options.

    Note: While this abstract class attempts to accommodate a wide range of
    database types, specific database backends may need to handle additional
    types or parameters not covered by the base interface.
    """

    def __init__(self):
        """Initialize type mapper"""
        self._placeholder_counter = 0
        self._supported_types: Set[DatabaseType] = set()
        self._type_mappings: Dict[DatabaseType, TypeMapping] = {}

    @abstractmethod
    def get_column_type(self, db_type: DatabaseType, **params) -> str:
        """
        Get database-specific column type definition string for a given unified type.

        Args:
            db_type: Unified database type from DatabaseType enum
            **params: Type-specific parameters, which may include:
                - length: For string types (CHAR, VARCHAR)
                - precision: For numeric types (DECIMAL, FLOAT)
                - scale: For DECIMAL type
                - timezone: For time/timestamp types
                - array_dimensions: For ARRAY types
                - geometry_type: For geometric types (POINT, POLYGON, etc.)
                - enum_values: For ENUM types
                - custom_type: For database-specific CUSTOM types

        Returns:
            str: Formatted column type definition for the target database

        Raises:
            ValueError: If the type is not supported by this database
        """
        pass

    @abstractmethod
    def get_placeholder(self, db_type: Optional[DatabaseType] = None) -> str:
        """
        Get parameter placeholder for prepared statements.

        Different databases use different placeholder syntax:
        - SQLite: ?
        - MySQL: %s
        - PostgreSQL: %s or $1, $2 (depending on driver)
        - MariaDB: ?
        - SQL Server: @p1, @p2 or ?

        Args:
            db_type: Optional database type for type-specific placeholders
                     (some databases may use different placeholders for different types)

        Returns:
            str: Parameter placeholder string
        """
        pass

    @abstractmethod
    def reset_placeholders(self) -> None:
        """
        Reset placeholder counter if the database uses positional placeholders.

        This is needed for databases like PostgreSQL with asyncpg driver ($1, $2)
        or Oracle (:1, :2) where placeholder position matters.
        """
        pass

    def supports_type(self, db_type: DatabaseType) -> bool:
        """
        Check if this database supports the given type.

        Args:
            db_type: DatabaseType to check

        Returns:
            bool: True if the type is supported
        """
        return db_type in self._supported_types

    def get_supported_types(self) -> Set[DatabaseType]:
        """
        Get all supported database types.

        Returns:
            Set[DatabaseType]: Set of supported database types
        """
        return self._supported_types.copy()

    def format_type_with_modifiers(self, base_type: str, **modifiers) -> str:
        """
        Format complete type definition with modifiers.

        This helper method creates a full type definition including modifiers
        like NULL/NOT NULL, DEFAULT, etc.

        Args:
            base_type: Base type definition string
            **modifiers: Type modifiers which may include:
                - nullable: bool
                - default: Any
                - primary_key: bool
                - unique: bool
                - check: str (constraint expression)
                - collate: str (collation name)
                - autoincrement: bool

        Returns:
            str: Formatted type definition with modifiers
        """
        parts = [base_type]

        if modifiers.get('nullable') is False:
            parts.append("NOT NULL")

        if 'default' in modifiers:
            default_val = modifiers['default']
            if isinstance(default_val, str):
                parts.append(f"DEFAULT '{default_val}'")
            else:
                parts.append(f"DEFAULT {default_val}")

        if modifiers.get('primary_key'):
            parts.append("PRIMARY KEY")

        if modifiers.get('unique'):
            parts.append("UNIQUE")

        if 'check' in modifiers:
            parts.append(f"CHECK ({modifiers['check']})")

        if 'collate' in modifiers:
            parts.append(f"COLLATE {modifiers['collate']}")

        return " ".join(parts)

    def format_with_length(self, base_type: str, params: Dict[str, Any]) -> str:
        """
        Format type with length parameter.

        Args:
            base_type: Base type name
            params: Type parameters including 'length'

        Returns:
            str: Formatted type with length
        """
        if 'length' in params:
            return f"{base_type}({params['length']})"
        return base_type

    def format_decimal(self, base_type: str, params: Dict[str, Any]) -> str:
        """
        Format decimal type with precision and scale.

        Args:
            base_type: Base type name
            params: Type parameters including 'precision' and 'scale'

        Returns:
            str: Formatted decimal type
        """
        precision = params.get('precision', 10)
        scale = params.get('scale', 0)
        return f"{base_type}({precision}, {scale})"

    def format_enum(self, base_type: str, params: Dict[str, Any]) -> str:
        """
        Format enum type with values.

        Args:
            base_type: Base type name
            params: Type parameters including 'values'

        Returns:
            str: Formatted enum type
        """
        if 'values' in params:
            values_str = ", ".join(f"'{v}'" for v in params['values'])
            return f"{base_type}({values_str})"
        return base_type

    @classmethod
    def get_pydantic_model_field_type(cls, field_info) -> Optional[DatabaseType]:
        """Infer database type from field type

        Args:
            field_info: Pydantic field information

        Returns:
            Optional[DatabaseType]: Inferred database type
        """
        from pydantic import Json
        annotation = field_info.annotation

        # Handle Optional/Union types
        if get_origin(annotation) in (Union, Optional):
            # Get non-None type
            types = [t for t in field_info.annotation.__args__ if t is not type(None)]
            if types:
                annotation = types[0]

        # Map Python types to DatabaseType
        if annotation in (datetime, Optional[datetime]):
            return DatabaseType.DATETIME
        elif annotation in (date, Optional[date]):
            return DatabaseType.DATE
        elif annotation in (time, Optional[time]):
            return DatabaseType.TIME
        elif annotation in (bool, Optional[bool]):
            return DatabaseType.BOOLEAN
        elif annotation in (int, Optional[int]):
            return DatabaseType.INTEGER
        elif annotation in (float, Optional[float]):
            return DatabaseType.FLOAT
        elif annotation in (Decimal, Optional[Decimal]):
            return DatabaseType.DECIMAL
        elif annotation in (uuid.UUID, Optional[uuid.UUID]):
            return DatabaseType.UUID
        elif annotation in (list, List, Optional[list], Optional[List]):
            return DatabaseType.ARRAY
        elif annotation in (dict, Dict, Optional[dict], Optional[Dict]):
            return DatabaseType.JSON
        # Check if Json type (Pydantic specific)
        elif get_origin(annotation) is Json:
            return DatabaseType.JSON
        # Check if Enum type
        elif isinstance(annotation, type) and issubclass(annotation, Enum):
            return DatabaseType.TEXT
        elif annotation in (bytes, bytearray):
            return DatabaseType.BLOB

        return DatabaseType.TEXT

class ValueMapper(ABC):
    """Abstract base class for value mappers"""

    @abstractmethod
    def to_database(self, value: Any, db_type: DatabaseType) -> Any:
        """Convert to database value"""
        pass

    @abstractmethod
    def from_database(self, value: Any, db_type: DatabaseType) -> Any:
        """Convert from database value"""
        pass

class ReturningClauseHandler(ABC):
    """
    Base class for RETURNING clause handlers.

    This abstract class defines the interface for handling RETURNING clauses
    across different database systems, with support for advanced features like
    expressions, aliases, and database-specific options.
    """

    @property
    @abstractmethod
    def is_supported(self) -> bool:
        """
        Check if RETURNING clause is supported by this database.

        Returns:
            bool: True if supported, False otherwise
        """
        pass

    @abstractmethod
    def format_clause(self, columns: Optional[List[str]] = None) -> str:
        """Format RETURNING clause

        Args:
            columns: Column names to return. None means all columns.

        Returns:
            str: Formatted RETURNING clause

        Raises:
            ReturningNotSupportedError: If RETURNING not supported
        """
        pass

    def format_advanced_clause(self,
                            columns: Optional[List[str]] = None,
                            expressions: Optional[List[Dict[str, Any]]] = None,
                            aliases: Optional[Dict[str, str]] = None,
                            dialect_options: Optional[Dict[str, Any]] = None) -> str:
        """
        Format advanced RETURNING clause with expressions and aliases.

        Args:
            columns: List of column names to return
            expressions: List of expressions to return, each a dict with expression details
            aliases: Dictionary mapping column/expression names to aliases
            dialect_options: Database-specific options

        Returns:
            str: Formatted RETURNING clause

        Raises:
            ReturningNotSupportedError: If RETURNING not supported or features not supported
        """
        # Default implementation using basic RETURNING functionality
        if not self.is_supported:
            raise ReturningNotSupportedError("RETURNING clause not supported by this database")

        # If only columns specified, use basic format for compatibility
        if columns and not expressions and not aliases:
            return self.format_clause(columns)

        # Process expressions and aliases
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
        Validate and escape column name or alias to prevent SQL injection.

        Args:
            column: Column name or alias to validate

        Returns:
            str: Validated and properly quoted column name

        Raises:
            ValueError: If column name is invalid
        """
        # Basic implementation, can be overridden by specific databases
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
        Check if a specific RETURNING feature is supported.

        Args:
            feature: Feature name, such as "expressions", "aliases", "output_params"

        Returns:
            bool: True if feature is supported, False otherwise
        """
        # Default implementation, can be overridden by specific databases
        # Most basic databases only support column names
        supported_features = {"columns"}
        return feature in supported_features

class AggregateHandler(ABC):
    """Base class for handling database-specific aggregate functionality.

    This handler provides a consistent interface to check for database
    compatibility with various aggregate features and to format
    SQL expressions appropriately for each database dialect.
    """

    def __init__(self, version: tuple):
        """Initialize the aggregate handler.

        Args:
            version: Database version tuple (major, minor, patch)
        """
        self._version = version

    @property
    def version(self) -> tuple:
        """Get database version."""
        return self._version

    @property
    @abstractmethod
    def supports_window_functions(self) -> bool:
        """Check if database supports window functions."""
        pass

    @property
    @abstractmethod
    def supports_advanced_grouping(self) -> bool:
        """Check if database supports advanced grouping (CUBE, ROLLUP, GROUPING SETS)."""
        pass

    @abstractmethod
    def format_window_function(self,
                               expr: str,
                               partition_by: Optional[List[str]] = None,
                               order_by: Optional[List[str]] = None,
                               frame_type: Optional[str] = None,
                               frame_start: Optional[str] = None,
                               frame_end: Optional[str] = None,
                               exclude_option: Optional[str] = None) -> str:
        """Format window function SQL for specific database dialect.

        Args:
            expr: Base expression for window function
            partition_by: PARTITION BY columns
            order_by: ORDER BY columns
            frame_type: Window frame type (ROWS/RANGE/GROUPS)
            frame_start: Frame start specification
            frame_end: Frame end specification
            exclude_option: Frame exclusion option

        Returns:
            str: Formatted window function SQL

        Raises:
            WindowFunctionNotSupportedError: If window functions not supported
        """
        pass

    @abstractmethod
    def format_grouping_sets(self,
                             type_name: str,
                             columns: List[Union[str, List[str]]]) -> str:
        """Format grouping sets SQL for specific database dialect.

        Args:
            type_name: Grouping type (CUBE, ROLLUP, GROUPING SETS)
            columns: Columns to group by

        Returns:
            str: Formatted grouping sets SQL

        Raises:
            GroupingSetNotSupportedError: If grouping sets not supported
        """
        pass

class JsonOperationHandler:
    """Interface for database-specific JSON operation support.

    This class defines methods that should be implemented by each database dialect
    to handle JSON operations according to their specific syntax.
    """

    @property
    @abstractmethod
    def supports_json_operations(self) -> bool:
        """Check if database supports JSON operations."""
        pass

    @property
    @abstractmethod
    def supports_json_arrows(self) -> bool:
        """Check if database supports -> and ->> arrow operators for JSON access."""
        pass

    @abstractmethod
    def format_json_operation(self,
                              column: Union[str, Any],
                              path: Optional[str] = None,
                              operation: str = "extract",
                              value: Any = None,
                              alias: Optional[str] = None) -> str:
        """Format JSON operation SQL for specific database dialect.

        Args:
            column: JSON column name or expression
            path: JSON path string
            operation: Operation type (extract, text, contains, exists, etc.)
            value: Value for operations that need it (contains, insert, etc.)
            alias: Optional alias for the result

        Returns:
            str: Formatted JSON operation SQL

        Raises:
            JsonOperationNotSupportedError: If JSON operations not supported
        """
        pass

    @abstractmethod
    def supports_json_function(self, function_name: str) -> bool:
        """Check if specific JSON function is supported by the database.

        Args:
            function_name: Name of JSON function to check (e.g., "json_extract", "json_array")

        Returns:
            bool: True if function is supported
        """
        pass

class SQLExpressionBase(ABC):
    """Base class for SQL expressions

    Used for embedding raw expressions in SQL, such as:
    - Arithmetic expressions: column + 1
    - Function calls: COALESCE(column, 0)
    - Subqueries: (SELECT MAX(id) FROM table)
    """

    def __init__(self, expression: str):
        self.expression = expression

    def __str__(self) -> str:
        return self.expression

    @classmethod
    def raw(cls, expression: str) -> 'SQLExpressionBase':
        """Create raw SQL expression"""
        return cls(expression)

    @abstractmethod
    def format(self, dialect: 'SQLDialectBase') -> str:
        """Format expression according to dialect

        Args:
            dialect: SQL dialect

        Returns:
            str: Formatted expression
        """
        pass

class ExplainType(Enum):
    """Type of EXPLAIN output"""
    BASIC = auto()      # Basic execution plan
    ANALYZE = auto()    # Include actual execution statistics
    QUERYPLAN = auto()  # Query plan only (SQLite specific)

class ExplainFormat(Enum):
    """Output format for EXPLAIN results"""
    TEXT = "text"    # Human readable text
    JSON = "json"    # JSON format
    XML = "xml"      # XML format (SQL Server)
    YAML = "yaml"    # YAML format (PostgreSQL)
    TREE = "tree"    # TREE format (MySQL)

@dataclass
class ExplainOptions:
    """Options for EXPLAIN command"""
    type: ExplainType = ExplainType.BASIC
    format: ExplainFormat = ExplainFormat.TEXT
    costs: bool = True        # Show estimated costs
    buffers: bool = False     # Show buffer usage
    timing: bool = True       # Include timing information
    verbose: bool = False     # Show additional information
    settings: bool = False    # Show modified settings (PostgreSQL)
    wal: bool = False        # Show WAL usage (PostgreSQL)
    analyze: bool = False     # Same as type=ANALYZE, for compatibility

    def __post_init__(self):
        """Validate options and handle compatibility"""
        if self.analyze:
            self.type = ExplainType.ANALYZE

    @property
    def supported_formats(self) -> Set[ExplainFormat]:
        """Get supported output formats for current database"""
        return {ExplainFormat.TEXT}  # Base implementation

    def validate_for_database(self, dialect: str):
        """Validate options against specific database capabilities"""
        if self.format not in self.supported_formats:
            raise ValueError(f"Format {self.format} not supported by {dialect}")

class SQLDialectBase(ABC):
    """Base class for SQL dialects

    Defines SQL syntax differences between database backends
    """
    _type_mapper: TypeMapper
    _value_mapper: ValueMapper
    _returning_handler: ReturningClauseHandler
    _aggregate_handler: AggregateHandler
    _json_operation_handler: JsonOperationHandler
    _version: tuple

    def __init__(self, version: tuple) -> None:
        """Initialize SQL dialect

        Args:
            version: Database version tuple
        """
        self._version = version

    @property
    def version(self) -> tuple:
        """Get database version"""
        return self._version

    @property
    def type_mapper(self) -> TypeMapper:
        """Get type mapper"""
        return self._type_mapper

    @property
    def value_mapper(self) -> ValueMapper:
        """Get value mapper"""
        return self._value_mapper

    @property
    def returning_handler(self) -> ReturningClauseHandler:
        """Get returning clause handler"""
        return self._returning_handler

    @property
    def aggregate_handler(self) -> AggregateHandler:
        """Get aggregate functionality handler"""
        return self._aggregate_handler

    @property
    def json_operation_handler(self) -> JsonOperationHandler:
        """Get JSON operation handler"""
        return self._json_operation_handler

    @abstractmethod
    def format_expression(self, expr: SQLExpressionBase) -> str:
        """Format expression

        Args:
            expr: SQL expression

        Returns:
            str: Formatted expression
        """
        pass

    @abstractmethod
    def get_placeholder(self) -> str:
        """Get parameter placeholder

        Returns:
            str: Parameter placeholder (e.g., ? or %s)
        """
        pass

    @abstractmethod
    def format_string_literal(self, value: str) -> str:
        """Format string literal.

        Args:
            value: String value to quote

        Returns:
            str: Quoted string (e.g., 'value', "value")
        """
        pass

    @abstractmethod
    def format_identifier(self, identifier: str) -> str:
        """Format identifier (table name, column name).

        Args:
            identifier: Database identifier to quote

        Returns:
            str: Quoted identifier (e.g., `name`, "name", [name])
        """
        pass

    @abstractmethod
    def format_limit_offset(self, limit: Optional[int] = None,
                          offset: Optional[int] = None) -> str:
        """Format LIMIT and OFFSET clause.

        Args:
            limit: Maximum number of rows
            offset: Number of rows to skip

        Returns:
            str: Complete LIMIT/OFFSET clause
        """
        pass

    @abstractmethod
    def get_parameter_placeholder(self, position: int) -> str:
        """Get parameter placeholder with position

        Args:
            position: Parameter position (0-based)

        Returns:
            str: Parameter placeholder for the specific database
        """
        pass

    def format_like_pattern(self, pattern: str) -> str:
        """Format LIKE pattern by escaping % characters

        Args:
            pattern: Original LIKE pattern

        Returns:
            str: Escaped pattern
        """
        return pattern

    @abstractmethod
    def format_explain(self, sql: str, options: Optional[ExplainOptions] = None) -> str:
        """Format EXPLAIN statement according to dialect rules

        Args:
            sql: SQL to explain
            options: Configuration for EXPLAIN output
                    Defaults are database-appropriate if not specified

        Returns:
            str: Formatted EXPLAIN statement
        """
        pass

    @abstractmethod
    def create_expression(self, expression: str) -> SQLExpressionBase:
        """Create SQL expression"""
        pass

    def format_json_expression(self, **params) -> str:
        """Format JSON expression according to dialect rules.

        Delegates to the json_operation_handler for database-specific JSON formatting.
        Uses keyword arguments to avoid direct coupling with the expression classes.

        Args:
            **params: JSON expression parameters including:
                column: Column name or expression
                path: JSON path string
                operation: Operation type (extract, contains, exists, etc.)
                value: Value for operations that need it (optional)
                alias: Optional result alias (optional)

        Returns:
            str: Database-specific JSON expression

        Raises:
            ValueError: If required parameters are missing
            JsonOperationNotSupportedError: If JSON operations not supported
        """
        # Check the required parameters
        if 'column' not in params or 'path' not in params:
            raise ValueError("Missing required parameters for JSON expression: 'column' and 'path' are required")

        # Set the default value
        operation = params.get('operation', 'extract')
        value = params.get('value', None)
        alias = params.get('alias', None)

        # Delegates to the json_operation_handler for database-specific JSON formatting
        return self.json_operation_handler.format_json_operation(
            column=params['column'],
            path=params['path'],
            operation=operation,
            value=value,
            alias=alias
        )

class SQLBuilder:
    """SQL Builder

    Used for building SQL statements containing expressions
    """

    def __init__(self, dialect: SQLDialectBase):
        self.dialect = dialect
        self.sql = ""
        self.params = []

    def build(self, sql: str, params: Optional[Union[Tuple, List, Dict]] = None) -> Tuple[str, Tuple]:
        """Build SQL statement with parameters

        All question marks (?) in the SQL statement are treated as parameter
        placeholders and must have corresponding parameters. If you need to
        use a question mark as an actual value in your SQL, pass it as a
        parameter.

        Args:
            sql: SQL statement with ? placeholders
            params: Parameter values

        Returns:
            Tuple[str, Tuple]: (Processed SQL, Processed parameters)

        Raises:
            ValueError: If parameter count doesn't match placeholder count
        """
        if not params:
            return sql, ()

        # Convert params to tuple if needed
        if isinstance(params, (list, dict)):
            params = tuple(params)

        # First pass: collect information about parameters
        final_params = []
        expr_positions = {}  # Maps original position to expression
        param_count = 0

        for i, param in enumerate(params):
            if isinstance(param, SQLExpressionBase):
                expr_positions[i] = self.dialect.format_expression(param)
            else:
                final_params.append(param)
                param_count += 1

        # Second pass: build SQL with correct placeholders
        result = []
        current_pos = 0
        param_position = 0  # Counter for regular parameters
        placeholder_count = 0  # Total placeholder counter

        while True:
            # Find next placeholder
            placeholder_pos = sql.find('?', current_pos)
            if placeholder_pos == -1:
                # No more placeholders, add remaining SQL
                result.append(sql[current_pos:])
                break

            # Add SQL up to placeholder
            result.append(sql[current_pos:placeholder_pos])

            # Check if this position corresponds to an expression
            if placeholder_count in expr_positions:
                # Add the formatted expression
                result.append(expr_positions[placeholder_count])
            else:
                # Add a parameter placeholder with correct position
                result.append(self.dialect.get_parameter_placeholder(param_position))
                param_position += 1

            current_pos = placeholder_pos + 1
            placeholder_count += 1

        # Verify parameter count
        if placeholder_count != len(params):
            raise ValueError(
                f"Parameter count mismatch: SQL needs {placeholder_count} "
                f"parameters but {len(params)} were provided"
            )

        return ''.join(result), tuple(final_params)

    def format_identifier(self, identifier: str) -> str:
        """Format identifier according to dialect rules

        Use this method to properly quote table and column names.

        Args:
            identifier: Raw identifier name

        Returns:
            str: Properly quoted and escaped identifier
        """
        return self.dialect.format_identifier(identifier)

    def format_string_literal(self, value: str) -> str:
        """Format string literal according to dialect rules

        Use this method to properly quote string values that need to be
        embedded directly in SQL, not passed as parameters.

        Args:
            value: Raw string value

        Returns:
            str: Properly quoted and escaped string literal
        """
        return self.dialect.format_string_literal(value)

    def format_limit_offset(self, limit: Optional[int] = None,
                            offset: Optional[int] = None) -> str:
        """Format LIMIT and OFFSET clause

        Args:
            limit: Maximum number of rows
            offset: Number of rows to skip

        Returns:
            str: Complete LIMIT/OFFSET clause according to dialect rules
        """
        return self.dialect.format_limit_offset(limit, offset)

    def format_expression(self, expr: Any) -> str:
        """Format SQL expression according to dialect rules

        Use this method to format special SQL expressions that may have
        dialect-specific syntax.

        Args:
            expr: Expression to format

        Returns:
            str: Formatted expression according to dialect rules
        """
        return self.dialect.format_expression(expr)


class ReturningOptions:
    """
    Comprehensive configuration options for RETURNING clause.

    This class encapsulates all options related to RETURNING clause functionality
    across different database systems, supporting simple column lists, expressions,
    aliases, and database-specific features.
    """

    def __init__(self,
                 enabled: bool = False,
                 columns: Optional[List[str]] = None,
                 expressions: Optional[List[Dict[str, Any]]] = None,
                 aliases: Optional[Dict[str, str]] = None,
                 output_params: Optional[List[str]] = None,  # For Oracle/SQL Server output parameters
                 format: Optional[str] = None,  # Optional formatting style
                 force: bool = False,  # Force RETURNING even if compatibility issues exist
                 dialect_options: Optional[Dict[str, Any]] = None  # Database-specific options
                 ):
        """
        Initialize RETURNING options.

        Args:
            enabled: Whether RETURNING is enabled
            columns: List of column names to return
            expressions: List of expressions to return (each a dict with expression details)
            aliases: Dictionary mapping column/expression names to aliases
            output_params: List of output parameter names (for Oracle/SQL Server)
            format: Optional formatting style (database-specific)
            force: Force RETURNING even with known compatibility issues
            dialect_options: Database-specific options
        """
        self.enabled = enabled
        self.columns = columns or []
        self.expressions = expressions or []
        self.aliases = aliases or {}
        self.output_params = output_params or []
        self.format = format
        self.force = force
        self.dialect_options = dialect_options or {}

    @classmethod
    def from_legacy(cls, returning: bool, force: bool = False) -> 'ReturningOptions':
        """
        Create options from legacy boolean value.

        Args:
            returning: Legacy boolean returning flag
            force: Legacy force_returning flag

        Returns:
            ReturningOptions instance
        """
        return cls(enabled=returning, force=force)

    @classmethod
    def columns_only(cls, columns: List[str], force: bool = False) -> 'ReturningOptions':
        """
        Create options to return only specified columns.

        Args:
            columns: List of column names to return
            force: Force RETURNING even with known compatibility issues

        Returns:
            ReturningOptions instance
        """
        return cls(enabled=True, columns=columns, force=force)

    @classmethod
    def with_expressions(cls,
                         expressions: List[Dict[str, Any]],
                         aliases: Optional[Dict[str, str]] = None,
                         force: bool = False) -> 'ReturningOptions':
        """
        Create options with expressions in RETURNING clause.

        Args:
            expressions: List of expressions to return
            aliases: Optional aliases for expressions
            force: Force RETURNING even with known compatibility issues

        Returns:
            ReturningOptions instance
        """
        return cls(enabled=True, expressions=expressions, aliases=aliases, force=force)

    @classmethod
    def all_columns(cls, force: bool = False) -> 'ReturningOptions':
        """
        Create options to return all columns.

        Args:
            force: Force RETURNING even with known compatibility issues

        Returns:
            ReturningOptions instance
        """
        return cls(enabled=True, force=force)

    def __bool__(self) -> bool:
        """
        Boolean conversion returns whether RETURNING is enabled.

        Returns:
            True if RETURNING is enabled, False otherwise
        """
        return self.enabled

    def has_column_specification(self) -> bool:
        """
        Check if specific columns or expressions are specified.

        Returns:
            True if specific columns or expressions are specified, False for RETURNING *
        """
        return bool(self.columns or self.expressions)

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, date, time
from decimal import Decimal
from enum import Enum, auto
from typing import Any, Callable, Dict, Optional, get_origin, Union, List, Tuple, Set


class DatabaseType(Enum):
    """Unified database type definitions"""
    # Numeric types
    TINYINT = auto()
    SMALLINT = auto()
    INTEGER = auto()
    BIGINT = auto()
    FLOAT = auto()
    DOUBLE = auto()
    DECIMAL = auto()

    # String types
    CHAR = auto()
    VARCHAR = auto()
    TEXT = auto()

    # Date and time types
    DATE = auto()
    TIME = auto()
    DATETIME = auto()
    TIMESTAMP = auto()

    # Binary types
    BLOB = auto()

    # Boolean type
    BOOLEAN = auto()

    # Other types
    UUID = auto()
    JSON = auto()
    ARRAY = auto()
    # Extensible database-specific types
    CUSTOM = auto()

@dataclass
class TypeMapping:
    """Type mapping rules"""
    db_type: str
    format_func: Optional[Callable[[str, Dict[str, Any]], str]] = None

class TypeMapper(ABC):
    """Abstract base class for type mappers"""

    @abstractmethod
    def get_column_type(self, db_type: DatabaseType, **params) -> str:
        """Get database column type definition

        Args:
            db_type: Unified type definition
            **params: Type parameters (length, precision, etc.)
        """
        pass

    @abstractmethod
    def get_placeholder(self, db_type: Optional[DatabaseType] = None) -> str:
        """Get parameter placeholder"""
        pass

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
    """Base class for RETURNING clause handlers"""

    @property
    @abstractmethod
    def is_supported(self) -> bool:
        """Whether RETURNING clause is supported

        Returns:
            bool: True if supported
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
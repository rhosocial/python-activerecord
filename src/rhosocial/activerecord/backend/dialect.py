import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, date, time
from decimal import Decimal
from enum import Enum, auto
from typing import Any, Callable, Dict, Optional, get_origin, Union, List, Tuple


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

    def build(self, sql: str, params: Optional[Tuple] = None) -> Tuple[str, Tuple]:
        """Build SQL and parameters

        Process expressions and parameter placeholders in SQL

        Args:
            sql: Raw SQL
            params: SQL parameters

        Returns:
            Tuple[str, Tuple]: (Processed SQL, Processed parameters)
        """
        if not params:
            return sql, ()

        # Find all placeholder positions
        placeholder = self.dialect.get_placeholder()
        placeholder_positions = []
        pos = 0
        while True:
            pos = sql.find(placeholder, pos)
            if pos == -1:
                break
            placeholder_positions.append(pos)
            pos += len(placeholder)

        if len(placeholder_positions) != len(params):
            raise ValueError(f"Parameter count mismatch: expected {len(placeholder_positions)}, got {len(params)}")

        # Record new positions for all parameters
        result = list(sql)
        final_params = []
        param_positions = []  # Record positions of parameters to keep

        # First pass: find all parameter positions to keep
        for i, param in enumerate(params):
            if not isinstance(param, SQLExpressionBase):
                param_positions.append(i)
                final_params.append(param)

        # Second pass: replace expressions from back to front
        for i in range(len(params) - 1, -1, -1):
            if isinstance(params[i], SQLExpressionBase):
                pos = placeholder_positions[i]
                expr_str = self.dialect.format_expression(params[i])
                result[pos:pos + len(placeholder)] = expr_str

        # Third pass: handle placeholders
        # To maintain the relative order of regular parameters,
        # we need to map the unsubstituted placeholders to the preserved parameters
        # according to their original relative order
        param_index = 0
        for i in range(len(params)):
            if i in param_positions:
                # This position is a regular parameter, keep the placeholder
                param_index += 1

        return ''.join(result), tuple(final_params)
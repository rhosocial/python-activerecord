import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, date, time
from decimal import Decimal
from enum import Enum, auto
from typing import Any, Callable, Dict, Optional, get_origin, Union, List

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
    def get_placeholder(self, db_type: DatabaseType) -> str:
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
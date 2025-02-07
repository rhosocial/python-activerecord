from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Generic, Optional, TypeVar, Union

# Base type aliases
DatabaseValue = Union[str, int, float, bool, datetime, Decimal, bytes, None]
PythonValue = TypeVar('PythonValue')
T = TypeVar('T')

@dataclass
class ConnectionConfig:
    """Database connection configuration"""
    host: str = 'localhost'
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    charset: str = 'utf8mb4'
    timezone: Optional[str] = None  # Use 'UTC' instead of '+00:00'

    # Connection pool configuration
    pool_size: int = 5
    pool_timeout: int = 30

    # SSL configuration
    ssl_ca: Optional[str] = None
    ssl_cert: Optional[str] = None
    ssl_key: Optional[str] = None

    # Additional configuration parameters
    options: Dict[str, Any] = field(default_factory=dict)

@dataclass
class QueryResult(Generic[T]):
    """Query result wrapper"""
    data: Optional[T] = None
    affected_rows: int = 0
    last_insert_id: Optional[int] = None
    duration: float = 0.0  # Query execution time (seconds)
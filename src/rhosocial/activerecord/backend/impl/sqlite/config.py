# src/rhosocial/activerecord/backend/impl/sqlite/config.py
"""
SQLite-specific configuration classes.

This module provides configuration classes for SQLite database connections,
including pragmas and other SQLite-specific settings.
"""

import sqlite3
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, ClassVar, Protocol, runtime_checkable

from ...config import ConnectionConfig


# ==== SQLite-specific Protocols ====

@runtime_checkable
class SQLitePragmaProtocol(Protocol):
    """Protocol defining SQLite pragma settings."""
    pragmas: Dict[str, Any]


@runtime_checkable
class SQLiteDriverProtocol(Protocol):
    """Protocol defining SQLite driver-specific options."""
    uri: bool
    timeout: float
    isolation_level: Optional[str]
    detect_types: int


@runtime_checkable
class SQLiteStorageProtocol(Protocol):
    """Protocol defining SQLite storage options."""
    database: str
    delete_on_close: bool

    def is_memory_db(self) -> bool:
        """Check if the database is in-memory."""
        ...


# ==== SQLite-specific Mixins ====

@dataclass
class SQLitePragmaMixin:
    """Mixin implementing SQLite pragma settings."""
    pragmas: Dict[str, Any] = field(default_factory=dict)

    # Default SQLite pragmas
    DEFAULT_PRAGMAS: ClassVar[Dict[str, str]] = {
        "foreign_keys": "ON",
        "journal_mode": "WAL",
        "synchronous": "FULL",
        "wal_autocheckpoint": "1000",
        "wal_checkpoint": "FULL"
    }

    def __post_init__(self):
        """Initialize with default pragmas if none provided."""
        if not self.pragmas:
            self.pragmas = self.DEFAULT_PRAGMAS.copy()


@dataclass
class SQLiteDriverMixin:
    """Mixin implementing SQLite driver-specific options."""
    uri: bool = False
    timeout: float = 5.0
    isolation_level: Optional[str] = None
    detect_types: int = sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES


@dataclass
class SQLiteStorageMixin:
    """Mixin implementing SQLite storage options."""
    database: str = ':memory:'
    delete_on_close: bool = False

    def is_memory_db(self) -> bool:
        """Check if this is an in-memory database."""
        return self.database == ':memory:' or self.database.startswith('file::memory:')


# ==== SQLite Configuration Classes ====

@dataclass
class SQLiteConnectionConfig(ConnectionConfig, SQLitePragmaMixin, SQLiteDriverMixin, SQLiteStorageMixin):
    """
    SQLite connection configuration with SQLite-specific parameters.

    This class extends the base ConnectionConfig with SQLite-specific
    parameters and functionality.
    """

    def to_dict(self) -> dict:
        """Convert config to dictionary, including SQLite specific parameters."""
        # Get base dictionary from parent class
        result = super().to_dict()

        # Add pragmas to the options dictionary
        if 'options' not in result:
            result['options'] = {}

        if self.pragmas:
            result['options']['pragmas'] = self.pragmas

        # Add other SQLite-specific parameters that aren't in the base class
        if self.uri:
            result['options']['uri'] = self.uri

        return result

    @classmethod
    def from_env(cls, prefix: str = 'SQLITE_', **kwargs) -> 'SQLiteConnectionConfig':
        """Create configuration from environment variables.

        Args:
            prefix: Environment variable prefix (e.g., 'SQLITE_')

        Returns:
            SQLiteConnectionConfig: Connection configuration instance
        """
        # Get base configuration from parent class
        config = super(SQLiteConnectionConfig, cls).from_env(prefix)

        # Create a new instance with SQLite specific parameters
        import os

        def get_env(key: str) -> Any:
            return os.environ.get(f"{prefix}{key}")

        def get_env_bool(key: str) -> Optional[bool]:
            value = get_env(key)
            if value is not None:
                return value.lower() in ('true', 'yes', '1', 'on')
            return None

        def get_env_float(key: str) -> Optional[float]:
            value = get_env(key)
            if value is not None:
                try:
                    return float(value)
                except ValueError:
                    pass
            return None

        def get_env_dict(prefix_key: str) -> dict:
            """Get dictionary from environment variables with a common prefix."""
            result = {}
            prefix_with_underscore = f"{prefix}{prefix_key}_"

            for env_key, env_value in os.environ.items():
                if env_key.startswith(prefix_with_underscore):
                    dict_key = env_key[len(prefix_with_underscore):]
                    result[dict_key.lower()] = env_value

            return result

        # Get pragmas from environment if defined
        pragmas = get_env_dict('PRAGMA')

        # Merge with default pragmas if not explicitly set
        if not pragmas:
            pragmas = cls.DEFAULT_PRAGMAS.copy()

        # Create a new instance with all parameters
        return cls(
            # Base parameters
            host=config.host,
            port=config.port,
            database=get_env('DATABASE') or ':memory:',
            username=config.username,
            password=config.password,
            driver_type=config.driver_type,
            options=config.options,

            # SQLite specific parameters
            pragmas=pragmas,
            uri=get_env_bool('URI') or False,
            timeout=get_env_float('TIMEOUT') or 5.0,
            isolation_level=get_env('ISOLATION_LEVEL'),
            detect_types=int(get_env('DETECT_TYPES') or (sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)),
            delete_on_close=get_env_bool('DELETE_ON_CLOSE') or False,
        )


# ==== Specialized SQLite Configuration Classes ====

@dataclass
class SQLiteInMemoryConfig(SQLiteConnectionConfig):
    """In-memory SQLite database configuration with memory-optimized settings."""

    database: str = ':memory:'

    def __post_init__(self):
        """Initialize with memory-optimized pragmas."""
        super().__post_init__()
        # Override pragmas for memory database
        self.pragmas.update({
            "journal_mode": "MEMORY",
            "synchronous": "OFF",
            "temp_store": "MEMORY"
        })


@dataclass
class SQLiteTempFileConfig(SQLiteConnectionConfig):
    """Temporary file SQLite database configuration."""

    def __post_init__(self):
        """Initialize with temporary file settings."""
        super().__post_init__()
        import tempfile
        # Create a temporary file for the database
        temp_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.database = temp_file.name
        # Set delete on close to true to clean up the file
        self.delete_on_close = True

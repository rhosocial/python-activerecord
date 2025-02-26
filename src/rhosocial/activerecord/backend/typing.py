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

    # Connection characteristics
    database: Optional[str] = None
    charset: str = 'utf8mb4'
    timezone: Optional[str] = None  # Use 'UTC' instead of '+00:00'

    # Pool configuration
    pool_size: int = 5
    pool_timeout: int = 30
    pool_name: Optional[str] = None  # Added for test configuration

    # SSL configuration
    ssl_ca: Optional[str] = None
    ssl_cert: Optional[str] = None
    ssl_key: Optional[str] = None
    ssl_mode: Optional[str] = None  # Added for MySQL 8.4+

    # Authentication configuration
    auth_plugin: Optional[str] = None  # Added for MySQL 8.4+

    # Additional configuration parameters
    raise_on_warnings: bool = False
    options: Dict[str, Any] = field(default_factory=dict)
    version: Optional[tuple] = None
    driver_type: Optional[Any] = None
    delete_on_close: Optional[bool] = False

    # Added pragmas field specifically for SQLite
    pragmas: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert config to dictionary, excluding None values"""
        result = {}
        for key, value in self.__dict__.items():
            if value is not None and key not in ('options', 'pragmas'):
                result[key] = value

        # Include non-empty dictionaries
        if self.options:
            result.update(self.options)

        # Add pragmas to the options if they exist
        if self.pragmas:
            if 'options' not in result:
                result['options'] = {}
            result['options']['pragmas'] = self.pragmas

        return result

    @classmethod
    def from_env(cls, prefix: str = '') -> 'ConnectionConfig':
        """Create configuration from environment variables

        Args:
            prefix: Environment variable prefix (e.g., 'MYSQL84_')

        Returns:
            ConnectionConfig: Connection configuration instance
        """
        import os

        def get_env(key: str) -> Any:
            return os.getenv(f"{prefix}{key}")

        def get_env_int(key: str) -> Optional[int]:
            value = get_env(key)
            return int(value) if value is not None else None

        def get_env_bool(key: str) -> Optional[bool]:
            value = get_env(key)
            if value is not None:
                return value.lower() in ('true', 'yes', '1', 'on')
            return None

        def get_env_dict(prefix_key: str) -> dict:
            """Get dictionary from environment variables with a common prefix"""
            result = {}
            prefix_with_underscore = f"{prefix}{prefix_key}_"

            for env_key, env_value in os.environ.items():
                if env_key.startswith(prefix_with_underscore):
                    dict_key = env_key[len(prefix_with_underscore):]
                    result[dict_key.lower()] = env_value

            return result

        # Get pragmas from environment if defined
        pragmas = get_env_dict('PRAGMA')

        return cls(
            host=get_env('HOST') or 'localhost',
            port=get_env_int('PORT'),
            database=get_env('DATABASE'),
            username=get_env('USER'),
            password=get_env('PASSWORD'),
            charset=get_env('CHARSET') or 'utf8mb4',
            timezone=get_env('TIMEZONE'),
            pool_size=get_env_int('POOL_SIZE') or 5,
            pool_timeout=get_env_int('POOL_TIMEOUT') or 30,
            pool_name=get_env('POOL_NAME'),
            ssl_ca=get_env('SSL_CA'),
            ssl_cert=get_env('SSL_CERT'),
            ssl_key=get_env('SSL_KEY'),
            ssl_mode=get_env('SSL_MODE'),
            auth_plugin=get_env('AUTH_PLUGIN'),
            raise_on_warnings=get_env_bool('RAISE_ON_WARNINGS') or False,
            delete_on_close=get_env_bool('DELETE_ON_CLOSE'),
            version=None,  # Version can't be set from environment
            driver_type=None,  # Driver type can't be set from environment
            pragmas=pragmas  # SQLite pragmas from environment
        )

    def clone(self, **updates) -> 'ConnectionConfig':
        """Create a copy of the configuration with updates

        Args:
            **updates: Fields to update in the new configuration

        Returns:
            ConnectionConfig: New configuration instance
        """
        config_dict = self.to_dict()

        # Handle pragmas specially
        if 'pragmas' in updates:
            if self.pragmas:
                # Make a copy of existing pragmas and update with new ones
                pragmas = self.pragmas.copy()
                pragmas.update(updates.pop('pragmas'))
                updates['pragmas'] = pragmas

        config_dict.update(updates)
        return ConnectionConfig(**config_dict)

@dataclass
class QueryResult(Generic[T]):
    """Query result wrapper"""
    data: Optional[T] = None
    affected_rows: int = 0
    last_insert_id: Optional[int] = None
    duration: float = 0.0  # Query execution time (seconds)
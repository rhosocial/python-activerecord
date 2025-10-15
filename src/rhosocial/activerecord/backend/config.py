# src/rhosocial/activerecord/backend/config.py
"""
Core configuration classes and protocols for database connections.

This module provides base protocols and abstract classes to define
configuration options for various database backends.
"""

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Protocol, TypeVar, runtime_checkable, Tuple

# Type variable for generics
T = TypeVar('T')


@runtime_checkable
class ConfigProtocol(Protocol):
    """Base protocol for all configuration classes."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        ...

    def clone(self, **updates) -> 'ConfigProtocol':
        """Create a copy with updates."""
        ...

    @classmethod
    def from_env(cls, prefix: str = '') -> 'ConfigProtocol':
        """Create configuration from environment variables."""
        ...


@dataclass
class BaseConfig:
    """Base implementation of ConfigProtocol with common methods."""

    # Additional options that don't fit into standard fields
    options: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary, excluding None values."""
        result = {}
        for key, value in self.__dict__.items():
            if value is not None and key not in ('options',):
                result[key] = value

        # Include non-empty options
        if self.options:
            result.update(self.options)

        return result

    def clone(self, **updates) -> 'BaseConfig':
        """Create a copy of the configuration with updates."""
        config_dict = self.to_dict()

        # Handle special cases like nested dictionaries
        for key, value in updates.items():
            if key == 'options' and hasattr(self, 'options') and isinstance(self.options, dict):
                new_options = self.options.copy()
                new_options.update(value)
                updates[key] = new_options

        config_dict.update(updates)
        return type(self)(**config_dict)

    @classmethod
    def from_env(cls, prefix: str = '') -> 'BaseConfig':
        """Create configuration from environment variables.

        Args:
            prefix: Environment variable prefix (e.g., 'DB_')

        Returns:
            BaseConfig: Configuration instance with values from environment
        """
        env_values = {}
        field_names = [f.name for f in cls.__dataclass_fields__.values()]

        for field_name in field_names:
            env_key = f"{prefix}{field_name.upper()}"
            if env_key in os.environ:
                # Convert environment value to appropriate type
                field_type = cls.__dataclass_fields__[field_name].type
                env_value = os.environ[env_key]

                # Handle type conversion
                if field_type == bool or field_type == Optional[bool]:
                    env_values[field_name] = env_value.lower() in ('true', 'yes', '1', 'on')
                elif field_type == int or field_type == Optional[int]:
                    try:
                        env_values[field_name] = int(env_value)
                    except ValueError:
                        pass
                elif field_type == float or field_type == Optional[float]:
                    try:
                        env_values[field_name] = float(env_value)
                    except ValueError:
                        pass
                else:
                    env_values[field_name] = env_value

        # Handle options dictionary from environment
        options = {}
        options_prefix = f"{prefix}OPT_"
        for env_key, env_value in os.environ.items():
            if env_key.startswith(options_prefix):
                option_key = env_key[len(options_prefix):].lower()
                options[option_key] = env_value

        if options:
            env_values['options'] = options

        return cls(**env_values)


# ==== Core Protocols ====

@runtime_checkable
class BasicConnectionProtocol(Protocol):
    """Protocol defining basic connection parameters."""
    host: str
    port: Optional[int]
    database: Optional[str]
    username: Optional[str]
    password: Optional[str]


@runtime_checkable
class ConnectionPoolProtocol(Protocol):
    """Protocol defining connection pooling options."""
    pool_size: int
    pool_timeout: int
    pool_min_size: Optional[int]
    pool_max_size: Optional[int]
    pool_name: Optional[str]
    pool_recycle: Optional[int]
    pool_pre_ping: bool
    pool_reset_session: bool  # Added for MySQL compatibility

@runtime_checkable
class SSLProtocol(Protocol):
    """Protocol defining SSL/TLS connection options."""
    ssl_ca: Optional[str]
    ssl_cert: Optional[str]
    ssl_key: Optional[str]
    ssl_mode: Optional[str]
    ssl_verify: bool  # Keep for backward compatibility
    ssl_verify_cert: bool  # Add for MySQL-specific cert verification
    ssl_verify_identity: bool  # Add for MySQL-specific identity verification
    ssl_ciphers: Optional[str]


@runtime_checkable
class CharsetProtocol(Protocol):
    """Protocol defining character set and encoding options."""
    charset: str
    client_encoding: Optional[str]  # Keep for PostgreSQL compatibility
    collation: Optional[str]  # Add for MySQL-specific collation


@runtime_checkable
class TimezoneProtocol(Protocol):
    """Protocol defining timezone options."""
    timezone: Optional[str]
    server_timezone: Optional[str]  # Keep for PostgreSQL compatibility
    use_timezone: bool  # Add for MySQL-specific timezone handling


@runtime_checkable
class VersionProtocol(Protocol):
    """Protocol defining version information."""
    version: Optional[Tuple[int, ...]]


@runtime_checkable
class LoggingProtocol(Protocol):
    """Protocol defining logging-related options."""
    raise_on_warnings: bool  # Keep for backward compatibility
    log_queries: bool  # Add for MySQL-specific query logging
    log_level: Optional[Any]  # Support both str and int


# ==== Mixins ====

@dataclass
class BasicConnectionMixin:
    """Mixin implementing basic connection parameters."""
    host: str = 'localhost'
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None


@dataclass
class ConnectionPoolMixin:
    """Mixin implementing connection pooling options."""
    pool_size: int = 5
    pool_timeout: int = 30
    pool_min_size: Optional[int] = None
    pool_max_size: Optional[int] = None
    pool_name: Optional[str] = None
    pool_recycle: Optional[int] = None
    pool_pre_ping: bool = False
    pool_reset_session: bool = True  # Added for MySQL compatibility


@dataclass
class SSLMixin:
    """Mixin implementing SSL/TLS connection options."""
    ssl_ca: Optional[str] = None
    ssl_cert: Optional[str] = None
    ssl_key: Optional[str] = None
    ssl_mode: Optional[str] = None
    # ssl_verify: bool = True  # Keep for backward compatibility
    ssl_verify_cert: bool = False  # Add for MySQL-specific cert verification
    ssl_verify_identity: bool = False  # Add for MySQL-specific identity verification
    ssl_ciphers: Optional[str] = None


@dataclass
class CharsetMixin:
    """Mixin implementing character set and encoding options."""
    charset: str = 'utf8mb4'
    client_encoding: Optional[str] = None  # Keep for PostgreSQL compatibility
    collation: Optional[str] = None  # Add for MySQL-specific collation


@dataclass
class TimezoneMixin:
    """Mixin implementing timezone options."""
    timezone: Optional[str] = None
    server_timezone: Optional[str] = None  # Keep for PostgreSQL compatibility
    use_timezone: bool = True  # Add for MySQL-specific timezone handling


@dataclass
class VersionMixin:
    """Mixin implementing version information."""
    version: Optional[Tuple[int, ...]] = None


@dataclass
class LoggingMixin:
    """Mixin implementing logging options."""
    raise_on_warnings: bool = False  # Keep for backward compatibility
    log_queries: bool = False  # Add for MySQL-specific query logging
    log_level: Optional[Any] = None  # Support both str and int


# ==== Base Connection Config ====

@dataclass
class ConnectionConfig(BaseConfig, BasicConnectionMixin):
    """
    Minimal base connection configuration with only the most essential parameters.

    This class is designed to be extended by database-specific configurations
    that add additional parameters as needed.
    """

    # Minimal set of connection parameters that are truly universal
    driver_type: Optional[str] = None

    # Additional options dict
    options: Dict[str, Any] = field(default_factory=dict)

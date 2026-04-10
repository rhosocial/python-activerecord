# src/rhosocial/activerecord/connection/pool/config.py
"""
Connection pool configuration module.

Provides PoolConfig dataclass for configuring connection pool parameters.
"""

from dataclasses import dataclass, field
from typing import Callable, Optional, Any, Dict


@dataclass
class PoolConfig:
    """Connection pool configuration.

    .. note::
        The connection pool uses a QueuePool strategy where connections can be
        acquired and released across different threads. This is suitable only for
        backends whose driver reports ``threadsafety >= 2`` (e.g., PostgreSQL
        with psycopg). For SQLite and MySQL, use ``BackendGroup`` with
        ``backend.context()`` instead.

    Attributes:
        min_size: Minimum number of connections (warmup).
        max_size: Maximum number of connections.
        timeout: Timeout for acquiring a connection (seconds).
        idle_timeout: Idle timeout for connections (seconds), closed after timeout.
        max_lifetime: Maximum lifetime of a connection (seconds).
        close_timeout: Timeout for graceful close - waiting for active connections (seconds).
        validate_on_borrow: Whether to validate connection when borrowing.
        validate_on_return: Whether to validate connection when returning.
        validation_query: Validation query statement (SQL string).
        backend_factory: Factory function to create Backend instances.
        backend_config: Backend configuration dictionary.

    Example:
        # PostgreSQL — suitable for connection pool (threadsafety=2)
        config = PoolConfig(
            min_size=2,
            max_size=10,
            backend_factory=lambda: PostgresBackend(host="localhost")
        )

        # Using backend_config (built-in sqlite only)
        config = PoolConfig(
            min_size=2,
            max_size=10,
            backend_config={
                'type': 'sqlite',
                'database': ':memory:'
            }
        )
    """

    # Pool size
    min_size: int = 1  # Minimum connections (warmup)
    max_size: int = 10  # Maximum connections

    # Timeout settings
    timeout: float = 30.0  # Acquire timeout (seconds)
    idle_timeout: float = 300.0  # Idle timeout (seconds), closed after timeout
    max_lifetime: float = 3600.0  # Maximum connection lifetime (seconds)
    close_timeout: float = 5.0  # Graceful close timeout (seconds), 0 = no wait

    # Validation settings
    validate_on_borrow: bool = True  # Validate connection when borrowing
    validate_on_return: bool = False  # Validate connection when returning
    validation_query: Optional[str] = "SELECT 1"  # Validation query (SQL string)

    # Backend factory
    backend_factory: Optional[Callable[[], Any]] = None  # Factory function to create Backend
    backend_config: Dict[str, Any] = field(default_factory=dict)  # Backend configuration

    def __post_init__(self):
        """Validate configuration parameters."""
        if self.min_size < 0:
            raise ValueError("min_size must be >= 0")
        if self.max_size < 1:
            raise ValueError("max_size must be >= 1")
        if self.min_size > self.max_size:
            raise ValueError("min_size cannot exceed max_size")
        if self.timeout <= 0:
            raise ValueError("timeout must be > 0")
        if self.idle_timeout < 0:
            raise ValueError("idle_timeout must be >= 0")
        if self.max_lifetime <= 0:
            raise ValueError("max_lifetime must be > 0")
        if self.close_timeout < 0:
            raise ValueError("close_timeout must be >= 0")

        # Validate validation_query logic
        if self.validation_query is None:
            if self.validate_on_borrow or self.validate_on_return:
                raise ValueError(
                    "validation_query cannot be None when validate_on_borrow "
                    "or validate_on_return is True. Either provide a valid "
                    "validation_query or disable validation."
                )
        elif not isinstance(self.validation_query, str):
            raise TypeError(
                f"validation_query must be str, got {type(self.validation_query).__name__}"
            )

    def clone(self, **updates) -> 'PoolConfig':
        """Create a copy with optional field updates.

        Args:
            **updates: Fields to update

        Returns:
            New PoolConfig instance
        """
        config_dict = {
            'min_size': self.min_size,
            'max_size': self.max_size,
            'timeout': self.timeout,
            'idle_timeout': self.idle_timeout,
            'max_lifetime': self.max_lifetime,
            'close_timeout': self.close_timeout,
            'validate_on_borrow': self.validate_on_borrow,
            'validate_on_return': self.validate_on_return,
            'validation_query': self.validation_query,
            'backend_factory': self.backend_factory,
            'backend_config': self.backend_config.copy(),
        }
        config_dict.update(updates)
        return PoolConfig(**config_dict)

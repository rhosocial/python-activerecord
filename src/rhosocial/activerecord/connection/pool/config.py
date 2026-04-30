# src/rhosocial/activerecord/connection/pool/config.py
"""
Connection pool configuration module.

Provides PoolConfig dataclass for configuring connection pool parameters.
"""

import logging
from dataclasses import dataclass, field
from typing import Callable, Literal, Optional, Any, Dict

logger = logging.getLogger(__name__)

# Connection mode type: auto-detect, persistent (long-lived), or transient (short-lived)
ConnectionMode = Literal["auto", "persistent", "transient"]


@dataclass
class PoolConfig:
    """Connection pool configuration.

    .. note::
        The connection pool supports two connection management modes controlled by
        ``connection_mode``:

        - ``"persistent"``: Connections are established at creation time and stay
          connected across acquire/release cycles. Only ``close()`` disconnects them.
          Suitable for backends with ``threadsafety >= 2`` (e.g., PostgreSQL with psycopg).

        - ``"transient"``: Connections are established on acquire and disconnected on
          release (controlled by ``auto_connect_on_acquire`` / ``auto_disconnect_on_release``).
          Suitable for backends with ``threadsafety < 2`` (e.g., SQLite, MySQL).

        - ``"auto"`` (default): Automatically selects the mode based on backend
          ``threadsafety``. ``persistent`` for ``threadsafety >= 2``, ``transient`` otherwise.

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
        connection_mode: Connection management mode (``"auto"``, ``"persistent"``, ``"transient"``).
        auto_connect_on_acquire: Automatically connect when acquiring (transient mode only).
        auto_disconnect_on_release: Automatically disconnect when releasing (transient mode only).
        backend_factory: Factory function to create Backend instances.
        backend_config: Backend configuration dictionary.

    Example:
        # PostgreSQL — persistent mode (auto-detected from threadsafety=2)
        config = PoolConfig(
            min_size=2,
            max_size=10,
            backend_factory=lambda: PostgresBackend(host="localhost")
        )
        # Connections are established at warmup and stay connected

        # SQLite — transient mode (auto-detected from threadsafety=1)
        config = PoolConfig(
            min_size=1,
            max_size=5,
            backend_config={
                'type': 'sqlite',
                'database': ':memory:'
            }
        )
        # Connections are established on acquire, disconnected on release

        # Explicit mode override
        config = PoolConfig(
            min_size=2,
            max_size=10,
            connection_mode="persistent",
            backend_factory=lambda: PostgresBackend(host="localhost")
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

    # Connection management mode
    connection_mode: ConnectionMode = "auto"  # auto, persistent, or transient

    # Connection lifecycle settings (effective in transient mode only)
    auto_connect_on_acquire: bool = True  # Automatically connect when acquiring
    auto_disconnect_on_release: bool = True  # Automatically disconnect when releasing

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

        # Validate connection_mode
        if self.connection_mode not in ("auto", "persistent", "transient"):
            raise ValueError(
                f"connection_mode must be 'auto', 'persistent', or 'transient', "
                f"got {self.connection_mode!r}"
            )

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

        # Warn if auto_connect/auto_disconnect set in persistent mode
        if self.connection_mode == "persistent":
            if self.auto_connect_on_acquire or self.auto_disconnect_on_release:
                logger.warning(
                    "PoolConfig: connection_mode='persistent' ignores "
                    "auto_connect_on_acquire and auto_disconnect_on_release. "
                    "Connections stay connected across acquire/release in persistent mode."
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
            'connection_mode': self.connection_mode,
            'auto_connect_on_acquire': self.auto_connect_on_acquire,
            'auto_disconnect_on_release': self.auto_disconnect_on_release,
            'backend_factory': self.backend_factory,
            'backend_config': self.backend_config.copy(),
        }
        config_dict.update(updates)
        return PoolConfig(**config_dict)

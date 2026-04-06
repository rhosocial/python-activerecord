# src/rhosocial/activerecord/connection/pool/pooled_backend.py
"""
Pooled Backend wrapper module.

Provides PooledBackend dataclass for wrapping Backend instances and tracking their state.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


@dataclass
class PooledBackend:
    """Pooled Backend instance.

    Wraps a Backend instance and tracks its lifecycle and usage state.

    Attributes:
        backend: Backend instance (StorageBackend or AsyncStorageBackend).
        pool_key: Pool identifier.
        created_at: Creation time.
        last_used_at: Last used time.
        acquired_at: Time when last acquired (for hold time tracking).
        use_count: Usage count.
        is_healthy: Health status.

    Example:
        pooled = PooledBackend(backend=my_backend, pool_key="pool-1")
        pooled.mark_used()
        if pooled.is_expired(3600):
            print("Connection expired")
    """

    backend: Any  # Backend instance (StorageBackend or AsyncStorageBackend)
    pool_key: str  # Pool identifier
    created_at: Optional[datetime] = None  # Creation time
    last_used_at: Optional[datetime] = None  # Last used time
    acquired_at: Optional[datetime] = None  # Time when last acquired
    use_count: int = 0  # Usage count
    is_healthy: bool = True  # Health status

    def __post_init__(self):
        """Initialize timestamps."""
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.last_used_at is None:
            self.last_used_at = self.created_at

    def mark_used(self) -> None:
        """Mark as used.

        Updates last used time and increments usage count.
        Also sets acquired_at for hold time tracking.
        """
        now = datetime.now()
        self.last_used_at = now
        self.acquired_at = now
        self.use_count += 1

    def hold_time(self) -> float:
        """Get current hold time (seconds).

        Returns:
            Time since last acquired, 0.0 if not currently held.
        """
        if self.acquired_at is None:
            return 0.0
        return (datetime.now() - self.acquired_at).total_seconds()

    def is_expired(self, max_lifetime: float) -> bool:
        """Check if maximum lifetime has been exceeded.

        Args:
            max_lifetime: Maximum lifetime (seconds)

        Returns:
            True if expired
        """
        if self.created_at is None:
            return False
        age = (datetime.now() - self.created_at).total_seconds()
        return age >= max_lifetime

    def is_idle(self, idle_timeout: float) -> bool:
        """Check if idle timeout has been exceeded.

        Args:
            idle_timeout: Idle timeout (seconds)

        Returns:
            True if idle timeout exceeded
        """
        if self.last_used_at is None:
            return False
        idle_time = (datetime.now() - self.last_used_at).total_seconds()
        return idle_time >= idle_timeout

    def age(self) -> float:
        """Get connection age (seconds).

        Returns:
            Time since creation (seconds)
        """
        if self.created_at is None:
            return 0.0
        return (datetime.now() - self.created_at).total_seconds()

    def idle_time(self) -> float:
        """Get idle time (seconds).

        Returns:
            Time since last use (seconds)
        """
        if self.last_used_at is None:
            return 0.0
        return (datetime.now() - self.last_used_at).total_seconds()

    def reset(self) -> None:
        """Reset state.

        Called when returning connection; resets health status and clears acquired_at.
        Note: Does not reset use_count and timestamps, used for statistics.
        """
        self.is_healthy = True
        self.acquired_at = None

    def mark_unhealthy(self) -> None:
        """Mark as unhealthy."""
        self.is_healthy = False

    def __repr__(self) -> str:
        """Return readable representation."""
        return (
            f"PooledBackend(backend={type(self.backend).__name__}, "
            f"pool_key={self.pool_key!r}, "
            f"use_count={self.use_count}, "
            f"is_healthy={self.is_healthy}, "
            f"age={self.age():.1f}s)"
        )

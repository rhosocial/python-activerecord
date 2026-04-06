# src/rhosocial/activerecord/connection/pool/stats.py
"""
Connection pool statistics module.

Provides PoolStats dataclass for tracking connection pool runtime status and statistics.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class PoolStats:
    """Connection pool statistics.

    Tracks connection pool runtime status including cumulative statistics and current state.

    Attributes:
        total_created: Total number of connections created.
        total_destroyed: Total number of connections destroyed.
        total_acquired: Total number of acquire operations.
        total_released: Total number of release operations.
        total_timeouts: Total number of timeout events.
        total_errors: Total number of errors.
        total_validation_failures: Total number of validation failures.
        current_available: Current number of available connections.
        current_in_use: Current number of connections in use.
        created_at: Pool creation time.
        last_acquired_at: Last acquire time.
        last_released_at: Last release time.

    Example:
        stats = pool.get_stats()
        print(f"Utilization: {stats.utilization_rate:.2%}")
        print(f"Current connections: {stats.current_total}")
    """

    # Cumulative statistics
    total_created: int = 0  # Total connections created
    total_destroyed: int = 0  # Total connections destroyed
    total_acquired: int = 0  # Total acquire operations
    total_released: int = 0  # Total release operations
    total_timeouts: int = 0  # Total timeout events
    total_errors: int = 0  # Total errors
    total_validation_failures: int = 0  # Total validation failures

    # Current state
    current_available: int = 0  # Current available connections
    current_in_use: int = 0  # Current connections in use

    # Timestamps
    created_at: Optional[datetime] = None  # Pool creation time
    last_acquired_at: Optional[datetime] = None  # Last acquire time
    last_released_at: Optional[datetime] = None  # Last release time

    def __post_init__(self):
        """Initialize creation time."""
        if self.created_at is None:
            self.created_at = datetime.now()

    @property
    def current_total(self) -> int:
        """Current total connections."""
        return self.current_available + self.current_in_use

    @property
    def utilization_rate(self) -> float:
        """Connection utilization rate (0.0 ~ 1.0)."""
        total = self.current_total
        return self.current_in_use / total if total > 0 else 0.0

    @property
    def avg_lifetime(self) -> float:
        """Average connection lifetime (seconds).

        This is a simplified calculation; actual implementation should track
        each connection's lifetime individually.
        """
        if self.total_created == 0:
            return 0.0
        elapsed = (datetime.now() - self.created_at).total_seconds()
        return elapsed / self.total_created

    @property
    def uptime(self) -> float:
        """Pool uptime (seconds)."""
        if self.created_at is None:
            return 0.0
        return (datetime.now() - self.created_at).total_seconds()

    @property
    def acquire_rate(self) -> float:
        """Acquire rate (operations per second)."""
        uptime = self.uptime
        return self.total_acquired / uptime if uptime > 0 else 0.0

    @property
    def error_rate(self) -> float:
        """Error rate (0.0 ~ 1.0)."""
        total_operations = self.total_acquired + self.total_released
        return self.total_errors / total_operations if total_operations > 0 else 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary.

        Returns:
            Dictionary containing all statistics
        """
        return {
            'total_created': self.total_created,
            'total_destroyed': self.total_destroyed,
            'total_acquired': self.total_acquired,
            'total_released': self.total_released,
            'total_timeouts': self.total_timeouts,
            'total_errors': self.total_errors,
            'total_validation_failures': self.total_validation_failures,
            'current_available': self.current_available,
            'current_in_use': self.current_in_use,
            'current_total': self.current_total,
            'utilization_rate': self.utilization_rate,
            'uptime': self.uptime,
            'acquire_rate': self.acquire_rate,
            'error_rate': self.error_rate,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_acquired_at': self.last_acquired_at.isoformat() if self.last_acquired_at else None,
            'last_released_at': self.last_released_at.isoformat() if self.last_released_at else None,
        }

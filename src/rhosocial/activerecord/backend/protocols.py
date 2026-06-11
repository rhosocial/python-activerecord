# src/rhosocial/activerecord/backend/protocols.py
"""
Backend protocol definitions.

This module defines protocol interfaces for backend implementations to declare
support for various backend-specific features.
"""

from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable


@dataclass(frozen=True)
class ConcurrencyHint:
    """
    Dataclass for holding concurrency constraint information.

    Attributes:
        max_concurrency: Maximum concurrent operations allowed.
            None = unlimited, 1 = serial
        reason: Human-readable explanation for the constraint.
    """

    max_concurrency: Optional[int]
    reason: str = ""


@runtime_checkable
class ConcurrencyAware(Protocol):
    """
    Protocol for backend classes to provide concurrency limit hints to upper layers.

    Conventions:
    - Implement only on Backend classes, not on Dialect classes.
    - get_concurrency_hint() always returns synchronously;
      backends requiring runtime queries (e.g., MySQL) should fetch and cache during connect().
    - Return None if the backend imposes no constraint; the caller decides the strategy.
    """

    def get_concurrency_hint(self) -> Optional[ConcurrencyHint]: ...


class ConcurrencyAwareMixin:
    """
    Mixin for ConcurrencyAware protocol implementation.

    Provides a default implementation that returns None (no constraint).
    Subclasses should override get_concurrency_hint() to provide specific values.
    """

    def get_concurrency_hint(self) -> Optional[ConcurrencyHint]:
        """
        Get concurrency hint for this backend.

        Default implementation returns None (no constraint).
        Override in subclasses to provide specific concurrency limits.

        Returns:
            ConcurrencyHint with max_concurrency and reason, or None if unlimited.
        """
        return None

# src/rhosocial/activerecord/backend/partition/protocols.py
"""The verbs a partition-maintenance executor may offer.

Engines disagree about what maintenance means, so one protocol that declared
every verb would claim too much. MySQL has no ``validate``, ClickHouse has no
``ensure``, and SQL Server merges a boundary where PostgreSQL drops a range.
Each verb is therefore its own protocol, and a caller asks what an executor can
actually do with ``isinstance`` -- the same feature-detection pattern the
dialect protocols use.

The sync and async protocols declare the same method names, in keeping with the
project's parity rule; only the ``async`` keyword differs. Runtime checks see
that a method exists, not whether it is a coroutine, so callers detect the verb
they need and already know whether they hold a sync or an async executor.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from .types import PartitionReport


@runtime_checkable
class PartitionInventory(Protocol):
    """An executor that can read the live partition state."""

    def list(self, *args: Any, **kwargs: Any) -> PartitionReport:
        """Return the current partitions for *args* as a report."""
        ...  # pragma: no cover


@runtime_checkable
class AsyncPartitionInventory(Protocol):
    """An executor that can read the live partition state asynchronously."""

    async def list(self, *args: Any, **kwargs: Any) -> PartitionReport:
        """Return the current partitions for *args* as a report."""
        ...  # pragma: no cover


@runtime_checkable
class PartitionEnsurer(Protocol):
    """An executor that can create the partitions a plan is missing."""

    def ensure(self, plan: Any, *args: Any, **kwargs: Any) -> PartitionReport:
        """Reconcile *plan* with the catalogue and return a report."""
        ...  # pragma: no cover


@runtime_checkable
class AsyncPartitionEnsurer(Protocol):
    """An executor that can create missing partitions asynchronously."""

    async def ensure(self, plan: Any, *args: Any, **kwargs: Any) -> PartitionReport:
        """Reconcile *plan* with the catalogue and return a report."""
        ...  # pragma: no cover


@runtime_checkable
class PartitionRetention(Protocol):
    """An executor that can drop partitions older than a cutoff."""

    def drop_before(
        self, plan: Any, cutoff: Any, *args: Any, **kwargs: Any
    ) -> PartitionReport:
        """Drop the partitions the plan puts before *cutoff*."""
        ...  # pragma: no cover


@runtime_checkable
class AsyncPartitionRetention(Protocol):
    """An executor that can drop partitions older than a cutoff asynchronously."""

    async def drop_before(
        self, plan: Any, cutoff: Any, *args: Any, **kwargs: Any
    ) -> PartitionReport:
        """Drop the partitions the plan puts before *cutoff*."""
        ...  # pragma: no cover


@runtime_checkable
class PartitionValidator(Protocol):
    """An executor that can report gaps, overlaps and mismatches without repairing them."""

    def validate(self, plan: Any, *args: Any, **kwargs: Any) -> PartitionReport:
        """Return the plan's findings without changing the catalogue."""
        ...  # pragma: no cover


@runtime_checkable
class AsyncPartitionValidator(Protocol):
    """An executor that reports findings asynchronously."""

    async def validate(self, plan: Any, *args: Any, **kwargs: Any) -> PartitionReport:
        """Return the plan's findings without changing the catalogue."""
        ...  # pragma: no cover

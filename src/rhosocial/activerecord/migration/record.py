# src/rhosocial/activerecord/migration/record.py
"""Version records for the ActiveRecord-layer migration runner.

Records are AR-side state (not the backend migration system's records). The
default store is in-memory; applications may supply their own strategy.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Protocol, runtime_checkable


@dataclass(frozen=True)
class MigrationRecord:
    version: str
    direction: str
    applied_at: datetime
    success: bool = True
    error_message: Optional[str] = None


@runtime_checkable
class MigrationRecordStore(Protocol):
    def get_applied(self) -> List[str]: ...

    def record(self, entry: MigrationRecord) -> None: ...

    def is_applied(self, version: str) -> bool: ...


class InMemoryMigrationRecordStore:
    """Default record store; applied = successful UP minus successful DOWN."""

    def __init__(self) -> None:
        self._entries: List[MigrationRecord] = []

    def get_applied(self) -> List[str]:
        applied: List[str] = []
        for entry in self._entries:
            if not entry.success:
                continue
            if entry.direction == "up" and entry.version not in applied:
                applied.append(entry.version)
            elif entry.direction == "down" and entry.version in applied:
                applied.remove(entry.version)
        return applied

    def record(self, entry: MigrationRecord) -> None:
        self._entries.append(entry)

    def is_applied(self, version: str) -> bool:
        return version in self.get_applied()

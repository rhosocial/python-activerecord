# src/rhosocial/activerecord/backend/migration/record.py
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
import json


@dataclass
class MigrationRecord:
    version: str
    migration_fqn: str
    direction: str
    applied_at: datetime
    success: bool
    error_message: str | None = None
    snapshot_before: dict | None = None
    snapshot_after: dict | None = None


class MigrationRecordStore(ABC):
    @abstractmethod
    def get_applied(self) -> list[MigrationRecord]:
        """Return all successfully applied (direction=up) and not rolled-back records."""

    @abstractmethod
    def record(self, record: MigrationRecord) -> None:
        """Write a single execution record."""

    @abstractmethod
    def is_applied(self, version: str) -> bool:
        """Return True if the given version has been applied (up) and not rolled back."""


class JSONFileMigrationRecordStore(MigrationRecordStore):
    """File-based record store backed by a JSON file."""

    def __init__(self, path: str | Path):
        self._path = Path(path)
        self._records: list[MigrationRecord] = self._load()

    def _load(self) -> list[MigrationRecord]:
        if not self._path.exists():
            return []
        with self._path.open() as f:
            data = json.load(f)
        records = []
        for r in data:
            r["applied_at"] = datetime.fromisoformat(r["applied_at"])
            records.append(MigrationRecord(**r))
        return records

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w") as f:
            json.dump(
                [vars(r) for r in self._records],
                f,
                indent=2,
                default=_json_default,
            )

    def get_applied(self) -> list[MigrationRecord]:
        applied = {r.version for r in self._records if r.direction == "up" and r.success}
        rolled_back = {r.version for r in self._records if r.direction == "down" and r.success}
        return [r for r in self._records if r.version in (applied - rolled_back) and r.direction == "up"]

    def record(self, record: MigrationRecord) -> None:
        self._records.append(record)
        self._save()

    def is_applied(self, version: str) -> bool:
        return any(r.version == version for r in self.get_applied())


@dataclass
class MigrationResult:
    version: str
    applied_at: datetime
    success: bool
    dry_run: bool = False
    dry_run_sql: list[tuple[str, str, tuple]] | None = None
    snapshot_diff: Any = None


def _json_default(obj: Any) -> str:
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

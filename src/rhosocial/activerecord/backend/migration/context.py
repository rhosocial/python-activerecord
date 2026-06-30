# src/rhosocial/activerecord/backend/migration/context.py
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rhosocial.activerecord.backend.named_expression.procedure import (
    ProcedureContext,
    AsyncProcedureContext,
)

if TYPE_CHECKING:
    from .core import MigrationDirection


class MigrationContext(ProcedureContext):
    """Runtime context for named migration execution.

    Extends ``ProcedureContext`` with migration-specific fields: direction
    control, dry-run mode, and an optional record store reference.
    """

    def __init__(
        self,
        dialect: Any,
        execute_callback: Any,
        direction: MigrationDirection | None = None,
        dry_run: bool = False,
        record_store: object | None = None,
        **kwargs: Any,
    ):
        super().__init__(dialect, execute_callback, **kwargs)
        self.direction = direction
        self.dry_run = dry_run
        self.record_store = record_store


class AsyncMigrationContext(AsyncProcedureContext):
    """Async runtime context for named migration execution.

    Extends ``AsyncProcedureContext`` with migration-specific fields: direction
    control, dry-run mode, and an optional record store reference.
    """

    def __init__(
        self,
        dialect: Any,
        execute_callback: Any,
        direction: MigrationDirection | None = None,
        dry_run: bool = False,
        record_store: object | None = None,
        **kwargs: Any,
    ):
        super().__init__(dialect, execute_callback, **kwargs)
        self.direction = direction
        self.dry_run = dry_run
        self.record_store = record_store
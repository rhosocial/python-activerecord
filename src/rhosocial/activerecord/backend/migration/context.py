# src/rhosocial/activerecord/backend/migration/context.py
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rhosocial.activerecord.backend.named_expression.procedure import (
    AsyncProcedureContext,
    ProcedureContext,
)

if TYPE_CHECKING:  # pragma: no cover
    from .core import MigrationDirection


class MigrationContext(ProcedureContext):
    """Runtime context for a named migration.

    Adds migration-specific fields to ``ProcedureContext``: direction control,
    an optional record store reference, and the backend connection.
    """

    def __init__(
        self,
        dialect: Any,
        execute_callback: Any,
        direction: MigrationDirection | None = None,
        dry_run: bool = False,
        record_store: object | None = None,
        backend: Any = None,
        **kwargs: Any,
    ):
        super().__init__(
            dialect,
            execute_callback,
            backend=backend,
            dry_run=dry_run,
            **kwargs,
        )
        self.direction = direction
        self.dry_run = dry_run
        self.record_store = record_store

    def apply(self, *expressions: Any) -> int:
        """Execute DDL expressions, or record them during a dry run.

        Migration functions use this instead of touching the backend directly:
        a dry run never writes, and every rendered statement is available in
        ``ProcedureResult.dry_run_sql``.  A single list/tuple is accepted as
        well, so ``ctx.apply(create_statements(...))`` works.

        Returns:
            Number of statements applied or rendered.
        """
        if len(expressions) == 1 and isinstance(expressions[0], (list, tuple)):
            expressions = tuple(expressions[0])
        from rhosocial.activerecord.backend.options import ExecutionOptions
        from rhosocial.activerecord.backend.schema import StatementType

        options = ExecutionOptions(stmt_type=StatementType.DDL)
        count = 0
        for expression in expressions:
            sql, params = expression.to_sql()
            if self.dry_run:
                version = getattr(self, "version", None)
                label = (
                    f"{version} {type(expression).__name__}"
                    if version
                    else type(expression).__name__
                )
                self._record_dry_run(label, sql, params)
                count += 1
                continue
            backend = self.backend
            if backend is None:
                raise RuntimeError("A migration context needs a backend to apply DDL")
            backend.execute(sql, params, options=options)
            count += 1
        return count


class AsyncMigrationContext(AsyncProcedureContext):
    """Async counterpart of :class:`MigrationContext`."""

    def __init__(
        self,
        dialect: Any,
        execute_callback: Any,
        direction: MigrationDirection | None = None,
        dry_run: bool = False,
        record_store: object | None = None,
        backend: Any = None,
        **kwargs: Any,
    ):
        super().__init__(
            dialect,
            execute_callback,
            backend=backend,
            dry_run=dry_run,
            **kwargs,
        )
        self.direction = direction
        self.dry_run = dry_run
        self.record_store = record_store

    async def apply(self, *expressions: Any) -> int:
        """Asynchronous counterpart of :meth:`MigrationContext.apply`."""
        if len(expressions) == 1 and isinstance(expressions[0], (list, tuple)):
            expressions = tuple(expressions[0])
        from rhosocial.activerecord.backend.options import ExecutionOptions
        from rhosocial.activerecord.backend.schema import StatementType

        options = ExecutionOptions(stmt_type=StatementType.DDL)
        count = 0
        for expression in expressions:
            sql, params = expression.to_sql()
            if self.dry_run:
                version = getattr(self, "version", None)
                label = (
                    f"{version} {type(expression).__name__}"
                    if version
                    else type(expression).__name__
                )
                self._record_dry_run(label, sql, params)
                count += 1
                continue
            backend = self.backend
            if backend is None:
                raise RuntimeError("A migration context needs a backend to apply DDL")
            await backend.execute(sql, params, options=options)
            count += 1
        return count

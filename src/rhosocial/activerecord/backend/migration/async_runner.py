# src/rhosocial/activerecord/backend/migration/async_runner.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from rhosocial.activerecord.backend.dialect.exceptions import (
    ProtocolNotImplementedError,
    UnsupportedFeatureError,
)
from rhosocial.activerecord.backend.named_expression.resolver import (
    resolve_named_expression,
)

from .context import AsyncMigrationContext
from .core import AsyncNamedMigration, MigrationDirection
from .exceptions import (
    MigrationAlreadyAppliedError,
    MigrationDependencyError,
    MigrationDialectError,
    MigrationNotAppliedError,
    MigrationVersionConflictError,
)
from .record import MigrationRecord, MigrationResult, MigrationRecordStore
from .resolver import AsyncNamedMigrationResolver
from .snapshot import compute_schema_diff, snapshot_to_dict, take_async_snapshot


class AsyncMigrationRunner:
    """Orchestrates a single named migration execution asynchronously.

    Mirrors ``MigrationRunner`` with async counterparts for all I/O
    operations.  Follows the same pattern as ``AsyncProcedureRunner``.

    Only accepts :class:`AsyncNamedMigration` subclasses; synchronous
    :class:`NamedMigration` subclasses must use :class:`MigrationRunner`.
    """

    def __init__(
        self,
        migration_fqn: str,
    ):
        self._fqn = migration_fqn
        self._cls = AsyncNamedMigrationResolver.resolve(migration_fqn)
        self._migration = self._cls()
        self._params_info = self._cls.get_parameters()

    @property
    def migration(self) -> AsyncNamedMigration:
        return self._migration

    async def run(
        self,
        backend: Any,
        direction: MigrationDirection,
        user_params: dict[str, Any] | None = None,
        record_store: MigrationRecordStore | None = None,
        dry_run: bool = False,
        manage_transaction: bool = True,
    ) -> MigrationResult:
        # 0. Apply user_params to the migration instance
        user_params = user_params or {}
        for name, value in user_params.items():
            if name in self._params_info:
                setattr(self._migration, name, value)

        # 1. Dependency check (skip during dry-run)
        if record_store and not dry_run:
            for dep in self._migration.dependencies:
                if not record_store.is_applied(dep):
                    raise MigrationDependencyError(
                        f"Dependency '{dep}' has not been applied, "
                        f"cannot execute '{self._migration.version}'"
                    )

        # 3. Duplicate execution protection (skip during dry-run)
        if record_store and not dry_run:
            already_applied = record_store.is_applied(self._migration.version)
            if direction == MigrationDirection.UP and already_applied:
                raise MigrationAlreadyAppliedError(
                    f"Migration '{self._migration.version}' has already been applied"
                )
            if direction == MigrationDirection.DOWN and not already_applied:
                raise MigrationNotAppliedError(
                    f"Migration '{self._migration.version}' has not been applied, "
                    f"cannot rollback"
                )

        # 4. Snapshot before
        snapshot_before = await take_async_snapshot(backend) if not dry_run else None

        # 5. Build execute callback based on dry_run flag
        dialect = getattr(backend, "dialect", None)
        collected_sql: list[tuple[str, str, tuple]] | None = [] if dry_run else None

        if dry_run:
            async def execute_callback(
                fqn: str, dial: Any, params: dict[str, Any]
            ) -> dict[str, Any]:
                expr = resolve_named_expression(fqn, dial, params or {})
                sql, params_sql = expr.to_sql()  # raises UnsupportedFeatureError if incompatible
                collected_sql.append((fqn, sql, params_sql))  # type: ignore[union-attr]
                return {"sql": sql, "params_sql": params_sql}
        else:
            backend_execute = getattr(backend, "execute", None)

            async def execute_callback(
                fqn: str, dial: Any, params: dict[str, Any]
            ) -> dict[str, Any]:
                expr = resolve_named_expression(fqn, dial, params)
                sql, params_sql = expr.to_sql()
                data, affected_rows = [], 0
                if backend_execute and sql:
                    stmt_type = getattr(expr, "statement_type", None)
                    if stmt_type:
                        from rhosocial.activerecord.backend.options import (
                            ExecutionOptions,
                        )

                        raw = await backend_execute(
                            sql,
                            params_sql,
                            options=ExecutionOptions(stmt_type=stmt_type),
                        )
                    else:
                        raw = await backend_execute(sql, params_sql)
                    if raw and raw.data:
                        data = raw.data
                    if raw:
                        affected_rows = raw.affected_rows or 0
                return {
                    "sql": sql,
                    "params_sql": params_sql,
                    "data": data,
                    "affected_rows": affected_rows,
                }

        # 6. Execute via AsyncMigrationContext
        ctx = AsyncMigrationContext(
            dialect=dialect,
            execute_callback=execute_callback,
            direction=direction,
            dry_run=dry_run,
            record_store=record_store,
        )

        error = None
        in_transaction = False

        async def begin_transaction():
            nonlocal in_transaction
            if backend and not in_transaction:
                await backend.begin_transaction()
                in_transaction = True
                ctx._in_transaction = True

        async def commit_transaction():
            nonlocal in_transaction
            if backend and in_transaction:
                await backend.commit_transaction()
                in_transaction = False
                ctx._in_transaction = False

        async def rollback_transaction():
            nonlocal in_transaction
            if backend and in_transaction:
                await backend.rollback_transaction()
                in_transaction = False
                ctx._in_transaction = False

        ctx._begin_transaction = begin_transaction
        ctx._commit_transaction = commit_transaction
        ctx._rollback_transaction = rollback_transaction

        try:
            if manage_transaction and not dry_run:
                await begin_transaction()
            await self._migration.run(ctx)  # always run — dry-run callback handles no-execution
            if manage_transaction and in_transaction:
                await commit_transaction()
        except (ProtocolNotImplementedError, UnsupportedFeatureError) as e:
            if not dry_run and in_transaction and manage_transaction:
                try:
                    await rollback_transaction()
                except Exception:
                    pass
            error = MigrationDialectError(str(e))
        except Exception as e:
            if not dry_run and in_transaction and manage_transaction:
                try:
                    await rollback_transaction()
                except Exception:
                    pass
            error = e

        # 7. Snapshot after
        snapshot_after = None
        if not dry_run and error is None:
            snapshot_after = await take_async_snapshot(backend)

        # 8. Version conflict check
        if not dry_run and record_store:
            for existing in record_store.get_applied():
                if (
                    existing.version == self._migration.version
                    and existing.migration_fqn != self._fqn
                ):
                    raise MigrationVersionConflictError(
                        f"Version '{self._migration.version}' already exists "
                        f"from '{existing.migration_fqn}', "
                        f"cannot record from '{self._fqn}'"
                    )

        # 9. Record
        if not dry_run and record_store:
            success = error is None
            record = MigrationRecord(
                version=self._migration.version,
                migration_fqn=self._fqn,
                direction=direction.value,
                applied_at=datetime.now(timezone.utc),
                success=success,
                error_message=str(error) if error else None,
                snapshot_before=snapshot_to_dict(snapshot_before),
                snapshot_after=snapshot_to_dict(snapshot_after),
            )
            record_store.record(record)

        if error:
            raise error

        snapshot_diff = compute_schema_diff(snapshot_before, snapshot_after, dialect)

        return MigrationResult(
            version=self._migration.version,
            applied_at=datetime.now(timezone.utc),
            success=True,
            dry_run=dry_run,
            dry_run_sql=collected_sql,
            snapshot_diff=snapshot_diff,
        )
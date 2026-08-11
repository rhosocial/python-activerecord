# src/rhosocial/activerecord/backend/migration/runner.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from rhosocial.activerecord.backend.dialect.exceptions import (
    ProtocolNotImplementedError,
    UnsupportedFeatureError,
)
from rhosocial.activerecord.backend.named_expression.procedure import (
    _build_execute_callback,
)

from .context import MigrationContext
from .core import MigrationDirection, NamedMigration
from rhosocial.activerecord.backend.migration.exceptions import (
    MigrationAlreadyAppliedError,
    MigrationDependencyError,
    MigrationDialectError,
    MigrationNotAppliedError,
    MigrationVersionConflictError,
)
from .record import MigrationRecord, MigrationResult, MigrationRecordStore
from .resolver import NamedMigrationResolver


class MigrationRunner:
    """Orchestrates a single named migration execution.

    Encapsulates the procedure execution pattern from ``ProcedureRunner``
    and adds migration-specific concerns: dependency checking, duplicate
    protection, optional schema snapshots, and optional record keeping.
    """

    def __init__(
        self,
        migration_fqn: str,
    ):
        self._fqn = migration_fqn
        self._cls = NamedMigrationResolver.resolve(migration_fqn)
        self._migration = self._cls()
        self._params_info = self._cls.get_parameters()

    @property
    def migration(self) -> NamedMigration:
        return self._migration

    def run(
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

        # 1. Dependency check (skip during dry-run — record_store may be empty)
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
        snapshot_before = _take_sync_snapshot(backend) if not dry_run else None

        # 5. Build execute callback and execute via MigrationContext
        dialect = getattr(backend, "dialect", None)
        collected_sql: list[tuple[str, str, tuple]] | None = [] if dry_run else None

        if dry_run:
            from rhosocial.activerecord.backend.named_expression.resolver import (
                resolve_named_expression,
            )

            def execute_callback(
                fqn: str, dial: Any, params: dict[str, Any]
            ) -> dict[str, Any]:
                expr = resolve_named_expression(fqn, dial, params or {})
                sql, params_sql = expr.to_sql()  # raises UnsupportedFeatureError if incompatible
                collected_sql.append((fqn, sql, params_sql))  # type: ignore[union-attr]
                return {"sql": sql, "params_sql": params_sql}
        else:
            execute_callback = _build_execute_callback(backend)

        ctx = MigrationContext(
            dialect=dialect,
            execute_callback=execute_callback,
            direction=direction,
            dry_run=dry_run,
            record_store=record_store,
        )

        error = None
        in_transaction = False

        def begin_transaction():
            nonlocal in_transaction
            if backend and not in_transaction:
                backend.begin_transaction()
                in_transaction = True
                ctx._in_transaction = True

        def commit_transaction():
            nonlocal in_transaction
            if backend and in_transaction:
                backend.commit_transaction()
                in_transaction = False
                ctx._in_transaction = False

        def rollback_transaction():
            nonlocal in_transaction
            if backend and in_transaction:
                backend.rollback_transaction()
                in_transaction = False
                ctx._in_transaction = False

        ctx._begin_transaction = begin_transaction
        ctx._commit_transaction = commit_transaction
        ctx._rollback_transaction = rollback_transaction

        try:
            if manage_transaction and not dry_run:
                begin_transaction()
            self._migration.run(ctx)  # always run — dry-run callback handles no-execution
            if manage_transaction and in_transaction:
                commit_transaction()
        except (ProtocolNotImplementedError, UnsupportedFeatureError) as e:
            if not dry_run and in_transaction and manage_transaction:
                try:
                    rollback_transaction()
                except Exception:
                    pass
            error = MigrationDialectError(str(e))
        except Exception as e:
            if not dry_run and in_transaction and manage_transaction:
                try:
                    rollback_transaction()
                except Exception:
                    pass
            error = e

        # 6. Snapshot after
        snapshot_after = None
        if not dry_run and error is None:
            snapshot_after = _take_sync_snapshot(backend)

        # 7. Version conflict check (duplicate version, different FQN)
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

        # 8. Record
        if not dry_run and record_store:
            success = error is None
            record = MigrationRecord(
                version=self._migration.version,
                migration_fqn=self._fqn,
                direction=direction.value,
                applied_at=datetime.now(timezone.utc),
                success=success,
                error_message=str(error) if error else None,
                snapshot_before=_snapshot_to_dict(snapshot_before),
                snapshot_after=_snapshot_to_dict(snapshot_after),
            )
            record_store.record(record)

        if error:
            raise error

        snapshot_diff = _compute_diff(snapshot_before, snapshot_after)

        return MigrationResult(
            version=self._migration.version,
            applied_at=datetime.now(timezone.utc),
            success=True,
            dry_run=dry_run,
            dry_run_sql=collected_sql,
            snapshot_diff=snapshot_diff,
        )


def _take_sync_snapshot(backend: Any) -> Any | None:
    """Capture a schema snapshot via the backend's introspector and dialect sync."""
    try:
        introspector = getattr(backend, "introspector", None)
        dialect = getattr(backend, "dialect", None)
        if introspector is None or dialect is None:
            return None
        from rhosocial.activerecord.backend.schema import SyncSchemaSnapshotBuilder

        builder = SyncSchemaSnapshotBuilder(introspector, dialect)
        return builder.build()
    except Exception:
        return None


def _snapshot_to_dict(snapshot: Any) -> dict | None:
    if snapshot is None:
        return None
    try:
        return snapshot.to_dict()
    except Exception:
        return None


def _compute_diff(before: Any, after: Any) -> Any | None:
    if before is None or after is None:
        return None
    try:
        dialect_class = getattr(type(before), "dialect_class", before) if hasattr(before, "dialect_class") else ""
        cls_lower = dialect_class.lower() if isinstance(dialect_class, str) else ""

        differ = _resolve_schema_differ(cls_lower)
        return differ.compare(before, after)
    except Exception:
        return None


def _resolve_schema_differ(dialect_class: str):
    """Resolve the appropriate schema differ for the given dialect class name."""
    from rhosocial.activerecord.backend.schema.differ import SchemaDiffer

    if "sqlite" in dialect_class:
        try:
            from rhosocial.activerecord.backend.impl.sqlite.schema.differ import (
                SQLiteSchemaDiffer,
            )
            return SQLiteSchemaDiffer()
        except ImportError:
            pass
    elif "mysql" in dialect_class:
        try:
            from rhosocial.activerecord.backend.impl.mysql.schema.differ import (
                MySQLSchemaDiffer,
            )
            return MySQLSchemaDiffer()
        except ImportError:
            pass
    elif "postgres" in dialect_class:
        try:
            from rhosocial.activerecord.backend.impl.postgres.schema.differ import (
                PostgresSchemaDiffer,
            )
            return PostgresSchemaDiffer()
        except ImportError:
            pass
    elif "sqlserver" in dialect_class:
        try:
            from rhosocial.activerecord.backend.impl.sqlserver.schema.differ import (
                SQLServerSchemaDiffer,
            )
            return SQLServerSchemaDiffer()
        except ImportError:
            pass
    return SchemaDiffer()

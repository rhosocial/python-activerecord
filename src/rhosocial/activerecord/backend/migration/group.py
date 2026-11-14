# src/rhosocial/activerecord/backend/migration/group.py
"""Reusable execution of a group of ``@migration`` functions.

The CLI and applications that already hold a backend use this module instead
of re-implementing ordering, dependency checks, transactions, dry-run capture
and version recording.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List, Optional, Sequence

from rhosocial.activerecord.backend.named_expression.procedure import (
    AsyncProcedure,
    AsyncProcedureRunner,
    Procedure,
    ProcedureRunner,
    TransactionMode,
)

from .context import AsyncMigrationContext, MigrationContext
from .core import MigrationDirection
from .exceptions import (
    MigrationAlreadyAppliedError,
    MigrationDependencyError,
    MigrationError,
    MigrationFunctionExecutionError,
    MigrationNotAppliedError,
    MigrationVersionConflictError,
)
from .functions import (
    MigrationFunctionRef,
    MigrationInfo,
    resolve_migration_function,
)
from .record import MigrationRecord, MigrationRecordStore

__all__ = [
    "MigrationGroupResult",
    "DryRunBackend",
    "AsyncDryRunBackend",
    "select_async_functions",
    "run_migration_group",
    "run_migration_group_async",
]


@dataclass
class MigrationGroupResult:
    """Outcome of one migration group."""

    direction: MigrationDirection
    dry_run: bool
    versions: List[str] = field(default_factory=list)
    applied: List[str] = field(default_factory=list)
    rolled_back: List[str] = field(default_factory=list)
    dry_run_sql: List[tuple] = field(default_factory=list)
    dry_run_total: int = 0
    records_written: List[str] = field(default_factory=list)


class _DryRunResult:
    """Minimal execution result returned by a dry-run backend."""

    def __init__(self, sql: str, params: Any) -> None:
        self.sql = sql
        self.params = params
        self.data: List[Any] = []
        self.affected_rows = 0
        self.rowcount = 0
        self.last_insert_id = None


class DryRunBackend:
    """Sync proxy that records writes instead of executing them."""

    def __init__(self, backend: Any, recorder) -> None:
        self._backend = backend
        self._recorder = recorder

    @property
    def dialect(self) -> Any:
        return self._backend.dialect

    def execute(self, sql: str, params=None, options=None):
        self._recorder("backend.execute", sql, params or ())
        return _DryRunResult(sql, params)

    def begin_transaction(self, *args, **kwargs) -> None:
        return None

    def commit_transaction(self, *args, **kwargs) -> None:
        return None

    def rollback_transaction(self, *args, **kwargs) -> None:
        return None

    def __getattr__(self, name: str) -> Any:
        return getattr(self._backend, name)


class AsyncDryRunBackend(DryRunBackend):
    """Asynchronous counterpart of :class:`DryRunBackend`."""

    async def execute(self, sql: str, params=None, options=None):
        self._recorder("backend.execute", sql, params or ())
        return _DryRunResult(sql, params)

    async def begin_transaction(self, *args, **kwargs) -> None:
        return None

    async def commit_transaction(self, *args, **kwargs) -> None:
        return None

    async def rollback_transaction(self, *args, **kwargs) -> None:
        return None


def _as_ref(function: Any) -> MigrationFunctionRef:
    """Accept a resolved ref, an FQN, or a decorated callable."""
    if isinstance(function, MigrationFunctionRef):
        return function
    if isinstance(function, str):
        return resolve_migration_function(function)
    info = getattr(function, "__migration__", None)
    if not isinstance(info, MigrationInfo):
        raise MigrationError(
            "Migration group entries must be MigrationFunctionRef, FQN, or "
            "a callable decorated with @migration"
        )
    owner = getattr(function, "__self__", None)
    if not isinstance(owner, type):
        owner = None
    module = getattr(function, "__module__", "")
    qualname = getattr(function, "__qualname__", getattr(function, "__name__", ""))
    return MigrationFunctionRef(
        fqn=f"{module}:{qualname}",
        function=function,
        info=info,
        owner=owner,
        is_async=inspect.iscoroutinefunction(function),
    )


def _refs(functions: Sequence[Any]) -> List[MigrationFunctionRef]:
    resolved = [_as_ref(function) for function in functions]
    if not resolved:
        raise MigrationError("A migration group needs at least one function")
    return resolved


def select_async_functions(functions: Sequence[Any]) -> List[MigrationFunctionRef]:
    """Resolve sync functions to their declared async variants.

    A sync function may name an ``async_variant`` FQN.  The returned ref keeps
    the sync function's FQN as the canonical record key, so sync and async
    executions share one version identity instead of colliding in a record
    store.
    """
    selected = []
    for ref in _refs(functions):
        if ref.is_async:
            selected.append(ref)
            continue
        if not ref.info.async_variant:
            raise MigrationError(
                f'Migration function "{ref.fqn}" is synchronous and declares no '
                "async_variant; pass an async function or add async_variant to "
                "@migration"
            )
        variant = resolve_migration_function(ref.info.async_variant)
        if not variant.is_async:
            raise MigrationError(
                f'async_variant "{variant.fqn}" of "{ref.fqn}" is not an ' "asynchronous function"
            )
        if variant.info.version != ref.info.version:
            raise MigrationError(
                f'async_variant "{variant.fqn}" declares version '
                f'"{variant.info.version}", but "{ref.fqn}" declares '
                f'"{ref.info.version}"'
            )
        selected.append(
            MigrationFunctionRef(
                fqn=ref.fqn,
                function=variant.function,
                info=ref.info,
                owner=variant.owner if variant.owner is not None else ref.owner,
                is_async=True,
            )
        )
    return selected


def _ordered(
    functions: Sequence[MigrationFunctionRef],
    direction: MigrationDirection,
) -> List[MigrationFunctionRef]:
    ordered = list(functions)
    if direction == MigrationDirection.DOWN:
        ordered.reverse()
    return ordered


def _validate(
    ordered: Sequence[MigrationFunctionRef],
    direction: MigrationDirection,
    record_store: Optional[MigrationRecordStore],
) -> None:
    versions = {}
    for function in ordered:
        version = function.info.version
        if version in versions:
            raise MigrationError(
                f'Duplicate migration version "{version}" in one group: '
                f"{versions[version]} and {function.fqn}"
            )
        versions[version] = function.fqn

    applied = {}
    if record_store is not None:
        applied = {record.version: record.migration_fqn for record in record_store.get_applied()}

    for function in ordered:
        existing = applied.get(function.info.version)
        if existing and existing != function.fqn:
            raise MigrationVersionConflictError(
                f'Version "{function.info.version}" is already recorded for '
                f"{existing}, not {function.fqn}"
            )

    if direction == MigrationDirection.UP:
        earlier = set()
        for function in ordered:
            if record_store is not None and record_store.is_applied(function.info.version):
                raise MigrationAlreadyAppliedError(
                    f'Migration "{function.info.version}" is already applied'
                )
            for dependency in function.info.dependencies:
                if dependency in earlier:
                    continue
                if record_store is not None and record_store.is_applied(dependency):
                    continue
                raise MigrationDependencyError(
                    f'Migration "{function.info.version}" depends on '
                    f'"{dependency}", which is neither earlier in this group '
                    "nor recorded as applied"
                )
            earlier.add(function.info.version)
    elif record_store is not None:
        for function in ordered:
            if not record_store.is_applied(function.info.version):
                raise MigrationNotAppliedError(
                    f'Migration "{function.info.version}" is not applied; ' "nothing to roll back"
                )


def _record(
    ordered: Sequence[MigrationFunctionRef],
    direction: MigrationDirection,
    record_store: Optional[MigrationRecordStore],
) -> List[str]:
    if record_store is None:
        return []
    now = datetime.now(timezone.utc)
    written = []
    for function in ordered:
        record_store.record(
            MigrationRecord(
                version=function.info.version,
                migration_fqn=function.fqn,
                direction=direction.value,
                applied_at=now,
                success=True,
            )
        )
        written.append(function.info.version)
    return written


def _invalidate_introspection(backend: Any) -> None:
    """Drop cached table metadata after DDL changed the schema."""
    introspector = getattr(backend, "introspector", None)
    clear = getattr(introspector, "clear_cache", None)
    if callable(clear):
        clear()


def _transactional_ddl(backend: Any) -> bool:
    """Report whether the backend can roll DDL back inside a transaction."""
    dialect = getattr(backend, "dialect", None)
    probe = getattr(dialect, "supports_transactional_ddl", None)
    if callable(probe):
        try:
            return bool(probe())
        except Exception:
            return True
    return True


def _sync_procedure(functions: Sequence[MigrationFunctionRef]) -> type:
    def run(self, ctx) -> None:
        if getattr(ctx, "backend", None) is None:
            return
        executed = getattr(type(self), "executed", [])
        for function in self.functions:
            ctx.version = function.info.version
            try:
                function.function(ctx)
            except Exception as exc:
                failure = MigrationFunctionExecutionError(
                    function.info.version,
                    function.fqn,
                    exc,
                    executed=executed,
                )
                failure.transactional_ddl = _transactional_ddl(ctx.backend)
                type(self).failure = failure
                raise failure from exc
            executed.append(function.info.version)

    return type(
        "MigrationFunctionGroup",
        (Procedure,),
        {"run": run, "functions": tuple(functions)},
    )


def _async_procedure(functions: Sequence[MigrationFunctionRef]) -> type:
    async def run(self, ctx) -> None:
        if getattr(ctx, "backend", None) is None:
            return
        executed = getattr(type(self), "executed", [])
        for function in self.functions:
            ctx.version = function.info.version
            try:
                await function.function(ctx)
            except Exception as exc:
                failure = MigrationFunctionExecutionError(
                    function.info.version,
                    function.fqn,
                    exc,
                    executed=executed,
                )
                failure.transactional_ddl = _transactional_ddl(ctx.backend)
                type(self).failure = failure
                raise failure from exc
            executed.append(function.info.version)

    return type(
        "AsyncMigrationFunctionGroup",
        (AsyncProcedure,),
        {"run": run, "functions": tuple(functions)},
    )


def _swap_models(functions: Sequence[MigrationFunctionRef], backend) -> List[tuple]:
    replaced = []
    for model in {ref.owner for ref in functions if ref.owner is not None}:
        replaced.append((model, getattr(model, "__backend__", None)))
        model.__backend__ = backend
    return replaced


def _restore_models(replaced: Sequence[tuple]) -> None:
    for model, previous in replaced:
        model.__backend__ = previous


def _check_backend_kind(function: MigrationFunctionRef, is_async: bool) -> None:
    if function.is_async != is_async:
        raise MigrationError(
            f'Migration function "{function.fqn}" is '
            f"{'asynchronous' if function.is_async else 'synchronous'}, but "
            f"the {('async' if is_async else 'sync')} runner was selected"
        )


def run_migration_group(
    backend,
    functions: Sequence[Any],
    *,
    direction: MigrationDirection = MigrationDirection.UP,
    record_store: Optional[MigrationRecordStore] = None,
    dry_run: bool = False,
    transaction_mode: TransactionMode = TransactionMode.AUTO,
) -> MigrationGroupResult:
    """Run a synchronous migration group."""
    resolved = _refs(functions)
    for function in resolved:
        _check_backend_kind(function, False)
    ordered = _ordered(resolved, direction)
    _validate(ordered, direction, record_store)

    holder = {}
    proxy = None
    replaced = []
    if dry_run:

        def record(label: str, sql: str, params: Any) -> None:
            ctx = holder.get("ctx")
            if ctx is not None:
                ctx._record_dry_run(label, sql, params)

        proxy = DryRunBackend(backend, record)
        replaced = _swap_models(ordered, proxy)

    def context_factory(**kwargs):
        ctx = MigrationContext(
            direction=direction,
            record_store=record_store,
            **kwargs,
        )
        holder["ctx"] = ctx
        return ctx

    procedure_class = _sync_procedure(ordered)
    procedure_class.failure = None
    procedure_class.executed = []
    try:
        result = ProcedureRunner(procedure_class=procedure_class).run(
            proxy or backend,
            transaction_mode=transaction_mode,
            dry_run=dry_run,
            context_factory=context_factory,
        )
    finally:
        if replaced:
            _restore_models(replaced)
        _invalidate_introspection(backend)

    if result.aborted:
        failure = getattr(procedure_class, "failure", None)
        if failure is not None:
            raise failure
        raise MigrationError(f"Migration group failed: {result.abort_reason}")

    written = [] if dry_run else _record(ordered, direction, record_store)
    versions = [function.info.version for function in ordered]
    return MigrationGroupResult(
        direction=direction,
        dry_run=dry_run,
        versions=versions,
        applied=versions if direction == MigrationDirection.UP and not dry_run else [],
        rolled_back=(versions if direction == MigrationDirection.DOWN and not dry_run else []),
        dry_run_sql=list(result.dry_run_sql),
        dry_run_total=result.dry_run_total,
        records_written=written,
    )


async def run_migration_group_async(
    backend,
    functions: Sequence[Any],
    *,
    direction: MigrationDirection = MigrationDirection.UP,
    record_store: Optional[MigrationRecordStore] = None,
    dry_run: bool = False,
    transaction_mode: TransactionMode = TransactionMode.AUTO,
) -> MigrationGroupResult:
    """Asynchronous counterpart of :func:`run_migration_group`."""
    resolved = select_async_functions(functions)
    for function in resolved:
        _check_backend_kind(function, True)
    ordered = _ordered(resolved, direction)
    _validate(ordered, direction, record_store)

    holder = {}
    proxy = None
    replaced = []
    if dry_run:

        def record(label: str, sql: str, params: Any) -> None:
            ctx = holder.get("ctx")
            if ctx is not None:
                ctx._record_dry_run(label, sql, params)

        proxy = AsyncDryRunBackend(backend, record)
        replaced = _swap_models(ordered, proxy)

    def context_factory(**kwargs):
        ctx = AsyncMigrationContext(
            direction=direction,
            record_store=record_store,
            **kwargs,
        )
        holder["ctx"] = ctx
        return ctx

    procedure_class = _async_procedure(ordered)
    procedure_class.failure = None
    procedure_class.executed = []
    try:
        result = await AsyncProcedureRunner(procedure_class=procedure_class).run(
            proxy or backend,
            transaction_mode=transaction_mode,
            dry_run=dry_run,
            context_factory=context_factory,
        )
    finally:
        if replaced:
            _restore_models(replaced)
        _invalidate_introspection(backend)

    if result.aborted:
        failure = getattr(procedure_class, "failure", None)
        if failure is not None:
            raise failure
        raise MigrationError(f"Migration group failed: {result.abort_reason}")

    written = [] if dry_run else _record(ordered, direction, record_store)
    versions = [function.info.version for function in ordered]
    return MigrationGroupResult(
        direction=direction,
        dry_run=dry_run,
        versions=versions,
        applied=versions if direction == MigrationDirection.UP and not dry_run else [],
        rolled_back=(versions if direction == MigrationDirection.DOWN and not dry_run else []),
        dry_run_sql=list(result.dry_run_sql),
        dry_run_total=result.dry_run_total,
        records_written=written,
    )

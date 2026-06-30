# src/rhosocial/activerecord/backend/migration/batch_runner.py
from __future__ import annotations

from typing import Any

from .core import MigrationDirection
from .exceptions import (
    MigrationDependencyError,
    MigrationVersionConflictError,
)
from .record import MigrationResult, MigrationRecordStore


class BatchMigrationRunner:
    """Runs multiple migrations in dependency order.

    Discovers ``NamedMigration`` subclasses in a module, topologically
    sorts them by their ``dependencies`` declarations, and runs them in
    sequence.
    """

    def __init__(
        self,
        module_name: str,
    ):
        self._module_name = module_name
        self._migrations: list[tuple[str, str, list[str]]] = []
        self._discover()

    def _discover(self) -> None:
        import importlib

        from .core import NamedMigration

        module = importlib.import_module(self._module_name)
        for name in dir(module):
            if name.startswith("_"):
                continue
            obj = getattr(module, name, None)
            if obj is None:
                continue
            if (
                isinstance(obj, type)
                and issubclass(obj, NamedMigration)
                and obj is not NamedMigration
            ):
                version = getattr(obj, "version", "")
                dependencies = getattr(obj, "dependencies", [])
                fqn = f"{self._module_name}.{name}"
                self._migrations.append((version, fqn, list(dependencies)))

    @property
    def discovered(self) -> list[dict[str, Any]]:
        return [
            {"version": v, "fqn": fqn, "dependencies": deps}
            for v, fqn, deps in self._migrations
        ]

    def _topological_order(self) -> list[tuple[str, str, list[str]]]:
        version_to_fqn: dict[str, str] = {v: fqn for v, fqn, _ in self._migrations}
        fqn_order: list[tuple[str, str, list[str]]] = []
        visited: set[str] = set()

        def visit(v: str, fqn: str, deps: list[str]) -> None:
            if v in visited:
                raise MigrationVersionConflictError(
                    f"Circular dependency detected involving version '{v}'"
                )
            visited.add(v)
            for dep in deps:
                if dep in version_to_fqn:
                    dep_fqn = version_to_fqn[dep]
                    dep_deps = next(
                        (d for vv, _, d in self._migrations if vv == dep), []
                    )
                    if dep not in {r[0] for r in fqn_order}:
                        visit(dep, dep_fqn, dep_deps)
                else:
                    raise MigrationDependencyError(
                        f"Dependency '{dep}' required by '{v}' not found in module"
                    )
            fqn_order.append((v, fqn, deps))

        for version, fqn, deps in self._migrations:
            if version not in {r[0] for r in fqn_order}:
                visit(version, fqn, deps)

        return fqn_order

    def migrate_up(
        self,
        backend: Any,
        record_store: MigrationRecordStore | None = None,
        user_params: dict[str, Any] | None = None,
        target_version: str | None = None,
        dry_run: bool = False,
        single_transaction: bool = False,
    ) -> list[MigrationResult]:
        """Run all pending UP migrations in dependency order.

        Args:
            backend: The database backend.
            record_store: Optional record store for dependency/duplicate checks.
            user_params: Optional user parameters shared across migrations.
            target_version: If set, stop after this version is applied.
            dry_run: Skip actual execution.
            single_transaction: If True, wrap all migrations in a single
                database transaction.  On failure the entire batch is
                rolled back and no records are written.  Records are
                written only after the final commit.

        Returns:
            List of ``MigrationResult`` for each migration attempted.
        """
        return self._run(
            backend, MigrationDirection.UP, record_store, user_params,
            target_version, dry_run, single_transaction,
        )

    def migrate_down(
        self,
        backend: Any,
        record_store: MigrationRecordStore | None = None,
        user_params: dict[str, Any] | None = None,
        target_version: str | None = None,
        dry_run: bool = False,
        single_transaction: bool = False,
    ) -> list[MigrationResult]:
        """Run DOWN migrations in reverse dependency order.

        Args:
            backend: The database backend.
            record_store: Optional record store for applied-status checks.
            user_params: Optional user parameters.
            target_version: If set, stop after this version is rolled back (exclusive).
            dry_run: Skip actual execution.
            single_transaction: If True, wrap all migrations in a single
                database transaction.

        Returns:
            List of ``MigrationResult`` for each migration rolled back.
        """
        return self._run(
            backend, MigrationDirection.DOWN, record_store, user_params,
            target_version, dry_run, single_transaction,
        )

    def _run(
        self,
        backend: Any,
        direction: MigrationDirection,
        record_store: MigrationRecordStore | None = None,
        user_params: dict[str, Any] | None = None,
        target_version: str | None = None,
        dry_run: bool = False,
        single_transaction: bool = False,
    ) -> list[MigrationResult]:
        from .runner import MigrationRunner

        ordered = self._topological_order()
        if direction == MigrationDirection.DOWN:
            ordered = list(reversed(ordered))

        in_outer_transaction = False

        def begin_outer():
            nonlocal in_outer_transaction
            if single_transaction and not dry_run and not in_outer_transaction:
                backend.begin_transaction()
                in_outer_transaction = True

        def commit_outer():
            nonlocal in_outer_transaction
            if in_outer_transaction:
                backend.commit_transaction()
                in_outer_transaction = False

        def rollback_outer():
            nonlocal in_outer_transaction
            if in_outer_transaction:
                try:
                    backend.rollback_transaction()
                except Exception:
                    pass
                in_outer_transaction = False

        results: list[MigrationResult] = []

        try:
            begin_outer()
            for version, fqn, _ in ordered:
                if target_version is not None and direction == MigrationDirection.UP and version > target_version:
                    break
                if target_version is not None and direction == MigrationDirection.DOWN and version <= target_version:
                    break
                runner = MigrationRunner(fqn)
                result = runner.run(
                    backend=backend,
                    direction=direction,
                    user_params=user_params,
                    record_store=record_store,
                    dry_run=dry_run,
                    manage_transaction=not single_transaction,
                )
                results.append(result)
            commit_outer()
        except Exception:
            rollback_outer()
            raise

        return results

    def pending_versions(
        self,
        record_store: MigrationRecordStore,
    ) -> list[tuple[str, str]]:
        """Return migrations that have not been applied yet, in dependency order.

        Returns:
            List of ``(version, fqn)`` tuples.
        """
        ordered = self._topological_order()
        pending: list[tuple[str, str]] = []
        for version, fqn, _ in ordered:
            if not record_store.is_applied(version):
                pending.append((version, fqn))
        return pending

    def status(
        self,
        record_store: MigrationRecordStore,
    ) -> list[dict[str, Any]]:
        """Return status of all discovered migrations.

        Returns:
            List of dicts with keys: ``version``, ``fqn``, ``applied``.
        """
        ordered = self._topological_order()
        result: list[dict[str, Any]] = []
        for version, fqn, _ in ordered:
            result.append({
                "version": version,
                "fqn": fqn,
                "applied": record_store.is_applied(version),
            })
        return result
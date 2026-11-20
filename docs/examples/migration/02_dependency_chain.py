# docs/examples/migration/02_dependency_chain.py
"""Ordering, dependencies, and validation — the function-style group does NOT auto-sort.

UP runs in the order you supply; DOWN reverses it. Dependencies are validated (must be earlier
in the group or already applied) but never resolved by reordering. This example shows the
resulting order plus the three most common validation failures.
"""
import os
import tempfile

from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.migration import migration, run_migration_group
from rhosocial.activerecord.backend.migration.exceptions import (
    MigrationDependencyError,
    MigrationError,
)


@migration("v001_base")
def base(ctx):
    print(f"    running {ctx.version} ({ctx.direction.value})")


@migration("v002_after_base", dependencies=("v001_base",))
def after_base(ctx):
    print(f"    running {ctx.version} ({ctx.direction.value})")


@migration("v003_bad_dep", dependencies=("v999_missing",))
def bad_dep(ctx):
    pass


@migration("v001_base")  # duplicate version on purpose
def duplicate(ctx):
    pass


def main():
    db_path = tempfile.mktemp(suffix=".db")
    backend = SQLiteBackend(connection_config=SQLiteConnectionConfig(database=db_path))
    backend.connect()
    fqn = lambda fn: f"{__name__}:{fn.__name__}"
    try:
        # 1) UP order = caller order (even if it "looks wrong", deps must be earlier)
        print("== UP in supplied order ==")
        result = run_migration_group(backend, [fqn(base), fqn(after_base)])
        print("  versions:", result.versions)

        # 2) dependency declared but placed AFTER its prerequisite -> rejected, not reordered
        print("\n== dependency not earlier (no auto-sort) ==")
        try:
            run_migration_group(backend, [fqn(after_base), fqn(base)])
        except MigrationDependencyError as exc:
            print("  rejected:", str(exc)[:90])

        # 3) dependency version that doesn't exist
        print("\n== missing dependency version ==")
        try:
            run_migration_group(backend, [fqn(bad_dep)])
        except MigrationDependencyError as exc:
            print("  rejected:", str(exc)[:90])

        # 4) duplicate version in one group
        print("\n== duplicate version ==")
        try:
            run_migration_group(backend, [fqn(base), fqn(duplicate)])
        except MigrationError as exc:
            print("  rejected:", str(exc)[:90])

        print("\nALL OK")
    finally:
        backend.disconnect()
        if os.path.exists(db_path):
            os.remove(db_path)


if __name__ == "__main__":
    main()

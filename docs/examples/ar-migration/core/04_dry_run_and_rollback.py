# docs/examples/ar-migration/core/04_dry_run_and_rollback.py
"""dry-run, up/down rollback, and dependency / guard behaviour.

Demonstrates the management features the MigrationRunner provides that user
up/down logic does not have to implement:

  - `dry_run=True` renders every statement without executing;
  - DOWN runs migrations in reverse order and clears version records;
  - dependency declarations are validated (missing dependency → error);
  - re-applying an applied version / rolling back an unapplied one is rejected.

Runs on a temporary SQLite database.
"""
import os
import tempfile
from datetime import datetime, timezone

from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.expression.statements import (
    AlterTableStatement, AddColumnAction, ColumnDefinition,
)
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.types import IntegerType
from rhosocial.activerecord.migration import (
    Migration, MigrationRunner, InMemoryMigrationRecordStore, MigrationRecord,
    MigrationDependencyError, MigrationAlreadyAppliedError,
)


def add_col(name):
    def up(ctx):
        ctx.apply(AlterTableStatement(
            ctx.backend.dialect, table=Table(ctx.backend.dialect, "t"),
            actions=[AddColumnAction(ctx.backend.dialect, column=ColumnDefinition(ctx.backend.dialect, name, IntegerType(ctx.backend.dialect)))],
        ))
    def down(ctx):
        pass  # a real migration would drop the column
    return Migration("v_" + name, up, down)


def main():
    db_path = tempfile.mktemp(suffix=".db")
    backend = SQLiteBackend(connection_config=SQLiteConnectionConfig(database=db_path))
    backend.connect()
    try:
        backend.execute("CREATE TABLE t (id INTEGER)", ())
        runner = MigrationRunner(backend)
        store = InMemoryMigrationRecordStore()

        # dry run: renders, writes nothing
        prev = runner.run([add_col("a")], store=store, dry_run=True)
        print("== dry run ==")
        print("   SQL:", [sql for sql, _ in prev.results[0].dry_run_sql])
        print("   applied:", prev.applied)

        # real up in order with a dependency
        m1 = add_col("a")
        m2 = add_col("b")
        m2 = Migration("v_b", m2.up, m2.down, dependencies=("v_a",))
        result = runner.run([m1, m2], store=store)
        print("\n== UP ==", result.applied, "| applied set:", store.get_applied())

        # down reverses and clears records
        back = runner.run([m1, m2], direction="down", store=store)
        print("== DOWN ==", back.rolled_back, "| applied set:", store.get_applied())

        # guards — use dry_run so we test validation without repeating DDL
        store2 = InMemoryMigrationRecordStore()
        runner.run([m1], store=store2, dry_run=True)  # mark nothing; guards read store
        store2.record(MigrationRecord("v_a", "up", datetime.now(timezone.utc)))
        try:
            runner.run([m1], store=store2, dry_run=True)
        except MigrationAlreadyAppliedError as e:
            print("\n== guard ==", type(e).__name__)
        bad = Migration("v_z", m1.up, m1.down, dependencies=("missing",))
        try:
            runner.run([bad], store=InMemoryMigrationRecordStore(), dry_run=True)
        except MigrationDependencyError as e:
            print("== guard ==", type(e).__name__)
    finally:
        backend.disconnect()
        if os.path.exists(db_path):
            os.remove(db_path)


if __name__ == "__main__":
    main()

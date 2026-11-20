# docs/examples/migration/01_first_migration.py
"""Your first migration: dry-run -> UP -> DOWN, with version records.

Runs entirely against a temporary SQLite database (no server needed).
Demonstrates the function-style migration API:
  - an @migration-decorated classmethod using ctx.apply(...)
  - run_migration_group with dry_run=True (renders SQL, writes nothing)
  - a real UP with a JSONFileMigrationRecordStore
  - a DOWN that rolls back and clears the applied version
"""
import os
import tempfile
from typing import Annotated, Optional

from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import UseSqlType
from rhosocial.activerecord.backend.expression.types import IntegerType, VarCharType
from rhosocial.activerecord.backend.migration import (
    migration,
    MigrationDirection,
    run_migration_group,
)
from rhosocial.activerecord.backend.migration.record import JSONFileMigrationRecordStore
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig


# ActiveRecord already mixes in MigrationMixin, so create_table_statement() and
# drop_table_statement() are available on the model.
class User(ActiveRecord):
    @classmethod
    def table_name(cls) -> str:
        return "users"

    id: Annotated[Optional[int], UseSqlType(IntegerType())] = None
    name: Annotated[str, UseSqlType(VarCharType(length=64))]


@migration("v001_create_users", description="create the initial users table")
def create_users(ctx):
    if ctx.direction == MigrationDirection.UP:
        ctx.apply(User.create_table_statement(backend=ctx.backend))
    else:
        ctx.apply(User.drop_table_statement(if_exists=True, backend=ctx.backend))


def main():
    db_path = tempfile.mktemp(suffix=".db")
    rec_path = tempfile.mktemp(suffix=".json")
    backend = SQLiteBackend(connection_config=SQLiteConnectionConfig(database=db_path))
    backend.connect()
    try:
        store = JSONFileMigrationRecordStore(rec_path)
        fqn = f"{__name__}:create_users"

        # 1) dry run — nothing is written
        preview = run_migration_group(backend, [fqn], dry_run=True)
        print("== dry run ==")
        print("  statements:", preview.dry_run_total)
        for label, sql, params in preview.dry_run_sql:
            print(f"  [{label}] {sql}")
        print("  records written:", preview.records_written)

        # 2) real UP — applies the DDL and writes a version record
        up = run_migration_group(backend, [fqn], record_store=store)
        print("\n== UP ==")
        print("  applied:", up.applied)
        print("  versions:", up.versions)
        print("  records written:", up.records_written)
        print("  applied versions:", [r.version for r in store.get_applied()])

        # 3) DOWN — rolls back and removes the applied version
        down = run_migration_group(
            backend, [fqn], direction=MigrationDirection.DOWN, record_store=store
        )
        print("\n== DOWN ==")
        print("  rolled back:", down.rolled_back)
        print("  applied versions after rollback:", [r.version for r in store.get_applied()])
    finally:
        backend.disconnect()
        for path in (db_path, rec_path):
            if os.path.exists(path):
                os.remove(path)


if __name__ == "__main__":
    main()

# docs/examples/ar-migration/core/01_hello_migration.py
"""Your first ActiveRecord-layer migration: declare, dry-run, apply, roll back.

Runs on a temporary SQLite database (no server). Demonstrates the new AR-layer
migration API (`rhosocial.activerecord.migration`):

  - write `up(ctx)` / `down(ctx)` logic;
  - `ctx.apply(...)` executes statements through the model's MigrationMixin;
  - dry-run renders SQL without touching the database;
  - MigrationRunner manages order, version records and the DOWN direction.

This is the AR-layer migration system, NOT the backend `migrate` command.
"""
import os
import tempfile
from typing import Annotated, Optional

from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import UseSqlType
from rhosocial.activerecord.backend.expression.types import IntegerType, VarCharType
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.migration import Migration, MigrationRunner, InMemoryMigrationRecordStore


class User(ActiveRecord):
    @classmethod
    def table_name(cls) -> str:
        return "users"

    id: Annotated[Optional[int], UseSqlType(IntegerType())] = None
    name: Annotated[str, UseSqlType(VarCharType(length=64))]


def main():
    db_path = tempfile.mktemp(suffix=".db")
    backend = SQLiteBackend(connection_config=SQLiteConnectionConfig(database=db_path))
    backend.connect()
    try:
        # A migration is just a versioned up/down pair.
        def up(ctx):
            ctx.apply(User.create_table_statement(backend=ctx.backend))

        def down(ctx):
            ctx.apply(User.drop_table_statement(if_exists=True, backend=ctx.backend))

        migration = Migration("v001_create_users", up, down, description="create users")
        runner = MigrationRunner(backend)
        store = InMemoryMigrationRecordStore()

        # 1) dry run: render SQL, write nothing
        preview = runner.run([migration], store=store, dry_run=True)
        print("== dry run ==")
        for sql, _ in preview.results[0].dry_run_sql:
            print("  ", sql)
        print("   applied:", preview.applied, "(nothing written)")

        # 2) real UP: execute and record the version
        result = runner.run([migration], store=store)
        print("\n== UP ==")
        print("   applied:", result.applied, "| versions left:", store.get_applied())

        # 3) DOWN: roll back and clear the version
        back = runner.run([migration], direction="down", store=store)
        print("\n== DOWN ==")
        print("   rolled back:", back.rolled_back, "| versions left:", store.get_applied())
    finally:
        backend.disconnect()
        if os.path.exists(db_path):
            os.remove(db_path)


if __name__ == "__main__":
    main()

# docs/examples/ar-migration/core/03_backfill_not_null.py
"""The classic "add a NOT NULL column with a backfill" migration.

You cannot add a NOT NULL column to a table that already has rows without a
default. The portable pattern is a MULTI-STEP migration inside one `up(ctx)`:

  1. add the new column as nullable;
  2. backfill existing rows (a DML UPDATE — `ctx.apply` handles DML too);
  3. (backend-dependent) set NOT NULL — shown as a dry-run preview because the
     exact statement differs per dialect. In production, pre-check the dialect's
     `supports_*` capability or use a fixed-backend branch.

`down(ctx)` reverses: drop the column.
"""
import os
import tempfile

from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.expression import Parameter
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.statements import (
    AlterTableStatement, AddColumnAction, DropColumnAction, ColumnDefinition, UpdateStatement,
)
from rhosocial.activerecord.backend.expression.types import VarCharType
from rhosocial.activerecord.migration import Migration, MigrationRunner


def add_nullable_nickname(dialect):
    return AlterTableStatement(
        dialect, table=Table(dialect, "users"),
        actions=[AddColumnAction(dialect, column=ColumnDefinition(dialect, "nickname", VarCharType(dialect, 50)))],
    )


def backfill(dialect):
    return UpdateStatement(
        dialect, table=Table(dialect, "users"),
        assignments={"nickname": Parameter(dialect, "anonymous", inline=True)},
    )


def drop_nickname(dialect):
    return AlterTableStatement(
        dialect, table=Table(dialect, "users"),
        actions=[DropColumnAction(dialect, column_name="nickname")],
    )


def main():
    dialect = SQLiteDialect(version=(3, 45, 0))
    print("== step SQL preview (no DB) ==")
    for label, stmt in [
        ("1 add nullable", add_nullable_nickname(dialect)),
        ("2 backfill", backfill(dialect)),
        ("rollback drop", drop_nickname(dialect)),
    ]:
        print(f"  {label}: {stmt.to_sql()[0]}")

    db_path = tempfile.mktemp(suffix=".db")
    backend = SQLiteBackend(connection_config=SQLiteConnectionConfig(database=db_path))
    backend.connect()
    try:
        backend.execute('CREATE TABLE "users" ("id" INTEGER)', ())
        backend.execute("INSERT INTO users (id) VALUES (1), (2)", ())

        def up(ctx):
            ctx.apply(add_nullable_nickname(ctx.backend.dialect))
            ctx.apply(backfill(ctx.backend.dialect))
            # step 3 (SET NOT NULL) is backend-dependent; omitted here on purpose.

        def down(ctx):
            ctx.apply(drop_nickname(ctx.backend.dialect))

        runner = MigrationRunner(backend)
        result = runner.run([Migration("v003_backfill_nickname", up, down)])
        print("\n== UP ==", result.applied, "(2 statements executed: add column + backfill)")
    finally:
        backend.disconnect()
        if os.path.exists(db_path):
            os.remove(db_path)


if __name__ == "__main__":
    main()

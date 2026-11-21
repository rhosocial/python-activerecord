# docs/examples/ar-migration/core/02_add_drop_column.py
"""Adding / dropping a column — the common case needs no backend suggestion.

When an operation is a SINGLE standard action with only spelling differences
across databases (ADD COLUMN / DROP COLUMN), the expression-dialect system
already renders the right SQL per backend. No `suggest_partition_*` needed.

This example renders the ALTER statements on a connectionless SQLiteDialect,
then applies them for real against a temporary SQLite database.
"""
import os
import tempfile

from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.statements import (
    AlterTableStatement, AddColumnAction, DropColumnAction, ColumnDefinition,
)
from rhosocial.activerecord.backend.expression.types import VarCharType
from rhosocial.activerecord.migration import Migration, MigrationRunner


def add_email(dialect):
    return AlterTableStatement(
        dialect, table=Table(dialect, "users"),
        actions=[AddColumnAction(dialect, column=ColumnDefinition(dialect, "email", VarCharType(dialect, 100)))],
    )


def drop_email(dialect):
    return AlterTableStatement(
        dialect, table=Table(dialect, "users"),
        actions=[DropColumnAction(dialect, column_name="email")],
    )


def main():
    # Preview on a connectionless dialect — no database needed.
    dialect = SQLiteDialect(version=(3, 45, 0))
    print("== rendered SQL (no DB) ==")
    print("  ", add_email(dialect).to_sql()[0])
    print("  ", drop_email(dialect).to_sql()[0])

    # Apply for real against a temporary database.
    db_path = tempfile.mktemp(suffix=".db")
    backend = SQLiteBackend(connection_config=SQLiteConnectionConfig(database=db_path))
    backend.connect()
    try:
        backend.execute('CREATE TABLE "users" ("id" INTEGER)', ())
        def up(ctx):
            ctx.apply(add_email(ctx.backend.dialect))
        def down(ctx):
            ctx.apply(drop_email(ctx.backend.dialect))
        runner = MigrationRunner(backend)
        applied = runner.run([Migration("v002_add_email", up, down)])
        print("\n== UP ==", applied.applied)
        preview = runner.run([Migration("v002_add_email", up, down)], dry_run=True)
        print("== dry run SQL ==", [sql for sql, _ in preview.results[0].dry_run_sql])
    finally:
        backend.disconnect()
        if os.path.exists(db_path):
            os.remove(db_path)


if __name__ == "__main__":
    main()

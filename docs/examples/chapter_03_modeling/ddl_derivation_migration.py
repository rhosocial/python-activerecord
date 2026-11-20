"""Chapter 3: Modeling Data - From Declaration to Executed DDL

Executable companion to docs/en_US/modeling/definition.md (Sections 0 and 2.3).

The four layers, in order:

    Annotated declarations
      -> DDLSource               (reads declarations)
      -> base/derivation.py      (builds generic statement expressions)
      -> .to_sql()               (dialect-bound SQL preview / dry run)
      -> MigrationMixin          (executes statements against a backend)

This example previews every statement first (the key point), using a
connectionless SQLiteDialect. It then configures a real in-memory SQLite
backend and executes the same statements through MigrationMixin.
"""

from typing import Annotated

from rhosocial.activerecord.backend.expression.types import IntegerType, TextType, VarCharType
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.base import UseComment, UseIndex, UseSqlType
from rhosocial.activerecord.base.derivation import (
    build_create_index_statements,
    build_create_table_statement,
    build_drop_table_statement,
)
from rhosocial.activerecord.model import ActiveRecord


class Note(ActiveRecord):
    """A model with an explicit storage type and an index declaration."""

    @classmethod
    def table_name(cls):
        return "notes"

    __primary_key__ = "id"

    id: Annotated[int, UseSqlType(IntegerType())]
    title: Annotated[
        str,
        UseSqlType(VarCharType(length=100)),
        UseIndex("idx_notes_title", unique=True),
        UseComment("note title"),
    ]
    body: Annotated[str, UseSqlType(TextType())]


def preview(label: str, statement):
    """Render a statement to SQL without executing it."""
    sql, params = statement.to_sql()
    print(f"{label}:")
    print(f"  SQL    : {sql}")
    print(f"  params : {params}")


def main():
    # Layers 1-3: declare, read, derive -- with no connection at all.
    dialect = SQLiteDialect(version=(3, 53, 0))

    create = build_create_table_statement(Note, dialect)
    indexes = build_create_index_statements(Note, dialect)
    drop = build_drop_table_statement(Note, dialect, if_exists=True)

    print("=== Dry run: declaration -> derivation -> SQL preview ===")
    preview("CREATE TABLE", create)
    for number, statement in enumerate(indexes, 1):
        preview(f"CREATE INDEX {number}", statement)
    preview("DROP TABLE", drop)
    print("Nothing above was executed; no database has been opened.")
    print()

    # Layer 4: bind a real backend and execute through MigrationMixin.
    config = SQLiteConnectionConfig(database=":memory:")
    Note.configure(config, SQLiteBackend)
    backend = Note.backend()

    print("=== Execution: in-memory SQLite backend ===")
    preview("CREATE TABLE (via MigrationMixin)", Note.create_table_statement(backend=backend))
    Note.create_table()
    Note.create_indexes()

    tables = [table.name for table in backend.introspector.list_tables()]
    print(f"  tables after create : {tables}")
    found = [idx.name for idx in backend.introspector.list_indexes("notes")]
    print(f"  indexes on notes    : {found}")

    preview("DROP TABLE (via MigrationMixin)", Note.drop_table_statement(if_exists=True, backend=backend))
    Note.drop_table(if_exists=True)
    # Introspection results are cached; refresh after the DDL change.
    backend.introspector.clear_cache()
    tables = [table.name for table in backend.introspector.list_tables()]
    print(f"  tables after drop   : {tables}")
    print()
    print("=== Declaration, derivation and execution stayed separate: the same")
    print("    statements were previewed before any of them were run. ===")
    print()


if __name__ == "__main__":
    main()

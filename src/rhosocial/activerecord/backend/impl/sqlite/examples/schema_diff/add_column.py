from rhosocial.activerecord.backend.expression.statements import (
    ColumnNotNullConstraint,
    ColumnPrimaryKeyConstraint,
)
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.impl.sqlite.schema.differ import (  # noqa: E402
    SQLiteSchemaDiffer,
)
from rhosocial.activerecord.backend.schema import (  # noqa: E402
    SyncSchemaSnapshotBuilder,
)
from rhosocial.activerecord.backend.expression.types import (
    IntegerType, TextType,
)
from rhosocial.activerecord.backend.expression import (
    CreateTableStatement,
    ColumnDefinition,
    ColumnConstraint,
    AlterTableStatement,
    AddColumn,
)
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
"""
Schema diff: detect a column added to an existing table.
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================

config = SQLiteConnectionConfig(database=":memory:")
backend = SQLiteBackend(config)
backend.introspect_and_adapt()
dialect = backend.dialect

expr = CreateTableStatement(
    dialect=dialect, table=Table(dialect, 'users'), columns=[
        ColumnDefinition(dialect, "id", IntegerType(),
            constraints=[ColumnConstraint(dialect, branch=ColumnPrimaryKeyConstraint(dialect))]),
        ColumnDefinition(dialect, "name", TextType(),
            constraints=[ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect))]),
    ]
)
sql, params = expr.to_sql()
backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================

builder = SyncSchemaSnapshotBuilder(backend.introspector, dialect)
snapshot_before = builder.build(schema="main")

# Add a new column
expr = AlterTableStatement(dialect, "users", [
    AddColumn(dialect, ColumnDefinition(dialect, "email", TextType()))
])
sql, params = expr.to_sql()
backend.execute(sql, params)

snapshot_after = builder.build(schema="main")

differ = SQLiteSchemaDiffer()
diff = differ.compare(snapshot_before, snapshot_after)

# ============================================================
# SECTION: Execution (run the expression)
# ============================================================
print(f"Modified tables: {diff.modified_tables}")

if "users" in diff.table_diffs:
    td = diff.table_diffs["users"]
    for cd in td.column_diffs:
        added = "added" if cd.is_added else "removed" if cd.is_removed else "modified"
        print(f"  Column '{cd.column_name}': {added}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()
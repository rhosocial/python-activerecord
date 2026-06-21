"""
Schema diff: detect a newly added table.

SQLite does not track column ordinal positions with semantic meaning,
so the default SQLiteSchemaDiffer is sufficient for all comparisons.
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.expression import (
    CreateTableExpression, ColumnDefinition,
    ColumnConstraint, ColumnConstraintType,
)
from rhosocial.activerecord.backend.expression.types import (
    IntegerType, TextType,
)

config = SQLiteConnectionConfig(database=":memory:")
backend = SQLiteBackend(config)
backend.introspect_and_adapt()
dialect = backend.dialect

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.schema import (  # noqa: E402
    SyncSchemaSnapshotBuilder,
)
from rhosocial.activerecord.backend.impl.sqlite.schema.differ import (  # noqa: E402
    SQLiteSchemaDiffer,
)

# Capture snapshot of the empty database
builder = SyncSchemaSnapshotBuilder(backend.introspector, dialect)
snapshot_before = builder.build(schema="main")

# Create a new table
expr = CreateTableExpression(
    dialect=dialect, table="users", columns=[
        ColumnDefinition("id", IntegerType(),
            constraints=[ColumnConstraint(constraint_type=ColumnConstraintType.PRIMARY_KEY)]),
        ColumnDefinition("name", TextType(),
            constraints=[ColumnConstraint(constraint_type=ColumnConstraintType.NOT_NULL)]),
        ColumnDefinition("email", TextType(),
            constraints=[ColumnConstraint(constraint_type=ColumnConstraintType.UNIQUE)]),
    ]
)
sql, params = expr.to_sql()
backend.execute(sql, params)

# Capture snapshot after adding the table
snapshot_after = builder.build(schema="main")

# Compare the two snapshots
differ = SQLiteSchemaDiffer()
diff = differ.compare(snapshot_before, snapshot_after)

# ============================================================
# SECTION: Execution (run the expression)
# ============================================================
print(f"Added tables:   {diff.added_tables}")
print(f"Removed tables: {diff.removed_tables}")
print(f"Modified tables:{diff.modified_tables}")
print(f"Diff is empty:  {diff.is_empty}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()
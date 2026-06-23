"""
Schema diff: roundtrip snapshot to JSON, then diff after deserialization.

Demonstrates that snapshots can be saved, loaded, and compared across sessions.
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
import json
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.expression import (
    CreateTableExpression, DropTableExpression,
    ColumnDefinition, ColumnConstraint, ColumnConstraintType,
)
from rhosocial.activerecord.backend.expression.types import (
    IntegerType, TextType,
)

config = SQLiteConnectionConfig(database=":memory:")
backend = SQLiteBackend(config)
backend.introspect_and_adapt()
dialect = backend.dialect

expr = CreateTableExpression(
    dialect=dialect, table="books", columns=[
        ColumnDefinition("id", IntegerType(),
            constraints=[ColumnConstraint(constraint_type=ColumnConstraintType.PRIMARY_KEY)]),
        ColumnDefinition("title", TextType(),
            constraints=[ColumnConstraint(constraint_type=ColumnConstraintType.NOT_NULL)]),
        ColumnDefinition("author", TextType()),
    ]
)
sql, params = expr.to_sql()
backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.schema import (  # noqa: E402
    SchemaSnapshot,
    SyncSchemaSnapshotBuilder,
)
from rhosocial.activerecord.backend.impl.sqlite.schema.differ import (  # noqa: E402
    SQLiteSchemaDiffer,
)

builder = SyncSchemaSnapshotBuilder(backend.introspector, dialect)
snapshot_before = builder.build(schema="main")

# Serialize, then deserialize the snapshot
snapshot_json = json.dumps(snapshot_before.to_dict(), default=str)
snapshot_loaded = SchemaSnapshot.from_dict(json.loads(snapshot_json))

# Modify the database
expr = DropTableExpression(dialect, "books")
sql, params = expr.to_sql()
backend.execute(sql, params)

snapshot_after = builder.build(schema="main")

# Compare loaded (before) vs current (after)
differ = SQLiteSchemaDiffer()
diff = differ.compare(snapshot_loaded, snapshot_after)

# ============================================================
# SECTION: Execution (run the expression)
# ============================================================
print(f"Snapshot serialized to   {len(snapshot_json)} chars")
print(f"Snapshot roundtrip ok:   {snapshot_loaded.dialect_class == snapshot_before.dialect_class}")
# Verify table data was faithfully restored from JSON
assert snapshot_loaded.dialect_class == snapshot_before.dialect_class
assert list(snapshot_loaded.tables.keys()) == list(snapshot_before.tables.keys()), (
    f"table names mismatch: {list(snapshot_loaded.tables.keys())} "
    f"!= {list(snapshot_before.tables.keys())}"
)
for name in snapshot_before.tables:
    before_t = snapshot_before.tables[name]
    after_t = snapshot_loaded.tables[name]
    assert [c.name for c in before_t.columns] == [c.name for c in after_t.columns], (
        f"columns mismatch in table '{name}'"
    )
    for col_b, col_a in zip(before_t.columns, after_t.columns):
        assert col_b.data_type.__class__.__name__ == col_a.data_type.__class__.__name__, (
            f"type mismatch in {name}.{col_b.name}"
        )
print(f"Table data roundtrip ok:  all columns and types match")
print(f"Removed tables:          {diff.removed_tables}")
print(f"Added tables:            {diff.added_tables}")
print(f"Modified tables:         {diff.modified_tables}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()
"""
SQLite 3.53.0 new features detection example.

This example demonstrates how to use introspect_and_adapt() to detect
SQLite version 3.53.0 new features and their support status.

SQLite 3.53.0 adds:
- ALTER TABLE ADD/DROP CONSTRAINT for NOT NULL and CHECK
- REINDEX EXPRESSIONS statement
- json_array_insert() and jsonb_array_insert() functions

NOTE: This example requires SQLite 3.53.0+ for full feature demonstration.
On older versions, it will show the features as unsupported.
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
import sqlite3
import sys

config = SQLiteConnectionConfig(database=":memory:")
backend = SQLiteBackend(config)
dialect = backend.dialect

print(f"Python version: {sys.version}")
print(f"SQLite library version: {sqlite3.sqlite_version}")
print(f"SQLite version info: {sqlite3.sqlite_version_info}")
print()

print(f"Initial dialect version: {backend._dialect.version}")
print()

backend.connect()
backend.introspect_and_adapt()

dialect = backend._dialect
print(f"Adapted dialect version: {dialect.version}")
print()

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
print("=" * 60)
print("SQLite 3.53.0 Feature Detection Results")
print("=" * 60)
print()

print("--- ALTER TABLE ADD/DROP CONSTRAINT ---")
print(f"  supports_add_constraint(): {dialect.supports_add_constraint()}")
print(f"  supports_drop_constraint(): {dialect.supports_drop_constraint()}")
print()

print("--- REINDEX EXPRESSIONS ---")
print(f"  supports_reindex_expressions(): {dialect.supports_reindex_expressions()}")
print()

print("--- JSON Functions (3.53.0+) ---")
funcs = dialect.supports_functions()
print(f"  json_array_insert: {funcs.get('json_array_insert')}")
print(f"  jsonb_array_insert: {funcs.get('jsonb_array_insert')}")
print()

print("--- Runtime Detection Parameters ---")
print(f"  math_functions_available: {dialect.get_runtime_param('math_functions_available')}")
print(f"  json1_available: {dialect.get_runtime_param('json1_available')}")
print()

print("--- Compile Options (extensions) ---")
compile_options = dialect.get_runtime_param("compile_options", {})
ext_available = {
    "fts3": dialect.get_runtime_param("fts3_available", False),
    "fts4": dialect.get_runtime_param("fts4_available", False),
    "fts5": dialect.get_runtime_param("fts5_available", False),
    "rtree": dialect.get_runtime_param("rtree_available", False),
    "geopoly": dialect.get_runtime_param("geopoly_available", False),
}
for name, available in ext_available.items():
    print(f"  {name}: {'available' if available else 'not available'}")
print()

# Compare with version-dependent functions
print("--- Version Comparison ---")
if dialect.version >= (3, 53, 0):
    print("SQLite version 3.53.0+ detected - all new features should be supported")
else:
    print(f"SQLite version {dialect.version[0]}.{dialect.version[1]}.{dialect.version[2]} detected")
    print("Some features require SQLite 3.53.0+")

# ============================================================
# SECTION: Execution (demonstrate feature usage)
# ============================================================
print()
print("=" * 60)
print("Feature Usage Demonstration")
print("=" * 60)

# Demonstrate REINDEX EXPRESSIONS if supported
from rhosocial.activerecord.backend.impl.sqlite.expression import SQLiteReindexExpression

if dialect.supports_reindex_expressions():
    print("\n--- REINDEX EXPRESSIONS Example ---")
    reindex_expr = SQLiteReindexExpression(dialect, expressions=True)
    sql, params = reindex_expr.to_sql()
    print(f"  SQL: {sql}")
else:
    print("\n--- REINDEX EXPRESSIONS Example ---")
    print("  Not supported in this SQLite version")

# Demonstrate json_array_insert if supported
from rhosocial.activerecord.backend.impl.sqlite.functions import json_array_insert
from rhosocial.activerecord.backend.expression import Column, Literal

if dialect.version >= (3, 53, 0) and funcs.get("json_array_insert"):
    print("\n--- json_array_insert Example ---")
    col_data = Column(dialect, "data")
    json_expr = json_array_insert(dialect, col_data, Literal(dialect, "new_item"), position=0)
    sql, params = json_expr.to_sql()
    print(f"  SQL: {sql}")
    print(f"  Params: {params}")
else:
    print("\n--- json_array_insert Example ---")
    print("  Not supported in this SQLite version")

# Demonstrate ALTER TABLE ADD CONSTRAINT if supported
# Note: format methods are available via AlterTableMixin
if dialect.supports_add_constraint():
    print("\n--- ALTER TABLE ADD CONSTRAINT Example ---")
    print(f"  Supports: supports_add_constraint() = True")
    print(f"  Example SQL: ALTER TABLE users ADD CONSTRAINT chk_age CHECK (age >= 0)")
else:
    print("\n--- ALTER TABLE ADD CONSTRAINT Example ---")
    print("  Not supported in this SQLite version (requires 3.53.0+)")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()

print("\nNote: The backend.introspect_and_adapt() method automatically")
print("detects the SQLite version and updates the dialect's capabilities.")
print("Use dialect.version or supports_* methods to check feature availability.")
# src/rhosocial/activerecord/backend/impl/sqlite/examples/extensions/geopoly_basic.py
"""
Geopoly polygon geometry operations.

Demonstrates: CREATE VIRTUAL TABLE, INSERT polygons, format_area_query(),
format_contains_query(), DROP TABLE.
All using the GeopolyExtension's formatting methods against real SQLite.

NOTE: Geopoly requires SQLite 3.26.0+ with SQLITE_ENABLE_GEOPOLY compile option.
Not all builds include this; the script degrades gracefully.
"""

# ============================================================
# SECTION: Setup
# ============================================================
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType
import sqlite3

config = SQLiteConnectionConfig(database=':memory:')
backend = SQLiteBackend(config)
dialect = backend.dialect
ddl_opts = ExecutionOptions(stmt_type=StatementType.DDL)
dml_opts = ExecutionOptions(stmt_type=StatementType.INSERT)
dql_opts = ExecutionOptions(stmt_type=StatementType.DQL)

sqlite_version = tuple(int(x) for x in sqlite3.sqlite_version.split('.'))
if sqlite_version < (3, 26, 0):
    print(f"Geopoly requires SQLite 3.26.0+, found {sqlite3.sqlite_version}")
    backend.disconnect()
    exit(0)

from rhosocial.activerecord.backend.impl.sqlite.extension.extensions.geopoly import get_geopoly_extension
geopoly = get_geopoly_extension()

def exec_dql(sql: str, params: tuple = ()):
    return backend.execute(sql, params, options=dql_opts).data

def try_execute(sql: str, params: tuple = (), label: str = ""):
    """Execute and catch errors gracefully."""
    try:
        backend.execute(sql, params, options=ddl_opts if sql.upper().startswith(("CREATE", "DROP")) else dml_opts)
        return True
    except Exception as e:
        print(f"    SKIP: {label} — {e}")
        return False

# ============================================================
# SECTION 1: CREATE Virtual Table
# ============================================================
print("=" * 60)
print("1. Geopoly Virtual Table Creation")
print("=" * 60)

sql, _ = geopoly.format_create_virtual_table('polygons')
print(f"\n[1a] Basic Geopoly table: {sql}")
if not try_execute(sql, label="geopoly"):
    print("    Geopoly not available in this SQLite build, exiting.")
    backend.disconnect()
    exit(0)

sql, _ = geopoly.format_create_virtual_table('zones', extra_columns=['name', 'category'])
print(f"[1b] Zones table: {sql}")
try_execute(sql, label="create zones")

# ============================================================
# SECTION 2: INSERT polygon data
# ============================================================
print("\n" + "=" * 60)
print("2. Inserting Polygon Data")
print("=" * 60)

backend.execute("INSERT INTO polygons(_shape) VALUES ('[[0,0],[1,0],[0.5,1],[0,0]]')", options=dml_opts)
backend.execute("INSERT INTO polygons(_shape) VALUES ('[[0.2,0.2],[0.8,0.2],[0.5,0.8],[0.2,0.2]]')", options=dml_opts)
print("    Inserted 2 polygons")

if exec_dql("SELECT name FROM sqlite_master WHERE name='zones'"):
    backend.execute(
        "INSERT INTO zones(_shape, name, category) VALUES (?, ?, ?)",
        ('[[0,0],[3,0],[3,2],[0,2],[0,0]]', 'Downtown', 'commercial'),
        options=dml_opts
    )
    print("    Inserted 1 zone")

# ============================================================
# SECTION 3: Area via format_area_query()
# ============================================================
print("\n" + "=" * 60)
print("3. Area via format_area_query()")
print("=" * 60)

sql, params = geopoly.format_area_query('polygons')
r = exec_dql(sql, params)
print(f"\n[3a] Polygon areas:")
for row in r:
    print(f"    _shape={row['_shape']!r} area={row['area']}")

if exec_dql("SELECT name FROM sqlite_master WHERE name='zones'"):
    sql, params = geopoly.format_area_query('zones')
    r = exec_dql(sql, params)
    print(f"\n[3b] Zone areas:")
    for row in r:
        print(f"    {row.get('name', '?')}: area={row['area']}")

# ============================================================
# SECTION 4: Contains via format_contains_query()
# ============================================================
print("\n" + "=" * 60)
print("4. Point-in-Polygon via format_contains_query()")
print("=" * 60)

sql, params = geopoly.format_contains_query('polygons', 0.3, 0.3)
r = exec_dql(sql, params)
print(f"\n[4a] Point (0.3, 0.3) inside polygon: {len(r)} (both polygons contain this point)")

sql, params = geopoly.format_contains_query('polygons', 0.9, 0.9)
r = exec_dql(sql, params)
print(f"[4b] Point (0.9, 0.9) inside polygon: {len(r)} (expected 0)")

if exec_dql("SELECT name FROM sqlite_master WHERE name='zones'"):
    sql, params = geopoly.format_contains_query('zones', 1.5, 1.0)
    r = exec_dql(sql, params)
    print(f"[4c] Point (1.5, 1.0) in zones: {len(r)} result(s)")
    for row in r:
        print(f"      {row.get('name', '?')}")

# ============================================================
# SECTION 5: DROP Virtual Table
# ============================================================
print("\n" + "=" * 60)
print("5. DROP Geopoly Virtual Table")
print("=" * 60)

sql, _ = geopoly.format_drop_virtual_table('zones', if_exists=True)
backend.execute(sql, options=ddl_opts)
print(f"\n[5a] Dropped 'zones': {sql}")

sql, _ = geopoly.format_drop_virtual_table('polygons')
backend.execute(sql, options=ddl_opts)
print(f"[5b] Dropped 'polygons': {sql}")

remaining = exec_dql(
    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
)
print(f"\n    Remaining tables: {len(remaining)} (all clean)")

# ============================================================
# SECTION: Teardown
# ============================================================
print("\n" + "=" * 60)
print("Geopoly demonstration complete.")
print("=" * 60)
backend.disconnect()
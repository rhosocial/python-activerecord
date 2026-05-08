# src/rhosocial/activerecord/backend/impl/sqlite/examples/extensions/rtree_basic.py
"""
R-Tree spatial index operations.

Demonstrates: CREATE VIRTUAL TABLE, INSERT, format_range_query(), DROP TABLE.
All using the RTreeExtension's formatting methods against real SQLite.
"""

# ============================================================
# SECTION: Setup
# ============================================================
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

config = SQLiteConnectionConfig(database=':memory:')
backend = SQLiteBackend(config)
dialect = backend.dialect
ddl_opts = ExecutionOptions(stmt_type=StatementType.DDL)
dml_opts = ExecutionOptions(stmt_type=StatementType.INSERT)
dql_opts = ExecutionOptions(stmt_type=StatementType.DQL)

from rhosocial.activerecord.backend.impl.sqlite.extension.extensions.rtree import get_rtree_extension
rtree = get_rtree_extension()

def exec_dql(sql: str, params: tuple = ()):
    return backend.execute(sql, params, options=dql_opts).data

# ============================================================
# SECTION 1: CREATE Virtual Table
# ============================================================
print("=" * 60)
print("1. R-Tree Virtual Table Creation")
print("=" * 60)

sql, _ = rtree.format_create_virtual_table('locations', dimensions=2)
print(f"\n[1a] 2D R-Tree table: {sql}")
backend.execute(sql, options=ddl_opts)

sql, _ = rtree.format_create_virtual_table('volumes', dimensions=3)
print(f"[1b] 3D R-Tree table: {sql}")
backend.execute(sql, options=ddl_opts)

# ============================================================
# SECTION 2: INSERT data
# ============================================================
print("\n" + "=" * 60)
print("2. Inserting Spatial Data")
print("=" * 60)

locations = [
    (-122.4194, -122.4194, 37.7749, 37.7749),
    (-74.0060, -74.0060, 40.7128, 40.7128),
    (-122.0, -121.0, 37.0, 38.0),
    (-73.99, -73.98, 40.71, 40.72),
    (-122.5, -122.0, 37.5, 38.0),
]
for vals in locations:
    backend.execute(
        "INSERT INTO locations(min0, max0, min1, max1) VALUES (?, ?, ?, ?)",
        vals, options=dml_opts
    )
print(f"    Inserted {len(locations)} locations")

volumes = [
    (0, 10, 0, 10, 0, 10),
    (5, 15, 5, 15, 5, 15),
    (100, 110, 100, 110, 100, 110),
]
for vals in volumes:
    backend.execute(
        "INSERT INTO volumes(min0, max0, min1, max1, min2, max2) VALUES (?, ?, ?, ?, ?, ?)",
        vals, options=dml_opts
    )
print(f"    Inserted {len(volumes)} volumes")

# ============================================================
# SECTION 3: Range Queries via format_range_query()
# ============================================================
print("\n" + "=" * 60)
print("3. Range Queries via format_range_query()")
print("=" * 60)

sql, params = rtree.format_range_query('locations', [(-122.5, -122.0), (37.5, 38.0)])
print(f"\n[3a] 2D range (SF area): {len(exec_dql(sql, params))} result(s)")

sql, params = rtree.format_range_query('locations', [(-75.0, -73.0), (40.0, 41.0)])
print(f"[3b] 2D range (NY area): {len(exec_dql(sql, params))} result(s)")

sql, params = rtree.format_range_query('volumes', [(0, 20), (0, 20), (0, 20)])
r = exec_dql(sql, params)
print(f"[3c] 3D range: {len(r)} result(s)")
for row in r:
    print(f"      id={row['id']}")

sql, params = rtree.format_range_query('locations', [(-180, -179), (0, 1)])
print(f"[3d] No-match range: {len(exec_dql(sql, params))} result(s) (expected 0)")

# ============================================================
# SECTION 4: Custom column names
# ============================================================
print("\n" + "=" * 60)
print("4. Range Query with Custom Column Names")
print("=" * 60)

sql, params = rtree.format_range_query(
    'locations', [(-122.5, -122.0), (37.5, 38.0)],
    column_names=[('"locations".min0', '"locations".max0'), ('"locations".min1', '"locations".max1')]
)
print(f"\n[4a] Custom column names: {len(exec_dql(sql, params))} result(s)")

# ============================================================
# SECTION 5: DROP Virtual Table
# ============================================================
print("\n" + "=" * 60)
print("5. DROP R-Tree Virtual Table")
print("=" * 60)

sql, _ = rtree.format_drop_virtual_table('volumes')
backend.execute(sql, options=ddl_opts)
print(f"\n[5a] Dropped 'volumes': {sql}")

sql, _ = rtree.format_drop_virtual_table('locations', if_exists=True)
backend.execute(sql, options=ddl_opts)
print(f"[5b] Dropped 'locations': {sql}")

remaining = exec_dql(
    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
)
print(f"\n    Remaining tables: {len(remaining)} (all clean)")

# ============================================================
# SECTION: Teardown
# ============================================================
print("\n" + "=" * 60)
print("R-Tree demonstration complete.")
print("=" * 60)
backend.disconnect()
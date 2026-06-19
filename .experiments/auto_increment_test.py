"""
实验：AUTOINCREMENT 支持、内省检测、下一序号查询

运行: python3 .experiments/auto_increment_test.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    CreateTableExpression, ColumnDefinition, ColumnConstraint, ColumnConstraintType,
)
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

DQL = ExecutionOptions(stmt_type=StatementType.DQL)

backend = SQLiteBackend(database=":memory:")
backend.connect()
backend.introspect_and_adapt()

dialect = backend.dialect
print("=" * 60)
print("  实验：AUTOINCREMENT 全链路验证")
print("=" * 60)

# === 1. DDL 生成 ===
print("\n--- 1. DDL 中 AUTOINCREMENT 输出 ---")
with_ai = ColumnDefinition("id", "INTEGER",
    constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)])
without_ai = ColumnDefinition("id", "INTEGER",
    constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=False)])

sql_ai, _ = CreateTableExpression(dialect, table="test_ai", columns=[with_ai]).to_sql()
sql_no_ai, _ = CreateTableExpression(dialect, table="test_no_ai", columns=[without_ai]).to_sql()
print(f"  有 AUTOINCREMENT: {sql_ai}")
print(f"  无 AUTOINCREMENT: {sql_no_ai}")

backend.execute(sql_ai)

# === 2. 内省能否检测 ===
print("\n--- 2. 内省能否检测到 AUTOINCREMENT ---")
cols = backend.introspector.list_columns("test_ai")
for c in cols:
    print(f"  {c.name:5s}  pk={c.is_primary_key}  auto_increment={c.is_auto_increment}")
print(f"  → is_auto_increment 始终=False，内省未检测 AUTOINCREMENT")

# === 3. sqlite_master 解析 ===
print("\n--- 3. 从 sqlite_master 检测 AUTOINCREMENT ---")
raw = backend.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='test_ai'", options=DQL)
print(f"  raw.data type={type(raw.data)}, value={raw.data}")
create_sql = ""
if raw.data:
    if isinstance(raw.data[0], (list, tuple)):
        create_sql = raw.data[0][0] or ""
    elif isinstance(raw.data[0], dict):
        create_sql = raw.data[0].get("sql", "")
print(f"  原始 CREATE SQL: {create_sql}")
print(f"  包含 AUTOINCREMENT: {'AUTOINCREMENT' in create_sql}")

# === 4. 插入后查序列 ===
print("\n--- 4. 插入后查询下一序号 ---")
backend.executescript("""
    CREATE TABLE test_auto (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        val TEXT NOT NULL
    );
    INSERT INTO test_auto (val) VALUES ('a');
    INSERT INTO test_auto (val) VALUES ('b');
    INSERT INTO test_auto (val) VALUES ('c');
""")

# sqlite_sequence
seq_raw = backend.execute("SELECT name, seq FROM sqlite_sequence WHERE name='test_auto'", options=DQL)
if seq_raw.data:
    row = seq_raw.data[0]
    name = row[0] if isinstance(row, (list, tuple)) else row.get("name")
    seq = row[1] if isinstance(row, (list, tuple)) else row.get("seq")
    print(f"  sqlite_sequence: name={name}, seq={seq}, 下一序号={seq + 1}")

data = backend.execute("SELECT * FROM test_auto", options=DQL)
for row in data.data:
    if isinstance(row, dict):
        print(f"  实际数据: id={row.get('id')}, val={row.get('val')}")
    else:
        print(f"  实际数据: id={row[0]}, val={row[1]}")

# === 5. 无 AUTOINCREMENT 行为 ===
print("\n--- 5. 无 AUTOINCREMENT 时的 rowid 行为 ---")
backend.executescript("""
    CREATE TABLE test_rowid (id INTEGER PRIMARY KEY, val TEXT);
    INSERT INTO test_rowid (id, val) VALUES (10, 'x');
    INSERT INTO test_rowid (val) VALUES ('y');
""")
data2 = backend.execute("SELECT id, val FROM test_rowid", options=DQL)
for row in data2.data:
    if isinstance(row, dict):
        print(f"  数据: id={row.get('id')}, val={row.get('val')}")
    else:
        print(f"  数据: id={row[0]}, val={row[1]}")

seq_raw2 = backend.execute("SELECT name, seq FROM sqlite_sequence WHERE name='test_rowid'", options=DQL)
print(f"  sqlite_sequence: {seq_raw2.data}（空=无记录）")

backend.execute("INSERT INTO test_rowid (val) VALUES ('z')")
li = backend.execute("SELECT last_insert_rowid()", options=DQL)
row = li.data[0]
last_id = row[0] if isinstance(row, (list, tuple)) else row.get("last_insert_rowid()")
print(f"  last_insert_rowid(): {last_id}")

max_raw = backend.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM test_rowid", options=DQL)
row = max_raw.data[0]
max_id = row[0] if isinstance(row, (list, tuple)) else list(row.values())[0]
print(f"  MAX(id)+1 推测下一序号: {max_id}")

backend.disconnect()

print("\n" + "=" * 60)
print("  总结")
print("=" * 60)
print("""
1. DDL 输出 AUTOINCREMENT: ✅ 是（SQLiteDDLColumnMixin 支持）
2. 内省检测 AUTOINCREMENT:  ❌ 否（ColumnInfo.is_auto_increment 始终=False）
   只能通过解析 sqlite_master.sql 来检测
3. 查询下一序号:
   - 有 AUTOINCREMENT: sqlite_sequence.seq + 1
   - 无 AUTOINCREMENT: 无法精确获知（MAX(id)+1 不准确）
   - last_insert_rowid() 获取最后插入的 rowid
""")

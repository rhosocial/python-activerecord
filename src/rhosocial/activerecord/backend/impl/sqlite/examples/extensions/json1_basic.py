# src/rhosocial/activerecord/backend/impl/sqlite/examples/extensions/json1_basic.py
"""
JSON1 extension - JSON functions demonstration.

Covers: json_array(), json_object(), json_extract (->), json_extract_text (->>),
json_valid/json_type, json_set/json_replace/json_remove, json_each/json_tree,
json_group_array/json_group_object, json_insert, json_patch.

Uses JSON1Extension formatting methods where available, and raw SQL for
functions without dedicated formatters, all executed against real SQLite.
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

from rhosocial.activerecord.backend.impl.sqlite.extension.extensions.json1 import get_json1_extension
json1 = get_json1_extension()

def exec_dql(sql: str, params: tuple = ()):
    return backend.execute(sql, params, options=dql_opts).data

# ============================================================
# SECTION 1: json_array() and json_object()
# ============================================================
print("=" * 60)
print("1. JSON Constructors")
print("=" * 60)

sql, params = json1.format_json_array(['Python', 'Java', 'SQL'])
r = exec_dql(f"SELECT {sql} AS arr", params)
print(f"\n[1a] json_array: {r[0]['arr']}")

sql, params = json1.format_json_object({"name": "Python", "type": "dynamic", "year": 1991})
r = exec_dql(f"SELECT {sql} AS obj", params)
print(f"[1b] json_object: {r[0]['obj']}")

# ============================================================
# SECTION 2: Create table with JSON data
# ============================================================
print("\n" + "=" * 60)
print("2. JSON Data Storage")
print("=" * 60)

backend.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, metadata TEXT)", options=ddl_opts)
users = [
    (1, 'Alice', '{"age": 30, "city": "New York", "tags": ["dev", "python"], "active": true}'),
    (2, 'Bob', '{"age": 25, "city": "London", "tags": ["devops", "go"], "active": false}'),
    (3, 'Charlie', '{"age": 35, "city": "New York", "tags": ["dev", "java", "python"], "active": true}'),
]
for uid, name, meta in users:
    backend.execute("INSERT INTO users VALUES (?, ?, ?)", (uid, name, meta), options=dml_opts)
print(f"    Inserted {len(users)} users with JSON metadata")

# ============================================================
# SECTION 3: json_extract() via -> and json_extract()
# ============================================================
print("\n" + "=" * 60)
print("3. json_extract()")
print("=" * 60)

sql, (path,) = json1.format_json_extract('metadata', '$.age')
r = exec_dql(f"SELECT name, {sql} AS age FROM users WHERE {sql} > 30", (path, path))
print(f"\n[3a] Users age > 30 via ->: {[(row['name'], row['age']) for row in r]}")

sql, (path,) = json1.format_json_extract('metadata', '$.tags[0]')
r = exec_dql(f"SELECT name, {sql} AS first_tag FROM users", (path,))
print(f"[3b] First tag via ->: {[(row['name'], row['first_tag']) for row in r]}")

sql, (path,) = json1.format_json_extract('metadata', '$.city', arrow_operator=False)
r = exec_dql(f"SELECT name, {sql} AS city FROM users", (path,))
print(f"[3c] Cities via json_extract(): {[row['city'] for row in r]}")

# ============================================================
# SECTION 4: json_extract_text() via ->>
# ============================================================
print("\n" + "=" * 60)
print("4. json_extract_text() via ->>")
print("=" * 60)

sql, (path,) = json1.format_json_extract_text('metadata', '$.city')
r = exec_dql(f"SELECT name FROM users WHERE {sql} = 'New York'", (path,))
print(f"\n[4a] Users in New York: {[row['name'] for row in r]}")

# ============================================================
# SECTION 5: json_valid() and json_type()
# ============================================================
print("\n" + "=" * 60)
print("5. json_valid() and json_type()")
print("=" * 60)

r = exec_dql("SELECT name, json_valid(metadata) AS valid FROM users")
print(f"\n[5a] json_valid: {[(row['name'], bool(row['valid'])) for row in r]}")

r = exec_dql("SELECT name, json_type(metadata, '$.age') AS age_type, json_type(metadata, '$.tags') AS tags_type FROM users")
print(f"[5b] json_type: {[(row['name'], row['age_type'], row['tags_type']) for row in r]}")

# ============================================================
# SECTION 6: json_set(), json_replace(), json_remove()
# ============================================================
print("\n" + "=" * 60)
print("6. JSON Modification")
print("=" * 60)

r = exec_dql("SELECT json_set(metadata, '$.country', 'USA', '$.city', 'Boston') AS m FROM users WHERE id=1")
print(f"\n[6a] json_set (add country, replace city): {r[0]['m']}")

r = exec_dql("SELECT json_replace(metadata, '$.city', 'Boston', '$.country', 'USA') AS m FROM users WHERE id=1")
print(f"[6b] json_replace (replace city only, country not added): {r[0]['m']}")

r = exec_dql("SELECT json_remove(metadata, '$.tags') AS m FROM users WHERE id=1")
print(f"[6c] json_remove (remove tags): {r[0]['m']}")

# ============================================================
# SECTION 7: json_insert()
# ============================================================
print("\n" + "=" * 60)
print("7. json_insert()")
print("=" * 60)

r = exec_dql("SELECT json_insert(metadata, '$.country', 'USA', '$.city', 'Boston') AS m FROM users WHERE id=1")
print(f"\n[7a] json_insert (city unchanged, country added): {r[0]['m']}")

# ============================================================
# SECTION 8: json_patch()
# ============================================================
print("\n" + "=" * 60)
print("8. json_patch()")
print("=" * 60)

r = exec_dql("SELECT json_patch(metadata, '{\"age\": 31, \"country\": \"USA\"}') AS m FROM users WHERE id=1")
print(f"\n[8a] json_patch: {r[0]['m']}")

# ============================================================
# SECTION 9: json_each() and json_tree()
# ============================================================
print("\n" + "=" * 60)
print("9. json_each() and json_tree()")
print("=" * 60)

r = exec_dql("SELECT value FROM users, json_each(users.metadata, '$.tags') WHERE users.id=3")
print(f"\n[9a] json_each (tags for Charlie): {[row['value'] for row in r]}")

r = exec_dql("SELECT key, value, type FROM users, json_tree(users.metadata) WHERE users.id=1 AND key IS NOT NULL")
print(f"[9b] json_tree (Alice metadata): {[(row['key'], row['value'], row['type']) for row in r]}")

# ============================================================
# SECTION 10: json_group_array() and json_group_object()
# ============================================================
print("\n" + "=" * 60)
print("10. JSON Aggregate Functions")
print("=" * 60)

r = exec_dql("SELECT json_group_array(name) AS names FROM users")
print(f"\n[10a] json_group_array: {r[0]['names']}")

r = exec_dql("SELECT json_group_object(name, json_extract(metadata, '$.age')) AS age_map FROM users")
print(f"[10b] json_group_object: {r[0]['age_map']}")

# ============================================================
# SECTION: Teardown
# ============================================================
print("\n" + "=" * 60)
print("JSON1 demonstration complete.")
print("=" * 60)
backend.disconnect()
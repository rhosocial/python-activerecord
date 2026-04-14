"""
JSON operations using JSON functions.
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

config = SQLiteConnectionConfig(database=':memory:')
backend = SQLiteBackend(config)
dialect = backend.dialect

backend.execute("""
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data TEXT
)
""")
import json
backend.execute("INSERT INTO documents (data) VALUES (?)", (json.dumps({'name': 'Alice', 'age': 30, 'tags': ['a', 'b']}),))
backend.execute("INSERT INTO documents (data) VALUES (?)", (json.dumps({'name': 'Bob', 'age': 25, 'tags': ['c']}),))

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.expression import (
    QueryExpression,
    TableExpression,
    Column,
)
from rhosocial.activerecord.backend.expression.functions.json import json_extract

query = QueryExpression(
    dialect=dialect,
    select=[
        Column(dialect, 'id'),
        json_extract(dialect, Column(dialect, 'data'), '$.name'),
    ],
    from_=TableExpression(dialect, 'documents'),
)

sql, params = query.to_sql()
print(f"SQL: {sql}")
print(f"Params: {params}")

# ============================================================
# SECTION: Execution (run the expression)
# ============================================================
options = ExecutionOptions(stmt_type=StatementType.DQL)
result = backend.execute(sql, params, options=options)
print(f"Rows returned: {len(result.data) if result.data else 0}")
for row in result.data or []:
    print(f"  {row}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()

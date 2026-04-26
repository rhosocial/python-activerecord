# src/rhosocial/activerecord/backend/impl/sqlite/examples/extensions/fts3_4_basic.py
"""
FTS3/FTS4 full-text search operations.

NOTE: FTS3 and FTS4 are deprecated. For new projects, use FTS5 instead.
This example is for compatibility and understanding legacy code.

FTS4 adds more features over FTS3:
- matchinfo() function
- Better content= option support
- Unicode61 tokenizer

Reference: https://www.sqlite.org/fts3.html
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

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.expression import (
    Column,
    InsertExpression,
    ValuesSource,
    QueryExpression,
    TableExpression,
    FunctionCall,
    WildcardExpression,
)
from rhosocial.activerecord.backend.expression.core import Literal
from rhosocial.activerecord.backend.impl.sqlite.expression import SQLiteMatchPredicate

# Create FTS4 virtual table using the dialect's generic virtual table
# formatting method. For FTS4, module='fts4' and tokenizer options
# are passed via the options dict.
create_sql, create_params = dialect.format_create_virtual_table(
    module='fts4',
    table_name='documents',
    columns=['title', 'content'],
    options={'tokenize': 'porter'},
)

backend.execute(create_sql, create_params)
print(f"Created FTS4 table")

# Insert document data
documents = [
    ('Python Tutorial', 'Learn Python programming from basics to advanced'),
    ('JavaScript Guide', 'JavaScript is a popular language for web development'),
    ('SQL Basics', 'SQL is used for managing relational databases'),
]

for title, content in documents:
    insert_expr = InsertExpression(
        dialect=dialect,
        into='documents',
        columns=['title', 'content'],
        source=ValuesSource(dialect, [[
            Literal(dialect, title),
            Literal(dialect, content),
        ]]),
    )
    sql, params = insert_expr.to_sql()
    backend.execute(sql, params)

# Full-text search using SQLiteMatchPredicate with QueryExpression
# SQLiteMatchPredicate delegates to the dialect's format_match_predicate,
# which in turn calls the FTS extension's formatting logic.
search_pred = SQLiteMatchPredicate(dialect, table='documents', query='programming')

# ... snippet query example ...
# predicate is expressed via SQLiteMatchPredicate.
snippet_pred = SQLiteMatchPredicate(dialect, table='documents', query='language')

# ... offsets query example ...
offsets_pred = SQLiteMatchPredicate(dialect, table='documents', query='database')

offsets_query = QueryExpression(
    dialect=dialect,
    select=[
        Column(dialect, 'title', table='documents'),
        FunctionCall(dialect, 'offsets', [Column(dialect, 'documents')]).as_('offsets'),
    ],
    from_=TableExpression(dialect, 'documents'),
    where=offsets_pred,
)
sql, params = offsets_query.to_sql()

result = backend.execute(sql, params, options=options)
print(f"Search with offsets for 'database': {len(result.data) if result.data else 0} rows")
for row in result.data or []:
    print(f"  {row}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
print("NOTE: FTS3/FTS4 are deprecated. Use FTS5 for new projects.")
backend.disconnect()

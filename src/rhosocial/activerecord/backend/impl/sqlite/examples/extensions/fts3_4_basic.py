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
from rhosocial.activerecord.backend.impl.sqlite.extension.extensions.fts3_4 import FTS4Extension
from rhosocial.activerecord.backend.expression import (
    Column,
    InsertExpression,
    ValuesSource,
    QueryExpression,
    TableExpression,
    FunctionCall,
)
from rhosocial.activerecord.backend.expression.core import Literal

# Get FTS4 extension (more features than FTS3)
fts4 = FTS4Extension()

# Create FTS4 virtual table using tokenizer=porter for stemming
create_sql = '''
CREATE VIRTUAL TABLE documents USING fts4(
    title,
    content,
    tokenize=porter
)
'''

backend.execute(create_sql, ())
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

# Full-text search using MATCH with QueryExpression
# Note: MATCH requires raw SQL since it's not a standard SQL operator
search_sql = 'SELECT * FROM documents WHERE documents MATCH ?'
search_params = ('programming',)

result = backend.execute(search_sql, search_params)
print(f"\nSearch for 'programming': {len(result.data) if result.data else 0} rows")
for row in result.data or []:
    print(f"  {row}")

# Search with snippet() to highlight matches
snippet_query = QueryExpression(
    dialect=dialect,
    select=[
        Column(dialect, 'title', table='documents'),
        FunctionCall(dialect, 'snippet', Column(dialect, 'documents')).as_('snippet'),
    ],
    from_=TableExpression(dialect, 'documents'),
    where=Literal(dialect, 'language'),  # This would need MATCH, using literal as workaround
)

# For FTS, MATCH must be used with raw SQL
snippet_sql = 'SELECT title, snippet(documents) AS snippet FROM documents WHERE documents MATCH ?'
snippet_params = ('language',)

result = backend.execute(snippet_sql, snippet_params)
print(f"\nSearch with snippet for 'language': {len(result.data) if result.data else 0} rows")
for row in result.data or []:
    print(f"  {row}")

# Search with offsets() to get match positions
offsets_sql = 'SELECT title, offsets(documents) AS offsets FROM documents WHERE documents MATCH ?'
offsets_params = ('database',)

result = backend.execute(offsets_sql, offsets_params)
print(f"\nSearch with offsets for 'database': {len(result.data) if result.data else 0} rows")
for row in result.data or []:
    print(f"  {row}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
print("\nNOTE: FTS3/FTS4 are deprecated. Use FTS5 for new projects.")
backend.disconnect()
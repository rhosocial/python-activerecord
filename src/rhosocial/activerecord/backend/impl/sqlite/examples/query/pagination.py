"""
Pagination using LIMIT/OFFSET - SQLite.

This example demonstrates:
1. Basic LIMIT clause
2. LIMIT with OFFSET for pagination
3. Iterating through pages of results
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

from rhosocial.activerecord.backend.expression import (
    CreateTableExpression,
    InsertExpression,
    ValuesSource,
    DropTableExpression,
)
from rhosocial.activerecord.backend.expression.core import Literal
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
)

create_table = CreateTableExpression(
    dialect=dialect,
    table_name='articles',
    columns=[
        ColumnDefinition('id', 'INTEGER', constraints=[
            ColumnConstraint(ColumnConstraintType.PRIMARY_KEY),
            ColumnConstraint(ColumnConstraintType.NOT_NULL, is_auto_increment=True),
        ]),
        ColumnDefinition('title', 'TEXT'),
        ColumnDefinition('author', 'TEXT'),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
backend.execute(sql, params)

articles = [
    ('Introduction to SQL', 'Alice'),
    ('Advanced Joins', 'Bob'),
    ('Subquery Patterns', 'Alice'),
    ('Window Functions', 'Charlie'),
    ('CTE Deep Dive', 'Bob'),
    ('Indexing Strategies', 'Alice'),
    ('Query Optimization', 'Charlie'),
    ('Transaction Isolation', 'Bob'),
    ('JSON in SQLite', 'Alice'),
    ('Recursive CTEs', 'Charlie'),
]
for title, author in articles:
    insert_expr = InsertExpression(
        dialect=dialect,
        into='articles',
        columns=['title', 'author'],
        source=ValuesSource(dialect, [[Literal(dialect, title), Literal(dialect, author)]]),
    )
    sql, params = insert_expr.to_sql()
    backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.expression import (
    QueryExpression,
    TableExpression,
    LimitOffsetClause,
    OrderByClause,
)
from rhosocial.activerecord.backend.expression.core import Column, WildcardExpression

# 1. Basic LIMIT - get first N rows
query_limit = QueryExpression(
    dialect=dialect,
    select=[WildcardExpression(dialect)],
    from_=TableExpression(dialect, 'articles'),
    order_by=OrderByClause(dialect, expressions=[(Column(dialect, 'id'), 'ASC')]),
    limit_offset=LimitOffsetClause(dialect, limit=3),
)
sql, params = query_limit.to_sql()
print(f"LIMIT 3 SQL: {sql}")
print(f"Params: {params}")

# 2. LIMIT with OFFSET - pagination
# Page 1: offset=0, limit=3
# Page 2: offset=3, limit=3
# Page 3: offset=6, limit=3
# Page 4: offset=9, limit=3
page_size = 3
page_number = 2
offset = (page_number - 1) * page_size

query_page = QueryExpression(
    dialect=dialect,
    select=[WildcardExpression(dialect)],
    from_=TableExpression(dialect, 'articles'),
    order_by=OrderByClause(dialect, expressions=[(Column(dialect, 'id'), 'ASC')]),
    limit_offset=LimitOffsetClause(dialect, limit=page_size, offset=offset),
)
sql, params = query_page.to_sql()
print(f"\nPage {page_number} SQL: {sql}")
print(f"Params: {params}")

# ============================================================
# SECTION: Execution (run the expression)
# ============================================================
options = ExecutionOptions(stmt_type=StatementType.DQL)

# Execute basic LIMIT
result = backend.execute(*query_limit.to_sql(), options=options)
print(f"\nLIMIT 3 result ({len(result.data)} rows):")
for row in result.data or []:
    print(f"  {row}")

# Execute page 2
result = backend.execute(*query_page.to_sql(), options=options)
print(f"\nPage {page_number} result ({len(result.data)} rows):")
for row in result.data or []:
    print(f"  {row}")

# Page through all results
print("\nAll pages:")
total_pages = -(-len(articles) // page_size)  # ceil division
for page in range(1, total_pages + 1):
    offset = (page - 1) * page_size
    query = QueryExpression(
        dialect=dialect,
        select=[WildcardExpression(dialect)],
        from_=TableExpression(dialect, 'articles'),
        order_by=OrderByClause(dialect, expressions=[(Column(dialect, 'id'), 'ASC')]),
        limit_offset=LimitOffsetClause(dialect, limit=page_size, offset=offset),
    )
    result = backend.execute(*query.to_sql(), options=options)
    rows = result.data or []
    print(f"  Page {page}/{total_pages}: {len(rows)} rows - {[r['title'] for r in rows]}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
drop_expr = DropTableExpression(dialect=dialect, table_name='articles', if_exists=True)
sql, params = drop_expr.to_sql()
backend.execute(sql, params)
backend.disconnect()

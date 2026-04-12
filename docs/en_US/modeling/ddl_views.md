# View DDL

Views are virtual tables based on a SELECT query. They don't store data but provide a way to simplify complex queries, enforce security, and abstract schema changes.

## Create View

```python
from rhosocial.activerecord.backend.expression import (
    CreateViewExpression,
    QueryExpression,
    TableExpression,
    Column
)

# Basic view
create_view = CreateViewExpression(
    dialect,
    view_name="user_summary",
    query=QueryExpression(
        dialect,
        select=[
            Column(dialect, "id"),
            Column(dialect, "name"),
            Column(dialect, "email")
        ],
        from_=TableExpression(dialect, "users")
    )
)
sql, params = create_view.to_sql()
# sql: 'CREATE VIEW "user_summary" AS SELECT "id", "name", "email" FROM "users"'
```

## View with Column Aliases

```python
create_view = CreateViewExpression(
    dialect,
    view_name="user_details",
    query=QueryExpression(
        dialect,
        select=[
            Column(dialect, "id"),
            Column(dialect, "name"),
            Column(dialect, "email")
        ],
        from_=TableExpression(dialect, "users")
    ),
    columns=["user_id", "full_name", "contact_email"]
)
sql, params = create_view.to_sql()
# sql: 'CREATE VIEW "user_details" ("user_id", "full_name", "contact_email") AS SELECT ...'
```

## View with OR REPLACE

```python
create_view = CreateViewExpression(
    dialect,
    view_name="user_summary",
    query=query,
    or_replace=True
)
sql, params = create_view.to_sql()
# sql: 'CREATE OR REPLACE VIEW "user_summary" AS ...'
```

## View with TEMPORARY (SQLite)

```python
create_view = CreateViewExpression(
    dialect,
    view_name="temp_stats",
    query=query,
    temporary=True
)
sql, params = create_view.to_sql()
# sql: 'CREATE TEMPORARY VIEW "temp_stats" AS ...'
```

## Drop View

```python
from rhosocial.activerecord.backend.expression import DropViewExpression

# Basic drop
drop_view = DropViewExpression(
    dialect,
    view_name="old_view"
)
sql, params = drop_view.to_sql()
# sql: 'DROP VIEW "old_view"'

# Drop if exists
drop_view = DropViewExpression(
    dialect,
    view_name="old_view",
    if_exists=True
)
sql, params = drop_view.to_sql()
# sql: 'DROP VIEW IF EXISTS "old_view"'
```

## Executing View DDL

```python
# Create a table first
create_table = CreateTableExpression(dialect, "users", user_columns)
backend.execute(create_table.to_sql())

# Create a view
create_view = CreateViewExpression(dialect, "user_summary", view_query)
backend.execute(create_view.to_sql())

# Introspection: List views
views = backend.introspector.list_views()
for v in views:
    print(f"View: {v.name}")
```

> **Note**: SQLite supports views. Different databases may have different view capabilities (e.g., MySQL's ALGORITHM, PostgreSQL's materialized views). Refer to your backend documentation.

## Example Code

Full example: [docs/examples/chapter_03_modeling/ddl_views.py](../../../examples/chapter_03_modeling/ddl_views.py)
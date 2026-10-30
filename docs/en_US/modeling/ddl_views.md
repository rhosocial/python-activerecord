# View DDL

Views are virtual tables based on a SELECT query. They don't store data but provide a way to simplify complex queries, enforce security, and abstract schema changes.

## Create View

```python
from rhosocial.activerecord.backend.expression import (
    Column,
    NamedRelationRef,
    QueryStatement,
)
from rhosocial.activerecord.backend.expression.objects import Table, View
from rhosocial.activerecord.backend.expression.statements import CreateViewStatement

# Basic view
query = QueryStatement(
    dialect,
    select=[
        Column(dialect, "id"),
        Column(dialect, "name"),
        Column(dialect, "email")
    ],
    from_=NamedRelationRef(dialect, Table(dialect, "users"))
)
create_view = CreateViewStatement(
    dialect,
    View(dialect, "user_summary"),
    query=query
)
sql, params = create_view.to_sql()
# sql: 'CREATE VIEW "user_summary" AS SELECT "id", "name", "email" FROM "users"'
```

## View with Column Aliases

```python
create_view = CreateViewStatement(
    dialect,
    View(dialect, "user_details"),
    query=query,
    column_aliases=["user_id", "full_name", "contact_email"]
)
sql, params = create_view.to_sql()
# sql: 'CREATE VIEW "user_details" ("user_id", "full_name", "contact_email") AS SELECT ...'
```

## View with OR REPLACE

```python
create_view = CreateViewStatement(
    dialect,
    View(dialect, "user_summary"),
    query=query,
    replace=True
)
sql, params = create_view.to_sql()
# sql: 'CREATE OR REPLACE VIEW "user_summary" AS ...'
```

## View with TEMPORARY (SQLite)

```python
create_view = CreateViewStatement(
    dialect,
    View(dialect, "temp_stats"),
    query=query,
    temporary=True
)
sql, params = create_view.to_sql()
# sql: 'CREATE TEMPORARY VIEW "temp_stats" AS ...'
```

## Drop View

```python
from rhosocial.activerecord.backend.expression.objects import View
from rhosocial.activerecord.backend.expression.statements import DropViewStatement

# Basic drop
drop_view = DropViewStatement(
    dialect,
    View(dialect, "old_view")
)
sql, params = drop_view.to_sql()
# sql: 'DROP VIEW "old_view"'

# Drop if exists
drop_view = DropViewStatement(
    dialect,
    View(dialect, "old_view"),
    if_exists=True
)
sql, params = drop_view.to_sql()
# sql: 'DROP VIEW IF EXISTS "old_view"'
```

## Executing View DDL

```python
from rhosocial.activerecord.backend.expression import (
    Column,
    ColumnDefinition,
    NamedRelationRef,
    QueryStatement,
)
from rhosocial.activerecord.backend.expression.objects import Table, View
from rhosocial.activerecord.backend.expression.statements import (
    ColumnConstraint,
    ColumnNotNullConstraint,
    ColumnPrimaryKeyConstraint,
    CreateTableStatement,
    CreateViewStatement,
)
from rhosocial.activerecord.backend.expression.types import IntegerType, VarCharType

# Create a table first
user_columns = [
    ColumnDefinition(
        dialect, "id", IntegerType(dialect),
        constraints=[ColumnConstraint(dialect, branch=ColumnPrimaryKeyConstraint(dialect))]
    ),
    ColumnDefinition(
        dialect, "name", VarCharType(dialect, length=100),
        constraints=[ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect))]
    ),
    ColumnDefinition(dialect, "email", VarCharType(dialect, length=255)),
]
create_table = CreateTableStatement(dialect, Table(dialect, "users"), columns=user_columns)
sql, params = create_table.to_sql()
backend.execute(sql, params)

# Create a view
view_query = QueryStatement(
    dialect,
    select=[
        Column(dialect, "id"),
        Column(dialect, "name"),
        Column(dialect, "email")
    ],
    from_=NamedRelationRef(dialect, Table(dialect, "users"))
)
create_view = CreateViewStatement(dialect, View(dialect, "user_summary"), query=view_query)
sql, params = create_view.to_sql()
backend.execute(sql, params)

# Introspection: List views
views = backend.introspector.list_views()
for v in views:
    print(f"View: {v.name}")
```

> **Note**: SQLite supports views. Different databases may have different view capabilities (e.g., MySQL's ALGORITHM, PostgreSQL's materialized views). Refer to your backend documentation.

## Example Code

Full example: [docs/examples/chapter_03_modeling/ddl_views.py](../../../examples/chapter_03_modeling/ddl_views.py)

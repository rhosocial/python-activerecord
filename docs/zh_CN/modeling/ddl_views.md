# 视图 DDL

视图是基于 SELECT 查询的虚拟表。它们不存储数据，但提供了一种简化复杂查询、实施安全性和抽象架构变化的方式。

## 创建视图

```python
from rhosocial.activerecord.backend.expression import (
    Column,
    NamedRelationRef,
    QueryStatement,
)
from rhosocial.activerecord.backend.expression.objects import Table, View
from rhosocial.activerecord.backend.expression.statements import CreateViewStatement

# 基础视图
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

## 带列别名的视图

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

## OR REPLACE 视图

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

## TEMPORARY 视图 (SQLite)

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

## 删除视图

```python
from rhosocial.activerecord.backend.expression.objects import View
from rhosocial.activerecord.backend.expression.statements import DropViewStatement

# 基础删除
drop_view = DropViewStatement(
    dialect,
    View(dialect, "old_view")
)
sql, params = drop_view.to_sql()
# sql: 'DROP VIEW "old_view"'

# 条件删除
drop_view = DropViewStatement(
    dialect,
    View(dialect, "old_view"),
    if_exists=True
)
sql, params = drop_view.to_sql()
# sql: 'DROP VIEW IF EXISTS "old_view"'
```

## 执行视图 DDL

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

# 先创建表
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

# 创建视图
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

# 内省：列出视图
views = backend.introspector.list_views()
for v in views:
    print(f"View: {v.name}")
```

> **注意**：SQLite 支持视图。不同的数据库可能具有不同的视图功能（例如 MySQL 的 ALGORITHM、PostgreSQL 的物化视图）。请参阅你的后端文档。

## 示例代码

完整示例：[docs/examples/chapter_03_modeling/ddl_views.py](../../../examples/chapter_03_modeling/ddl_views.py)

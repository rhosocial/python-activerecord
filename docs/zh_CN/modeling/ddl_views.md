# 视图 DDL

视图是基于 SELECT 查询的虚拟表。它们不存储数据，但提供了一种简化复杂查询、实施安全性和抽象架构变化的方式。

## 创建视图

```python
from rhosocial.activerecord.backend.expression import (
    CreateViewExpression,
    QueryExpression,
    TableExpression,
    Column
)

# 基础视图
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

## 带列别名的视图

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

## OR REPLACE 视图

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

## TEMPORARY 视图 (SQLite)

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

## 删除视图

```python
from rhosocial.activerecord.backend.expression import DropViewExpression

# 基础删除
drop_view = DropViewExpression(
    dialect,
    view_name="old_view"
)
sql, params = drop_view.to_sql()
# sql: 'DROP VIEW "old_view"'

# 条件删除
drop_view = DropViewExpression(
    dialect,
    view_name="old_view",
    if_exists=True
)
sql, params = drop_view.to_sql()
# sql: 'DROP VIEW IF EXISTS "old_view"'
```

## 执行视图 DDL

```python
# 先创建表
create_table = CreateTableExpression(dialect, "users", user_columns)
backend.execute(create_table.to_sql())

# 创建视图
create_view = CreateViewExpression(dialect, "user_summary", view_query)
backend.execute(create_view.to_sql())

# 内省：列出视图
views = backend.introspector.list_views()
for v in views:
    print(f"View: {v.name}")
```

> **注意**：SQLite 支持视图。不同的数据库可能具有不同的视图功能（例如 MySQL 的 ALGORITHM、PostgreSQL 的物化视图）。请参阅你的后端文档。

## 示例代码

完整示例：[docs/examples/chapter_03_modeling/ddl_views.py](../../../examples/chapter_03_modeling/ddl_views.py)
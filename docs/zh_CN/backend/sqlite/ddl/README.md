# DDL 操作

## 概述

本节介绍 SQLite 后端的 DDL（数据定义语言）操作。rhosocial-activerecord 中的所有 DDL 都是基于表达式的——您在 Python 中定义 schema，框架生成 SQL，然后通过后端执行。

与其他数据库相比，SQLite 有显著的 DDL 限制。本章记录了支持的功能和可用的解决方法。

## 支持的操作

| 操作 | SQLite 支持 | 备注 |
|------|------------|------|
| CREATE TABLE | 是 | 包括 IF NOT EXISTS、临时表 |
| ALTER TABLE | 有限 | 不支持 ALTER COLUMN；有限的 RENAME/DROP |
| DROP TABLE | 是 | 不支持 CASCADE/RESTRICT |
| CREATE INDEX | 是 | 仅 B-tree；支持部分索引和函数索引 |
| DROP INDEX | 是 | 支持 IF EXISTS |
| CREATE VIEW | 是 | 不支持 OR REPLACE，不支持物化视图 |
| DROP VIEW | 是 | 支持 IF EXISTS |
| TRUNCATE | 否 | 使用 DELETE FROM + VACUUM |
| CREATE SCHEMA | 否 | SQLite 没有 schema 概念 |
| CREATE SEQUENCE | 否 | 改为使用 AUTOINCREMENT |

## CREATE TABLE

SQLite 支持带 IF NOT EXISTS 的 CREATE TABLE。后端生成 SQLite 特定的 DDL：

```python
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from typing import ClassVar

class User(ActiveRecord):
    id: int | None = None
    username: str
    email: str
    age: int
    is_active: bool = True

    c: ClassVar[FieldProxy] = FieldProxy()

    @classmethod
    def table_name(cls) -> str:
        return 'users'
```

为 SQLite 生成的 SQL：

```sql
CREATE TABLE IF NOT EXISTS "users" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT,
    "username" VARCHAR NOT NULL,
    "email" VARCHAR NOT NULL,
    "age" INTEGER NOT NULL,
    "is_active" BOOLEAN NOT NULL DEFAULT 1
)
```

关键的 SQLite 差异：
- 在 `INTEGER PRIMARY KEY` 上使用 `AUTOINCREMENT`（不是列属性）
- 没有 ENGINE、CHARSET 或 COLLATE 选项
- 布尔值存储为 INTEGER（0/1）

## ALTER TABLE

与其他数据库相比，SQLite 的 ALTER TABLE 支持非常有限：

### 添加列

```python
# 支持——但在 SQLite 3.35.0 之前不支持 IF NOT EXISTS
ALTER TABLE users ADD COLUMN phone VARCHAR
```

### 重命名列

需要 SQLite 3.25.0+：

```python
# SQLite 3.25.0+
ALTER TABLE users RENAME COLUMN phone TO telephone
```

### 删除列

需要 SQLite 3.35.0+：

```python
# SQLite 3.35.0+
ALTER TABLE users DROP COLUMN phone
```

### 不支持的操作

| 操作 | SQLite | MySQL | PostgreSQL |
|------|--------|-------|------------|
| ALTER COLUMN（类型更改） | 否 | MODIFY COLUMN | ALTER COLUMN ... TYPE |
| ALTER COLUMN（重命名） | 否 | CHANGE COLUMN | ALTER COLUMN ... RENAME |
| ADD COLUMN with IF NOT EXISTS | 否（< 3.35.0） | 否 | 是 |
| DROP COLUMN with IF EXISTS | 否（< 3.35.0） | 否 | 是 |

对于 SQLite 中的列类型更改，通常需要创建新表、复制数据、删除旧表并重命名新表。

## DROP TABLE

```python
# 基本删除
DROP TABLE users

# 带 IF EXISTS
DROP TABLE IF EXISTS users
```

SQLite 不支持 CASCADE 或 RESTRICT 关键字。如果传递它们，将被静默忽略。

## CREATE INDEX

SQLite 支持具有部分索引和函数索引功能的 B-tree 索引：

```python
# 基本索引
CREATE INDEX idx_users_email ON users(email)

# 唯一索引
CREATE UNIQUE INDEX idx_users_email ON users(email)

# 部分索引（SQLite 3.8.0+）
CREATE INDEX idx_active_users ON users(email) WHERE is_active = 1

# 函数索引
CREATE INDEX idx_users_lower_email ON users(lower(email))
```

| 索引功能 | SQLite | MySQL | PostgreSQL |
|---------|--------|-------|------------|
| B-tree | 是 | 是 | 是 |
| HASH | 否 | 是 | 是 |
| GIN/GiST/BRIN | 否 | 否 | 是 |
| 部分索引 | 是 | 否 | 是 |
| 函数索引 | 是 | 否 | 是 |
| CONCURRENTLY | 否 | 否 | 是 |

## Schema 支持

SQLite 没有 schema 或命名空间概念。如果您在 ActiveRecord 模型上设置 `schema()`，它将被静默忽略。

## 序列

SQLite 不支持序列。改为在 `INTEGER PRIMARY KEY` 上使用 `AUTOINCREMENT`：

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
)
```

请注意，AUTOINCREMENT 阻止 rowid 重用并增加存储开销。对于大多数情况，省略 AUTOINCREMENT 并依赖隐式 rowid 行为就足够了。

## 运行 DDL

```python
# 生成 DDL SQL 但不执行
from rhosocial.activerecord.base.ddl_generator import DDLGenerator

create_sql = DDLGenerator.generate_create_table(User)
print(create_sql)

# 通过后端执行 DDL
with User.connection() as conn:
    conn.execute(create_sql)

# 或一步生成并执行
DDLGenerator.create_table(User)
```

## 另请参阅

- [后端特定功能](../backend_specific_features/README.md) — SQLite 特定功能
- [类型适配器](../type_adapters/README.md) — 类型映射
- [核心：DDL](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/modeling/ddl)

💡 *AI 提示*："当 ALTER TABLE 受限时，如何在 SQLite 中重命名列？"

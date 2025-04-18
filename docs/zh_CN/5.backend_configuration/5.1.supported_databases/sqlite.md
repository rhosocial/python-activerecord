# SQLite 支持

rhosocial ActiveRecord 为 SQLite 数据库系统提供了全面的支持。本文档涵盖了在使用 rhosocial ActiveRecord 与 SQLite 时的特定功能、配置选项和注意事项。

## 概述

SQLite 是一个自包含、无服务器、零配置、事务性 SQL 数据库引擎。它是一个 C 语言库，提供了一个轻量级的基于磁盘的数据库，不需要单独的服务器进程。它非常适合开发、测试和中小型应用程序。rhosocial ActiveRecord 的 SQLite 后端提供了一个一致的接口，同时尊重 SQLite 的独特特性。

## 功能

- 完整的 CRUD 操作支持
- 事务管理与 SQLite 的隔离级别
- 支持 SQLite 特定的 pragma 和配置
- 支持内存数据库用于测试
- 基于文件的数据库，配置简单
- 支持 SQLite 的 JSON 函数（SQLite 3.9+ 版本）
- 自动处理 SQLite 的类型亲和性系统
- 支持 SQLite 的全文搜索功能

## 配置

要将 SQLite 与 rhosocial ActiveRecord 一起使用，您需要使用 SQLite 后端配置您的模型：

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend import ConnectionConfig
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend

class User(ActiveRecord):
    pass

# 配置模型使用 SQLite 后端（文件数据库）
User.configure(
    ConnectionConfig(
        database='/path/to/database.db',  # 数据库文件路径
        # 可选参数
        pragmas={
            'journal_mode': 'WAL',       # 写入前日志模式
            'synchronous': 'NORMAL',      # 同步模式
            'foreign_keys': 'ON',         # 启用外键约束
            'cache_size': -1000           # 缓存大小（KB，负值表示内存中）
        }
    ),
    SQLiteBackend
)

# 使用内存数据库
User.configure(
    ConnectionConfig(
        database=':memory:',  # 内存数据库
        pragmas={'foreign_keys': 'ON'}
    ),
    SQLiteBackend
)
```

## 数据类型映射

rhosocial ActiveRecord 将 Python 数据类型映射到 SQLite 数据类型，以下是主要的映射关系：

| Python 类型 | SQLite 类型 |
|------------|-------------|
| int        | INTEGER     |
| float      | REAL        |
| str        | TEXT        |
| bytes      | BLOB        |
| bool       | INTEGER     |
| datetime   | TEXT        |
| date       | TEXT        |
| time       | TEXT        |
| Decimal    | TEXT        |
| uuid.UUID  | TEXT        |
| dict, list | TEXT (JSON) |

请注意，SQLite 使用动态类型系统，称为"类型亲和性"。这意味着 SQLite 可以存储任何类型的数据到任何列中，但会尝试将数据转换为列的声明类型。rhosocial ActiveRecord 处理这些转换，确保数据正确存储和检索。

## 事务支持

SQLite 提供了事务支持，rhosocial ActiveRecord 提供了简单的事务管理接口：

```python
# 使用默认隔离级别的事务
with User.transaction() as tx:
    user = User(name='Alice')
    user.save()
    # 如果在事务块内发生异常，事务将自动回滚
```

SQLite 支持以下隔离级别：

- **DEFERRED**（默认）：延迟获取锁，直到需要时
- **IMMEDIATE**：立即获取保留锁
- **EXCLUSIVE**：立即获取排他锁

```python
from rhosocial.activerecord.backend import TransactionIsolationLevel

# 指定隔离级别的事务
with User.transaction(isolation_level=TransactionIsolationLevel.IMMEDIATE) as tx:
    user = User.find_by(name='Alice')
    user.balance += 100
    user.save()
```

## 批量操作

SQLite 支持批量插入和更新操作：

```python
# 批量插入
users = [
    User(name='Alice', email='alice@example.com'),
    User(name='Bob', email='bob@example.com'),
    User(name='Charlie', email='charlie@example.com')
]
User.bulk_insert(users)

# 批量更新
User.update_all(status='active', where={'group_id': 5})

# 批量删除
User.delete_all(where={'status': 'inactive'})
```

## JSON 支持

SQLite 3.9+ 版本提供了 JSON 支持，rhosocial ActiveRecord 允许您使用这些功能：

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPk, Field

class Product(ActiveRecord):
    id = IntegerPk()
    name = Field(str)
    properties = Field(dict)  # 将存储为 JSON 字符串
    
# 使用 JSON 数据
product = Product(
    name='智能手机',
    properties={
        'color': '黑色',
        'dimensions': {'width': 7, 'height': 15, 'depth': 0.8},
        'features': ['5G', '防水', '双摄像头']
    }
)
product.save()

# 使用 JSON 查询（需要 SQLite 3.9+）
products = Product.find_all(
    Product.properties.json_extract('$.color') == '黑色'
)
```

## 全文搜索

SQLite 提供了 FTS5（全文搜索）扩展，rhosocial ActiveRecord 支持这一特性：

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPk, Field

class Article(ActiveRecord):
    id = IntegerPk()
    title = Field(str)
    content = Field(str)
    
    class Meta:
        table_name = 'articles'
        # 注意：需要在 SQLite 中创建 FTS 虚拟表

# 使用全文搜索
articles = Article.find_all(
    Article.contains(['title', 'content'], 'python 编程')
)
```

## 内存数据库

SQLite 的一个独特特性是支持完全在内存中运行的数据库，这对于测试特别有用：

```python
# 配置内存数据库
User.configure(
    ConnectionConfig(database=':memory:'),
    SQLiteBackend
)

# 现在可以创建表并使用数据库，但数据只存在于内存中
# 当程序结束时，所有数据都会丢失
```

## 性能优化

使用 SQLite 后端时的一些性能优化建议：

1. **使用 WAL 模式**：写入前日志（WAL）模式通常比默认的日志模式提供更好的并发性和性能
   ```python
   User.connection.execute_pragma('journal_mode', 'WAL')
   ```

2. **调整同步模式**：根据您的需求平衡性能和数据安全性
   ```python
   # FULL 提供最高的安全性，但性能最低
   # NORMAL 是一个良好的平衡点
   # OFF 提供最高的性能，但在系统崩溃时可能丢失数据
   User.connection.execute_pragma('synchronous', 'NORMAL')
   ```

3. **增加缓存大小**：为频繁访问的数据库分配更多内存
   ```python
   # 负值表示千字节（KB）
   User.connection.execute_pragma('cache_size', -10000)  # 约 10MB
   ```

4. **使用适当的索引**：为经常在 WHERE、JOIN 和 ORDER BY 子句中使用的列创建索引

5. **批量操作**：使用事务和批量操作减少磁盘 I/O

6. **减少磁盘同步**：在批量导入数据时，考虑暂时禁用同步
   ```python
   with User.transaction() as tx:
       User.connection.execute_pragma('synchronous', 'OFF')
       # 执行批量操作
       # ...
   # 事务结束后，同步模式将恢复为默认值
   ```

## 限制和注意事项

使用 SQLite 后端时需要注意的一些限制：

1. **并发访问**：SQLite 对并发写入的支持有限，不适合高并发写入场景

2. **数据库大小**：虽然 SQLite 可以支持最大 281 TB 的数据库，但实际上，当数据库大小超过几 GB 时，性能可能会下降

3. **网络访问**：SQLite 是一个本地文件数据库，不直接支持网络访问

4. **锁定粒度**：SQLite 使用数据库级锁，而不是行级锁或表级锁

5. **ALTER TABLE 限制**：SQLite 的 ALTER TABLE 功能有限，不支持某些模式更改操作

## 版本兼容性

rhosocial ActiveRecord 的 SQLite 后端支持以下版本：

- SQLite 3.7.0 及更高版本

某些高级功能（如 JSON 支持）需要更新的 SQLite 版本：

- JSON 函数：需要 SQLite 3.9.0+
- FTS5 全文搜索：需要 SQLite 3.9.0+
- 窗口函数：需要 SQLite 3.25.0+

## 总结

SQLite 是一个轻量级但功能强大的数据库选项，特别适合开发、测试和中小型应用程序。rhosocial ActiveRecord 的 SQLite 后端提供了一个简单而强大的接口，使您能够充分利用 SQLite 的功能，同时保持与其他数据库后端的 API 一致性。
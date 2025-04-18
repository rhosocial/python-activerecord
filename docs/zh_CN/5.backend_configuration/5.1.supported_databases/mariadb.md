# MariaDB 支持

rhosocial ActiveRecord 为 MariaDB 数据库系统提供了全面的支持。本文档涵盖了在使用 rhosocial ActiveRecord 与 MariaDB 时的特定功能、配置选项和注意事项。

> **重要提示**：MariaDB 后端正在作为单独的代码包开发中，将在未来发布。本文档作为即将推出的功能的参考提供。

## 概述

MariaDB 是 MySQL 的一个社区开发的分支，由 MySQL 的原始开发者创建，旨在保持开源并提供更多功能。rhosocial ActiveRecord 的 MariaDB 后端提供了一个一致的接口，同时尊重 MariaDB 的独特特性。

## MariaDB 特有功能

- 完整的 CRUD 操作支持
- 事务管理与 MariaDB 的隔离级别
- 支持 MariaDB 特定的配置选项
- 支持 InnoDB、MyISAM、Aria 和 ColumnStore 等存储引擎
- 支持 MariaDB 的 JSON 函数（MariaDB 10.2+）
- 支持全文搜索功能
- 支持地理空间数据类型和函数
- 支持 MariaDB 特有的窗口函数（MariaDB 10.2+）

## 配置

要将 MariaDB 与 rhosocial ActiveRecord 一起使用，您需要使用 MariaDB 后端配置您的模型：

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend import ConnectionConfig
from rhosocial.activerecord.backend.impl.mariadb import MariaDBBackend

class User(ActiveRecord):
    pass

# 配置模型使用 MariaDB 后端
User.configure(
    ConnectionConfig(
        host='localhost',      # MariaDB 服务器主机
        port=3306,            # MariaDB 服务器端口
        database='my_db',     # 数据库名称
        user='username',      # 用户名
        password='password',  # 密码
        # 可选参数
        charset='utf8mb4',    # 字符集
        collation='utf8mb4_unicode_ci',  # 排序规则
        ssl_mode='REQUIRED',  # SSL 模式
        connect_timeout=10,   # 连接超时（秒）
        pool_size=5,          # 连接池大小
        pool_recycle=3600     # 连接回收时间（秒）
    ),
    MariaDBBackend
)
```

## 数据类型映射

rhosocial ActiveRecord 将 Python 数据类型映射到 MariaDB 数据类型，以下是主要的映射关系：

| Python 类型 | MariaDB 类型 |
|------------|----------------|
| int        | INT            |
| float      | DOUBLE         |
| str        | VARCHAR, TEXT  |
| bytes      | BLOB           |
| bool       | TINYINT(1)     |
| datetime   | DATETIME       |
| date       | DATE           |
| time       | TIME           |
| Decimal    | DECIMAL        |
| uuid.UUID  | CHAR(36)       |
| dict, list | JSON           |

## 存储引擎

MariaDB 支持多种存储引擎，包括一些 MySQL 中不可用的引擎。rhosocial ActiveRecord 允许您在表级别指定存储引擎：

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPk

class Product(ActiveRecord):
    id = IntegerPk()
    
    class Meta:
        table_name = 'products'
        engine = 'InnoDB'  # 指定 InnoDB 存储引擎
        charset = 'utf8mb4'
        collation = 'utf8mb4_unicode_ci'
```

MariaDB 特有的存储引擎包括：

- **Aria**：MyISAM 的改进版本，提供更好的崩溃恢复能力
- **ColumnStore**：面向列的存储引擎，适合数据仓库和分析工作负载
- **Spider**：分布式存储引擎，支持分片
- **Connect**：用于访问外部数据的存储引擎

除此之外，MariaDB 还支持 MySQL 中常见的存储引擎：

- **InnoDB**：支持事务、外键和行级锁定，适合大多数应用场景
- **MyISAM**：不支持事务和外键，但在某些读密集型场景下性能较好
- **MEMORY**：将数据存储在内存中，适合临时表和缓存
- **ARCHIVE**：适合存储和检索大量很少被查询的历史数据

## 事务支持

MariaDB 支持事务（使用 InnoDB 引擎），rhosocial ActiveRecord 提供了简单的事务管理接口：

```python
from rhosocial.activerecord.backend import TransactionIsolationLevel

# 使用默认隔离级别的事务
with User.transaction() as tx:
    user = User(name='Alice')
    user.save()
    # 如果在事务块内发生异常，事务将自动回滚

# 指定隔离级别的事务
with User.transaction(isolation_level=TransactionIsolationLevel.SERIALIZABLE) as tx:
    user = User.find_by(name='Alice')
    user.balance += 100
    user.save()
```

MariaDB 支持的隔离级别包括：

- **READ UNCOMMITTED**：最低隔离级别，允许脏读
- **READ COMMITTED**：防止脏读，但允许不可重复读和幻读
- **REPEATABLE READ**：MariaDB 的默认级别，防止脏读和不可重复读，但允许幻读
- **SERIALIZABLE**：最高隔离级别，防止所有并发问题，但性能最低

## 锁定策略

rhosocial ActiveRecord 支持 MariaDB 的锁定功能，用于处理并发访问：

```python
# 悲观锁 - 使用 FOR UPDATE 锁定行
with User.transaction() as tx:
    user = User.find_by(id=1, lock='FOR UPDATE')
    user.balance -= 100
    user.save()

# 共享锁 - 使用 LOCK IN SHARE MODE
with User.transaction() as tx:
    user = User.find_by(id=1, lock='LOCK IN SHARE MODE')
    # 读取但不修改数据
```

## 批量操作

MariaDB 支持高效的批量插入和更新操作：

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

MariaDB 10.2+ 提供了原生 JSON 支持，rhosocial ActiveRecord 允许您使用这些功能：

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPk, Field

class Product(ActiveRecord):
    id = IntegerPk()
    name = Field(str)
    properties = Field(dict)  # 将存储为 JSON
    
# 使用 JSON 数据
product = Product(
    name='Smartphone',
    properties={
        'color': 'black',
        'dimensions': {'width': 7, 'height': 15, 'depth': 0.8},
        'features': ['5G', 'Water resistant', 'Dual camera']
    }
)
product.save()

# 使用 JSON 查询
products = Product.find_all(
    Product.properties.json_extract('$.color') == 'black'
)
```

## 全文搜索

MariaDB 提供全文搜索功能，rhosocial ActiveRecord 支持这一特性：

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPk, Field

class Article(ActiveRecord):
    id = IntegerPk()
    title = Field(str)
    content = Field(str)
    
    class Meta:
        table_name = 'articles'
        indexes = [
            {'type': 'FULLTEXT', 'fields': ['title', 'content']}
        ]

# 使用全文搜索
articles = Article.find_all(
    Article.match(['title', 'content'], 'python programming')
)
```

## 与 MySQL 的区别

虽然 MariaDB 是 MySQL 的一个分支，但两者之间存在一些重要差异：

1. **存储引擎**：MariaDB 包含一些 MySQL 中不可用的存储引擎，如 Aria、ColumnStore、Spider 和 Connect
2. **JSON 实现**：MariaDB 和 MySQL 的 JSON 实现有所不同，特别是在函数名称和性能方面
3. **窗口函数**：MariaDB 从 10.2 版本开始支持窗口函数，而 MySQL 从 8.0 版本开始支持
4. **系统表**：两者的系统表结构有所不同
5. **复制**：MariaDB 提供了一些 MySQL 中不可用的复制功能，如多源复制
6. **插件架构**：MariaDB 有更灵活的插件架构
7. **授权模型**：MariaDB 保持完全开源，而 MySQL 由 Oracle 拥有，有些功能可能需要商业许可

如果您的应用程序特别依赖于 MariaDB 特有的功能，建议使用专门的 MariaDB 后端。如果您需要 MySQL 特有的功能，请参考 [MySQL 文档](mysql.md)。

## 性能优化

使用 MariaDB 时，可以考虑以下性能优化技术：

1. **适当的索引**：为经常在 WHERE 子句中使用的列创建索引
2. **查询优化**：使用 EXPLAIN 分析查询性能
3. **连接池**：使用连接池减少连接开销
4. **批量操作**：使用批量插入和更新减少数据库往返
5. **分区**：对大表使用表分区
6. **缓存**：实现应用层缓存减少数据库负载
7. **利用 MariaDB 特有的优化器改进**：MariaDB 包含一些 MySQL 中不可用的优化器改进

## 常见问题

### 连接问题

如果遇到连接问题，请检查：

- 主机名和端口是否正确
- 用户名和密码是否正确
- MariaDB 服务器是否正在运行
- 防火墙设置是否允许连接
- 用户是否有权限访问指定的数据库

### 字符集问题

为避免字符集问题，建议：

- 使用 utf8mb4 字符集和 utf8mb4_unicode_ci 排序规则
- 确保数据库、表和连接都使用相同的字符集

### 性能问题

如果遇到性能问题，请考虑：

- 检查查询是否使用了适当的索引
- 优化复杂查询
- 增加连接池大小
- 调整 MariaDB 服务器配置
- 考虑使用 MariaDB 特有的存储引擎，如 ColumnStore 用于分析查询

## 总结

rhosocial ActiveRecord 的 MariaDB 后端提供了一个强大而灵活的接口，用于与 MariaDB 数据库交互。通过利用 MariaDB 的特定功能，同时保持 ActiveRecord 的简洁 API，您可以构建高效且可维护的数据库驱动应用程序。
# MySQL/MariaDB 支持

Python ActiveRecord 为 MySQL 和 MariaDB 数据库系统提供了全面的支持。本文档涵盖了在使用 Python ActiveRecord 与 MySQL/MariaDB 时的特定功能、配置选项和注意事项。

## 概述

MySQL 是世界上最流行的开源关系型数据库管理系统之一，而 MariaDB 是 MySQL 的一个社区开发的分支。Python ActiveRecord 的 MySQL/MariaDB 后端提供了一个一致的接口，同时尊重 MySQL/MariaDB 的独特特性。

## 功能

- 完整的 CRUD 操作支持
- 事务管理与 MySQL/MariaDB 的隔离级别
- 支持 MySQL/MariaDB 特定的配置选项
- 支持 InnoDB 和 MyISAM 等存储引擎
- 支持 MySQL/MariaDB 的 JSON 函数（MySQL 5.7+ 或 MariaDB 10.2+）
- 支持全文搜索功能
- 支持地理空间数据类型和函数

## 配置

要将 MySQL/MariaDB 与 Python ActiveRecord 一起使用，您需要使用 MySQL 后端配置您的模型：

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend import ConnectionConfig
from rhosocial.activerecord.backend.impl.mysql import MySQLBackend

class User(ActiveRecord):
    pass

# 配置模型使用 MySQL 后端
User.configure(
    ConnectionConfig(
        host='localhost',      # MySQL 服务器主机
        port=3306,            # MySQL 服务器端口
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
    MySQLBackend
)
```

## 数据类型映射

Python ActiveRecord 将 Python 数据类型映射到 MySQL/MariaDB 数据类型，以下是主要的映射关系：

| Python 类型 | MySQL/MariaDB 类型 |
|------------|-------------------|
| int        | INT               |
| float      | DOUBLE            |
| str        | VARCHAR, TEXT     |
| bytes      | BLOB              |
| bool       | TINYINT(1)        |
| datetime   | DATETIME          |
| date       | DATE              |
| time       | TIME              |
| Decimal    | DECIMAL           |
| uuid.UUID  | CHAR(36)          |
| dict, list | JSON              |

## 存储引擎

MySQL/MariaDB 支持多种存储引擎，每种都有其特点和用例。Python ActiveRecord 允许您在表级别指定存储引擎：

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

常用的存储引擎包括：

- **InnoDB**：支持事务、外键和行级锁定，适合大多数应用场景
- **MyISAM**：不支持事务和外键，但在某些读密集型场景下性能较好
- **MEMORY**：将数据存储在内存中，适合临时表和缓存
- **ARCHIVE**：适合存储和检索大量很少被查询的历史数据

## 事务支持

MySQL/MariaDB 支持事务（使用 InnoDB 引擎），Python ActiveRecord 提供了简单的事务管理接口：

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

MySQL/MariaDB 支持的隔离级别包括：

- **READ UNCOMMITTED**：最低隔离级别，允许脏读
- **READ COMMITTED**：防止脏读，但允许不可重复读和幻读
- **REPEATABLE READ**：MySQL/MariaDB 的默认级别，防止脏读和不可重复读，但允许幻读
- **SERIALIZABLE**：最高隔离级别，防止所有并发问题，但性能最低

## 锁定策略

Python ActiveRecord 支持 MySQL/MariaDB 的锁定功能，用于处理并发访问：

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

MySQL/MariaDB 支持高效的批量插入和更新操作：

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

MySQL 5.7+ 和 MariaDB 10.2+ 提供了原生 JSON 支持，Python ActiveRecord 允许您使用这些功能：

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

MySQL/MariaDB 提供全文搜索功能，Python ActiveRecord 支持这一特性：

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
            {'type': 'FULLTEXT', 'columns': ['title', 'content']}
        ]

# 使用全文搜索
articles = Article.find_all(
    Article.match(['title', 'content'], 'python programming')
)
```

## 性能优化

使用 MySQL/MariaDB 后端时的一些性能优化建议：

1. **适当的索引**：为经常在 WHERE、JOIN 和 ORDER BY 子句中使用的列创建索引
2. **连接池**：使用连接池减少连接创建的开销
3. **批量操作**：尽可能使用批量插入、更新和删除
4. **查询优化**：使用 EXPLAIN 分析查询性能，避免全表扫描
5. **合适的字段类型**：选择适合数据的最小字段类型
6. **分区表**：对大表使用分区来提高查询性能
7. **读写分离**：对读密集型应用考虑使用主从复制和读写分离

## 限制和注意事项

使用 MySQL/MariaDB 后端时需要注意的一些限制：

1. **标识符长度**：表名、列名等标识符的最大长度为 64 个字符
2. **事务支持**：只有 InnoDB 等存储引擎支持事务
3. **锁定行为**：不同存储引擎的锁定行为有所不同
4. **JSON 支持**：需要 MySQL 5.7+ 或 MariaDB 10.2+ 才能使用 JSON 功能
5. **字符集**：建议使用 utf8mb4 字符集以支持完整的 Unicode 字符集

## 版本兼容性

Python ActiveRecord 的 MySQL/MariaDB 后端支持以下版本：

- MySQL 5.7 及更高版本
- MariaDB 10.2 及更高版本

较旧的版本可能也能工作，但某些功能（如 JSON 支持）可能不可用。
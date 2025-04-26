# SQL Server 支持

rhosocial ActiveRecord 为 Microsoft SQL Server 数据库系统提供了全面的支持。本文档涵盖了在使用 rhosocial ActiveRecord 与 SQL Server 时的特定功能、配置选项和注意事项。

## 概述

Microsoft SQL Server 是一个企业级关系型数据库管理系统，提供了高性能、高可用性和先进的安全功能。rhosocial ActiveRecord 的 SQL Server 后端提供了一个一致的接口，同时尊重 SQL Server 的独特特性和企业级功能。

## 功能

- 完整的 CRUD 操作支持
- 事务管理与 SQL Server 的隔离级别
- 支持 SQL Server 特定的数据类型和函数
- 支持存储过程和函数调用
- 支持 SQL Server 的 JSON 功能（SQL Server 2016 及更高版本）
- 支持 SQL Server 的空间数据类型
- 支持 SQL Server 的全文搜索功能
- 支持 SQL Server 的临时表
- 支持 Windows 身份验证和 SQL 身份验证

## 配置

要将 SQL Server 与 rhosocial ActiveRecord 一起使用，您需要使用 SQL Server 后端配置您的模型：

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend import ConnectionConfig
from rhosocial.activerecord.backend.impl.sqlserver import SQLServerBackend

class User(ActiveRecord):
    pass

# 配置模型使用 SQL Server 后端（SQL 身份验证）
User.configure(
    ConnectionConfig(
        host='localhost',      # SQL Server 主机
        port=1433,            # SQL Server 端口
        database='my_db',     # 数据库名称
        user='username',      # 用户名
        password='password',  # 密码
        # 可选参数
        schema='dbo',         # 模式名称
        trust_server_certificate=False,  # 是否信任服务器证书
        encrypt=True,         # 是否加密连接
        connection_timeout=30,  # 连接超时（秒）
        pool_size=5,          # 连接池大小
        pool_recycle=3600     # 连接回收时间（秒）
    ),
    SQLServerBackend
)

# 使用 Windows 身份验证
User.configure(
    ConnectionConfig(
        host='localhost',
        database='my_db',
        trusted_connection=True  # 使用 Windows 身份验证
    ),
    SQLServerBackend
)
```

## 数据类型映射

rhosocial ActiveRecord 将 Python 数据类型映射到 SQL Server 数据类型，以下是主要的映射关系：

| Python 类型 | SQL Server 类型 |
|------------|----------------|
| int        | INT            |
| float      | FLOAT          |
| str        | NVARCHAR, NTEXT |
| bytes      | VARBINARY      |
| bool       | BIT            |
| datetime   | DATETIME2      |
| date       | DATE           |
| time       | TIME           |
| Decimal    | DECIMAL        |
| uuid.UUID  | UNIQUEIDENTIFIER |
| dict, list | NVARCHAR(MAX) (JSON) |

## 模式（Schema）支持

SQL Server 使用模式（Schema）来组织数据库对象。rhosocial ActiveRecord 允许您指定模式：

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPk

class Product(ActiveRecord):
    id = IntegerPk()
    
    class Meta:
        table_name = 'products'
        schema = 'inventory'  # 指定模式
```

## 事务支持

SQL Server 提供了强大的事务支持，rhosocial ActiveRecord 提供了简单的事务管理接口：

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

SQL Server 支持的隔离级别包括：

- **READ UNCOMMITTED**：最低隔离级别，允许脏读、不可重复读和幻读
- **READ COMMITTED**：SQL Server 的默认级别，防止脏读，但允许不可重复读和幻读
- **REPEATABLE READ**：防止脏读和不可重复读，但允许幻读
- **SERIALIZABLE**：最高隔离级别，防止所有并发问题
- **SNAPSHOT**：提供基于版本的并发控制，允许读取操作不被写入操作阻塞

## 锁定策略

rhosocial ActiveRecord 支持 SQL Server 的锁定功能，用于处理并发访问：

```python
# 悲观锁 - 使用 WITH (UPDLOCK) 锁定行
with User.transaction() as tx:
    user = User.find_by(id=1, lock='WITH (UPDLOCK)')
    user.balance -= 100
    user.save()

# 表锁 - 使用 WITH (TABLOCK)
with User.transaction() as tx:
    users = User.find_all(where={'status': 'active'}, lock='WITH (TABLOCK)')
    # 处理用户
    
# 使用 NOLOCK（脏读）
users = User.find_all(where={'status': 'active'}, lock='WITH (NOLOCK)')
```

## 批量操作

SQL Server 支持高效的批量插入和更新操作：

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

# 使用 OUTPUT 子句
new_ids = User.bulk_insert(users, returning=['id'])
```

## 存储过程支持

rhosocial ActiveRecord 允许您调用 SQL Server 的存储过程：

```python
# 调用存储过程
result = User.connection.execute_procedure(
    'update_user_status',
    params={'@user_id': 1, '@status': 'active'}
)

# 调用返回结果集的存储过程
results = User.connection.execute_procedure(
    'get_users_by_status',
    params={'@status': 'active'},
    fetch_results=True
)
```

## JSON 支持

SQL Server 2016 及更高版本提供了 JSON 支持，rhosocial ActiveRecord 允许您使用这些功能：

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPk, Field

class Product(ActiveRecord):
    id = IntegerPk()
    name = Field(str)
    properties = Field(dict)  # 将存储为 JSON 字符串
    
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

SQL Server 提供全文搜索功能，rhosocial ActiveRecord 支持这一特性：

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPk, Field

class Article(ActiveRecord):
    id = IntegerPk()
    title = Field(str)
    content = Field(str)
    
    class Meta:
        table_name = 'articles'
        # 注意：需要在 SQL Server 中创建全文索引

# 使用全文搜索
articles = Article.find_all(
    Article.contains(['title', 'content'], 'python programming')
)
```

## 临时表

SQL Server 支持临时表，rhosocial ActiveRecord 允许您使用这一特性：

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPk, Field

# 本地临时表（仅在当前连接中可见）
class TempResult(ActiveRecord):
    id = IntegerPk()
    value = Field(float)
    
    class Meta:
        table_name = '#temp_results'  # 以 # 开头的表名表示本地临时表

# 全局临时表（对所有连接可见）
class GlobalTempResult(ActiveRecord):
    id = IntegerPk()
    value = Field(float)
    
    class Meta:
        table_name = '##global_temp_results'  # 以 ## 开头的表名表示全局临时表
```

## 性能优化

使用 SQL Server 后端时的一些性能优化建议：

1. **适当的索引**：为经常在 WHERE、JOIN 和 ORDER BY 子句中使用的列创建索引
2. **查询优化**：使用查询计划分析器分析查询性能
3. **分区表**：对大表使用表分区来提高查询性能
4. **索引视图**：对复杂查询使用索引视图
5. **参数化查询**：使用参数化查询而不是字符串拼接，以利用查询计划缓存
6. **连接池**：使用连接池减少连接创建的开销
7. **批量操作**：尽可能使用批量插入、更新和删除
8. **统计信息**：确保数据库统计信息是最新的

## 限制和注意事项

使用 SQL Server 后端时需要注意的一些限制：

1. **标识符长度**：表名、列名等标识符的最大长度为 128 个字符
2. **表大小**：单表最大可达 524,272 TB
3. **批量操作限制**：批量插入操作的最大行数受到内存和网络限制
4. **JSON 支持**：需要 SQL Server 2016 及更高版本才能使用 JSON 功能
5. **Unicode 支持**：建议使用 NVARCHAR 而不是 VARCHAR 以支持 Unicode 字符

## 版本兼容性

rhosocial ActiveRecord 的 SQL Server 后端支持以下版本：

- SQL Server 2012 及更高版本
- Azure SQL Database

较旧的版本可能也能工作，但某些功能可能不可用。
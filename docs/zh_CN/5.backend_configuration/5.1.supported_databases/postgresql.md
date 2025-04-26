# PostgreSQL 支持

rhosocial ActiveRecord 为 PostgreSQL 数据库系统提供了全面的支持。本文档涵盖了在使用 rhosocial ActiveRecord 与 PostgreSQL 时的特定功能、配置选项和注意事项。

## 概述

PostgreSQL 是一个功能强大的开源对象关系数据库系统，以其可靠性、功能稳健性和性能著称。rhosocial ActiveRecord 的 PostgreSQL 后端提供了一个一致的接口，同时充分利用 PostgreSQL 的高级功能。

## 功能

- 完整的 CRUD 操作支持
- 事务管理与 PostgreSQL 的隔离级别
- 支持 PostgreSQL 特定的数据类型和操作符
- 支持 JSON 和 JSONB 数据类型及其操作
- 支持数组类型
- 支持地理空间数据（PostGIS）
- 支持全文搜索功能
- 支持继承和分区表
- 支持自定义类型和域
- 支持物化视图

## 配置

要将 PostgreSQL 与 rhosocial ActiveRecord 一起使用，您需要使用 PostgreSQL 后端配置您的模型：

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend import ConnectionConfig
from rhosocial.activerecord.backend.impl.postgresql import PostgreSQLBackend

class User(ActiveRecord):
    pass

# 配置模型使用 PostgreSQL 后端
User.configure(
    ConnectionConfig(
        host='localhost',      # PostgreSQL 服务器主机
        port=5432,            # PostgreSQL 服务器端口
        database='my_db',     # 数据库名称
        user='username',      # 用户名
        password='password',  # 密码
        # 可选参数
        schema='public',      # 模式名称
        sslmode='require',    # SSL 模式
        connect_timeout=10,   # 连接超时（秒）
        pool_size=5,          # 连接池大小
        pool_recycle=3600     # 连接回收时间（秒）
    ),
    PostgreSQLBackend
)
```

## 数据类型映射

rhosocial ActiveRecord 将 Python 数据类型映射到 PostgreSQL 数据类型，以下是主要的映射关系：

| Python 类型 | PostgreSQL 类型 |
|------------|----------------|
| int        | INTEGER        |
| float      | DOUBLE PRECISION |
| str        | VARCHAR, TEXT  |
| bytes      | BYTEA          |
| bool       | BOOLEAN        |
| datetime   | TIMESTAMP      |
| date       | DATE           |
| time       | TIME           |
| Decimal    | NUMERIC        |
| uuid.UUID  | UUID           |
| dict, list | JSONB          |
| list       | ARRAY          |
| ipaddress.IPv4Address | INET |
| ipaddress.IPv6Address | INET |

## 模式（Schema）支持

PostgreSQL 支持模式（Schema）来组织数据库对象。rhosocial ActiveRecord 允许您指定模式：

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

PostgreSQL 提供了强大的事务支持，rhosocial ActiveRecord 提供了简单的事务管理接口：

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

PostgreSQL 支持的隔离级别包括：

- **READ UNCOMMITTED**：在 PostgreSQL 中等同于 READ COMMITTED
- **READ COMMITTED**：PostgreSQL 的默认级别，防止脏读，但允许不可重复读和幻读
- **REPEATABLE READ**：防止脏读和不可重复读，但允许幻读
- **SERIALIZABLE**：最高隔离级别，防止所有并发问题

## 锁定策略

rhosocial ActiveRecord 支持 PostgreSQL 的锁定功能，用于处理并发访问：

```python
# 悲观锁 - 使用 FOR UPDATE 锁定行
with User.transaction() as tx:
    user = User.find_by(id=1, lock='FOR UPDATE')
    user.balance -= 100
    user.save()

# 共享锁 - 使用 FOR SHARE
with User.transaction() as tx:
    user = User.find_by(id=1, lock='FOR SHARE')
    # 读取但不修改数据
    
# 跳过锁定的行 - 使用 SKIP LOCKED
with User.transaction() as tx:
    next_job = Job.find_by(status='pending', lock='FOR UPDATE SKIP LOCKED')
    if next_job:
        # 处理任务
        next_job.status = 'processing'
        next_job.save()
```

## JSON 和 JSONB 支持

PostgreSQL 提供了强大的 JSON 和 JSONB 支持，rhosocial ActiveRecord 允许您使用这些功能：

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPk, Field

class Product(ActiveRecord):
    id = IntegerPk()
    name = Field(str)
    properties = Field(dict, db_type='JSONB')  # 使用 JSONB 类型
    
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
    Product.properties.json_extract('color') == 'black'
)

# 使用 JSONB 包含操作符
products = Product.find_all(
    Product.properties.json_contains({'color': 'black'})
)

# 使用 JSONB 路径存在检查
products = Product.find_all(
    Product.properties.json_exists('dimensions.width')
)
```

## 数组支持

PostgreSQL 支持数组类型，rhosocial ActiveRecord 允许您使用这一特性：

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPk, Field

class Post(ActiveRecord):
    id = IntegerPk()
    title = Field(str)
    tags = Field(list, db_type='TEXT[]')  # 使用数组类型
    
# 使用数组数据
post = Post(
    title='PostgreSQL 技巧',
    tags=['database', 'postgresql', 'tips']
)
post.save()

# 使用数组查询
posts = Post.find_all(
    Post.tags.contains(['postgresql'])
)

# 使用数组重叠查询
posts = Post.find_all(
    Post.tags.overlaps(['database', 'mysql'])
)
```

## 全文搜索

PostgreSQL 提供强大的全文搜索功能，rhosocial ActiveRecord 支持这一特性：

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPk, Field

class Article(ActiveRecord):
    id = IntegerPk()
    title = Field(str)
    content = Field(str)
    search_vector = Field(None, db_type='TSVECTOR')  # 全文搜索向量
    
    class Meta:
        table_name = 'articles'
        indexes = [
            {'type': 'GIN', 'columns': ['search_vector']}
        ]

# 使用全文搜索
articles = Article.find_all(
    Article.search_vector.matches('python & programming')
)
```

## 地理空间数据支持

结合 PostGIS 扩展，PostgreSQL 提供了强大的地理空间数据支持：

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPk, Field

class Location(ActiveRecord):
    id = IntegerPk()
    name = Field(str)
    position = Field(None, db_type='GEOMETRY(Point, 4326)')  # 地理位置点
    
    class Meta:
        table_name = 'locations'
        indexes = [
            {'type': 'GIST', 'columns': ['position']}
        ]

# 查找附近的位置
locations = Location.find_all(
    Location.position.st_dwithin(
        'SRID=4326;POINT(-73.935242 40.730610)', 1000  # 1000米内
    )
)
```

## 批量操作

PostgreSQL 支持高效的批量插入和更新操作：

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

# 使用 RETURNING 子句
new_ids = User.bulk_insert(users, returning=['id'])
```

## 性能优化

使用 PostgreSQL 后端时的一些性能优化建议：

1. **适当的索引**：为经常在 WHERE、JOIN 和 ORDER BY 子句中使用的列创建索引
2. **使用 JSONB 而非 JSON**：JSONB 在查询性能上优于 JSON
3. **分区表**：对大表使用表分区来提高查询性能
4. **并行查询**：利用 PostgreSQL 的并行查询功能
5. **物化视图**：对复杂查询使用物化视图
6. **适当的 VACUUM 和 ANALYZE**：定期维护数据库以保持性能
7. **连接池**：使用连接池减少连接创建的开销

## 限制和注意事项

使用 PostgreSQL 后端时需要注意的一些限制：

1. **标识符长度**：表名、列名等标识符的最大长度为 63 个字符
2. **大对象限制**：大对象（BLOB/CLOB）的最大大小为 4TB
3. **行大小限制**：单行数据的最大大小约为 1GB
4. **表大小**：单表最大可达 32TB

## 版本兼容性

rhosocial ActiveRecord 的 PostgreSQL 后端支持以下版本：

- PostgreSQL 10 及更高版本

较旧的版本可能也能工作，但某些功能可能不可用。
# Oracle 支持

rhosocial ActiveRecord 为 Oracle 数据库系统提供了全面的支持。本文档涵盖了在使用 rhosocial ActiveRecord 与 Oracle 时的特定功能、配置选项和注意事项。

## 概述

Oracle 数据库是一个企业级关系型数据库管理系统，以其可靠性、可扩展性和全面的功能集而闻名。rhosocial ActiveRecord 的 Oracle 后端提供了一个一致的接口，同时尊重 Oracle 的独特特性和企业级功能。

## 功能

- 完整的 CRUD 操作支持
- 事务管理与 Oracle 的隔离级别
- 支持 Oracle 特定的数据类型和函数
- 支持 PL/SQL 存储过程和函数调用
- 支持 Oracle 的 JSON 功能（Oracle 12c 及更高版本）
- 支持 Oracle 的空间数据类型
- 支持 Oracle 的 CLOB 和 BLOB 类型
- 支持 Oracle 的序列和触发器
- 支持 Oracle RAC（Real Application Clusters）

## 配置

要将 Oracle 与 rhosocial ActiveRecord 一起使用，您需要使用 Oracle 后端配置您的模型：

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend import ConnectionConfig
from rhosocial.activerecord.backend.impl.oracle import OracleBackend

class User(ActiveRecord):
    pass

# 配置模型使用 Oracle 后端
User.configure(
    ConnectionConfig(
        host='localhost',      # Oracle 服务器主机
        port=1521,            # Oracle 监听器端口
        service_name='ORCL',  # 服务名
        # 或者使用 SID
        # sid='ORCL',         # SID
        user='username',      # 用户名
        password='password',  # 密码
        # 可选参数
        encoding='UTF-8',     # 字符编码
        mode=None,            # 连接模式（SYSDBA, SYSOPER 等）
        purity='NEW',         # 连接纯度（NEW, SELF, DEFAULT）
        events=False,         # 是否接收 Oracle 事件
        pool_min=1,           # 连接池最小连接数
        pool_max=5,           # 连接池最大连接数
        pool_increment=1,     # 连接池增量
        pool_timeout=60       # 连接池超时（秒）
    ),
    OracleBackend
)

# 使用 TNS 名称连接
User.configure(
    ConnectionConfig(
        dsn='my_tns_name',    # TNS 名称
        user='username',      # 用户名
        password='password'   # 密码
    ),
    OracleBackend
)
```

## 数据类型映射

rhosocial ActiveRecord 将 Python 数据类型映射到 Oracle 数据类型，以下是主要的映射关系：

| Python 类型 | Oracle 类型 |
|------------|-------------|
| int        | NUMBER      |
| float      | NUMBER      |
| str        | VARCHAR2, CLOB |
| bytes      | BLOB        |
| bool       | NUMBER(1)   |
| datetime   | TIMESTAMP   |
| date       | DATE        |
| time       | TIMESTAMP   |
| Decimal    | NUMBER      |
| uuid.UUID  | RAW(16)     |
| dict, list | CLOB (JSON) |

## 模式（Schema）支持

Oracle 使用模式（Schema）来组织数据库对象。在 Oracle 中，模式通常与用户名相同。rhosocial ActiveRecord 允许您指定模式：

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPk

class Product(ActiveRecord):
    id = IntegerPk()
    
    class Meta:
        table_name = 'products'
        schema = 'INVENTORY'  # 指定模式
```

## 序列和自增主键

Oracle 使用序列（Sequence）来实现自增主键。rhosocial ActiveRecord 自动处理序列的创建和使用：

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPk, Field

class Product(ActiveRecord):
    id = IntegerPk()  # 自动使用序列
    name = Field(str)
    
    class Meta:
        table_name = 'products'
        sequence_name = 'PRODUCT_SEQ'  # 自定义序列名称
```

## 事务支持

Oracle 提供了强大的事务支持，rhosocial ActiveRecord 提供了简单的事务管理接口：

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

Oracle 支持的隔离级别包括：

- **READ COMMITTED**：Oracle 的默认级别，防止脏读，但允许不可重复读和幻读
- **SERIALIZABLE**：防止脏读、不可重复读和幻读
- **READ ONLY**：事务只能读取数据，不能修改数据

## 锁定策略

rhosocial ActiveRecord 支持 Oracle 的锁定功能，用于处理并发访问：

```python
# 悲观锁 - 使用 FOR UPDATE 锁定行
with User.transaction() as tx:
    user = User.find_by(id=1, lock='FOR UPDATE')
    user.balance -= 100
    user.save()

# 带等待时间的锁 - 使用 WAIT
with User.transaction() as tx:
    user = User.find_by(id=1, lock='FOR UPDATE WAIT 5')
    # 等待最多 5 秒获取锁
    
# 不等待锁 - 使用 NOWAIT
with User.transaction() as tx:
    try:
        user = User.find_by(id=1, lock='FOR UPDATE NOWAIT')
        # 如果行被锁定，立即抛出异常
    except Exception as e:
        # 处理锁定异常
```

## 批量操作

Oracle 支持高效的批量插入和更新操作：

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

## PL/SQL 支持

rhosocial ActiveRecord 允许您调用 Oracle 的 PL/SQL 存储过程和函数：

```python
# 调用存储过程
result = User.connection.execute_procedure(
    'update_user_status',
    params={'p_user_id': 1, 'p_status': 'active'}
)

# 调用函数
balance = User.connection.execute_function(
    'get_user_balance',
    params={'p_user_id': 1},
    return_type=float
)
```

## JSON 支持

Oracle 12c 及更高版本提供了 JSON 支持，rhosocial ActiveRecord 允许您使用这些功能：

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

## 性能优化

使用 Oracle 后端时的一些性能优化建议：

1. **适当的索引**：为经常在 WHERE、JOIN 和 ORDER BY 子句中使用的列创建索引
2. **分区表**：对大表使用表分区来提高查询性能
3. **物化视图**：对复杂查询使用物化视图
4. **绑定变量**：使用参数化查询而不是字符串拼接，以利用 Oracle 的绑定变量优化
5. **连接池**：使用连接池减少连接创建的开销
6. **批量操作**：尽可能使用批量插入、更新和删除
7. **并行执行**：利用 Oracle 的并行执行功能
8. **统计信息**：确保数据库统计信息是最新的

## Oracle RAC 支持

rhosocial ActiveRecord 支持 Oracle RAC（Real Application Clusters）配置：

```python
User.configure(
    ConnectionConfig(
        dsn='(DESCRIPTION=(ADDRESS_LIST=(ADDRESS=(PROTOCOL=TCP)(HOST=node1)(PORT=1521))(ADDRESS=(PROTOCOL=TCP)(HOST=node2)(PORT=1521)))(CONNECT_DATA=(SERVICE_NAME=service_name)))',
        user='username',
        password='password'
    ),
    OracleBackend
)
```

## 限制和注意事项

使用 Oracle 后端时需要注意的一些限制：

1. **标识符长度**：表名、列名等标识符的最大长度为 30 个字符（Oracle 12c 之前）或 128 个字符（Oracle 12c 及更高版本）
2. **日期处理**：Oracle 的日期处理与其他数据库有所不同
3. **NULL 排序**：Oracle 默认将 NULL 值排在最后（升序）或最前（降序）
4. **ROWID**：Oracle 使用 ROWID 作为物理行标识符
5. **LONG 和 LONG RAW**：这些旧类型有很多限制，建议使用 CLOB 和 BLOB 代替

## 版本兼容性

rhosocial ActiveRecord 的 Oracle 后端支持以下版本：

- Oracle Database 11g Release 2 及更高版本

较旧的版本可能也能工作，但某些功能可能不可用。
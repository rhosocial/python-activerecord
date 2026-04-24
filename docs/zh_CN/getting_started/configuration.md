# 数据库配置 (Database Configuration)

在定义 ActiveRecord 模型之后，你还不能立即访问数据库后端执行操作。`rhosocial-activerecord` 需要显式配置后端才能执行数据库操作。配置后端后，你就可以访问对应数据库并执行查询操作。特别地，如果你只想查看查询对应的SQL结果而不关心具体后端，可以使用 dummy 后端。

> 💡 **AI提示词示例**: "我定义了ActiveRecord模型，但是调用save()时报错说没有配置后端，怎么办？"

## SQLite 配置

目前，SQLite 是主要支持的生产级后端。配置 SQLite 后端后，你就可以执行真实的数据库操作。

```python
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig

# 1. 创建配置对象
config = SQLiteConnectionConfig(
    database='my_database.db',  # 或者 ':memory:' 使用内存数据库
    timeout=5.0
)

# 2. 配置 ActiveRecord 基类或特定模型
# 这将为所有继承自 ActiveRecord 的模型设置默认后端
ActiveRecord.configure(config, SQLiteBackend)

# 3. 配置完成后，你可以执行数据库操作
user = User(name="张三", email="zhangsan@example.com")
user.save()  # 这将真正保存到 SQLite 数据库

# 4. 你也可以查看生成的 SQL 语句
sql, params = User.query().where(User.c.name == "张三").to_sql()
print(f"SQL: {sql}")
print(f"参数: {params}")
```

> 💡 **AI提示词示例**: "我想知道这个查询会生成什么样的SQL语句，但不想真的执行它，有什么办法吗？"

### SQLite 特殊默认值

如果不指定 `database` 参数，SQLite 会使用内存数据库 (`:memory:`)：

```python
config = SQLiteConnectionConfig()  #database 默认为 ':memory:'
```

这对于测试和临时操作非常有用。

### 环境变量配置

SQLite 支持从环境变量读取配置，这在 Kubernetes 管理的容器中特别有用：

```bash
export SQLITE_DATABASE=/data/app.db
export SQLITE_TIMEOUT=30
export SQLITE_URI=false
export SQLITE_PRAGMA_FOREIGN_KEYS=ON
export SQLITE_PRAGMA_JOURNAL_MODE=WAL
```

```python
# 通过环境变量创建配置
config = SQLiteConnectionConfig.from_env()
```

支持的 SQLite 环境变量前缀为 `SQLITE_`，特殊变量包括：
- `SQLITE_DATABASE` - 数据库文件路径
- `SQLITE_TIMEOUT` - 连接超时时间
- `SQLITE_URI` - 是否使用 URI
- `SQLITE_DETECT_TYPES` - 类型检测掩码
- `SQLITE_DELETE_ON_CLOSE` - 关闭时删除文件
- `SQLITE_CACHED_STATEMENTS` - 语句缓存数量
- `SQLITE_AUTOCOMMIT` - 自动提交模式
- `SQLITE_PRAGMA_*` - PRAGMA 设置（如 `SQLITE_PRAGMA_JOURNAL_MODE=WAL`）

## 共享后端实例 (Shared Backend Instance)

在实际应用中，你希望所有模型共享同一个数据库连接池。如果你配置了基类或第一个模型，框架会自动处理这一点。

如果你有多个数据库，可以单独配置模型：

```python
# 配置 User 模型使用 DB1
User.configure(config1, SQLiteBackend)

# 配置 Post 模型与 User 共享后端 (推荐)
# 这确保它们使用相同的连接和事务上下文
Post.__backend__ = User.__backend__
Post.__connection_config__ = User.__connection_config__
Post.__backend_class__ = User.__backend_class__
```

## Dummy 后端配置

如果你只想查看查询生成的 SQL 语句而不执行实际的数据库操作，可以使用 Dummy 后端。这对于调试和测试非常有用。

```python
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.impl.dummy import DummyBackend
from rhosocial.activerecord.backend.config import ConnectionConfig

# 1. 创建配置对象
config = ConnectionConfig()

# 2. 配置使用 Dummy 后端
ActiveRecord.configure(config, DummyBackend)

# 3. 现在你可以生成 SQL 但不能执行数据库操作
# 这行代码可以正常工作，生成 SQL 语句
sql, params = User.query().where(User.c.name == "张三").to_sql()
print(f"SQL: {sql}")
print(f"参数: {params}")

# 但这行代码会抛出异常，因为 Dummy 后端不支持真实数据库操作
# user.save()  # 这会引发 NotImplementedError
```

> 💡 **AI提示词示例**: "我想在不连接数据库的情况下测试我的查询逻辑是否正确，应该怎么做？"

## 命名连接 (Named Connection)

命名连接是一种将数据库连接配置外部化的方式，允许你将配置定义在独立的 Python 模块中，享受完整的 IDE 支持和版本控制。

### 定义命名连接

命名连接是一个可调用对象(函数或带有 `__call__` 方法的类),必须满足以下条件:

1. 接受任意命名参数(可选)
2. 返回值必须是 `ConnectionConfig` 子类对象

```python
# myapp/connections/__init__.py

# 函数形式
def production_db(pool_size: int = 10):
    """获取生产环境数据库配置。"""
    return MySQLConnectionConfig(
        host="prod.example.com",
        database="myapp",
        user="app_user",
        password="secret",  # 敏感字段会被自动过滤
        pool_size=pool_size
    )

def development_db(database: str = "dev.db"):
    """获取开发环境数据库配置。"""
    return SQLiteConnectionConfig(database=database)

# 类形式(如果需要维护状态)
class ConnectionFactory:
    def __call__(self, environment: str = "development"):
        """根据环境获取数据库配置。"""
        if environment == "production":
            return MySQLConnectionConfig(host="prod.example.com", database="myapp")
        return SQLiteConnectionConfig(database=f"{environment}.db")
```

### 使用命名连接

```python
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.named_connection import resolve_named_connection

# 方式1: 使用便捷函数
config = resolve_named_connection("myapp.connections.production_db", {"pool_size": 20})
ActiveRecord.configure(config, SQLiteBackend)

# 方式2: 使用解析器(更多控制)
from rhosocial.activerecord.backend.named_connection import NamedConnectionResolver

resolver = NamedConnectionResolver("myapp.connections.production_db").load()
config = resolver.resolve({"pool_size": 20})
ActiveRecord.configure(config, SQLiteBackend)

# 查看配置描述(敏感字段会被过滤)
print(resolver.describe())
# 输出类似: {'pool_size': 20, 'database': 'my_database.db', ...}
```

### 列出可用连接

```python
from rhosocial.activerecord.backend.named_connection import list_named_connections_in_module

# 列出模块中所有命名连接
connections = list_named_connections_in_module("myapp.connections")
print(connections)
# 输出: [{'name': 'production_db', 'doc': '获取生产环境数据库配置。'}, ...]
```

### 重要说明

- 命名连接是后端特性,独立于 ActiveRecord 模型
- 敏感字段(密码、密钥等)在 `describe()` 输出中会被自动过滤
- 配置文件可以与代码一起进行版本控制
- 支持动态参数,便于在不同环境间切换

## 异步配置 (预览)

虽然核心逻辑已就绪支持异步，但当前的驱动程序是同步的。异步驱动支持 (如 `aiosqlite`) 计划在未来版本中发布。

如果你需要异步支持，可以使用 AsyncDummyBackend 来测试异步查询的 SQL 生成：

```python
from rhosocial.activerecord.model import AsyncActiveRecord
from rhosocial.activerecord.backend.impl.dummy import AsyncDummyBackend
from rhosocial.activerecord.backend.config import ConnectionConfig

# 配置异步 Dummy 后端
config = ConnectionConfig()
AsyncActiveRecord.configure(config, AsyncDummyBackend)

# 生成异步查询的 SQL
sql, params = await User.query().where(User.c.name == "张三").to_sql()
print(f"异步 SQL: {sql}")
```

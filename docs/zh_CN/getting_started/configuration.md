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

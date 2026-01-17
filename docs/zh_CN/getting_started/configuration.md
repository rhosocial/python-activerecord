# 数据库配置 (Database Configuration)

在定义模型之前，你需要配置数据库连接。`rhosocial-activerecord` 使用灵活的后端系统。

## SQLite 配置

目前，SQLite 是主要支持的生产级后端。

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
```

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

## 异步配置 (预览)

虽然核心逻辑已就绪支持异步，但当前的驱动程序是同步的。异步驱动支持 (如 `aiosqlite`) 计划在未来版本中发布。

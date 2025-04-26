# 基本配置

本指南介绍如何为您的第一个项目配置rhosocial ActiveRecord与SQLite。

## 设置SQLite连接

rhosocial ActiveRecord使用连接配置对象来建立数据库连接。对于SQLite，这非常简单，因为它只需要一个文件路径。

### 基本SQLite配置

```python
from rhosocial.activerecord.backend.typing import ConnectionConfig
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord import ActiveRecord

# 配置基于文件的SQLite数据库
config = ConnectionConfig(database='database.sqlite3')

# 配置ActiveRecord使用此连接
ActiveRecord.configure(config, backend_class=SQLiteBackend)
```

此配置将：
1. 在当前目录中创建一个名为`database.sqlite3`的SQLite数据库文件（如果不存在）
2. 配置所有ActiveRecord模型默认使用此连接

### 内存SQLite数据库

对于测试或临时数据，您可以使用内存SQLite数据库：

```python
# 内存数据库配置
config = ConnectionConfig(database=':memory:')
ActiveRecord.configure(config, backend_class=SQLiteBackend)
```

> **注意**：内存数据库仅在连接期间存在，连接关闭时会被删除。

## 配置选项

`ConnectionConfig`类接受多个参数来自定义您的连接：

```python
config = ConnectionConfig(
    database='database.sqlite3',  # 数据库文件路径
    pragmas={                     # SQLite特定的编译指示
        'journal_mode': 'WAL',    # 预写式日志，提高并发性
        'foreign_keys': 'ON',     # 启用外键约束
    },
    timeout=30.0,                # 连接超时（秒）
    isolation_level=None,        # 使用SQLite的自动提交模式
)
```

### 常用SQLite编译指示（Pragmas）

SQLite编译指示是控制SQLite库操作的配置选项。一些有用的编译指示包括：

- `journal_mode`：控制日志文件的管理方式（`DELETE`、`TRUNCATE`、`PERSIST`、`MEMORY`、`WAL`、`OFF`）
- `foreign_keys`：启用或禁用外键约束执行（`ON`、`OFF`）
- `synchronous`：控制SQLite写入磁盘的积极程度（`OFF`、`NORMAL`、`FULL`、`EXTRA`）
- `cache_size`：设置内存缓存中使用的页面数量

## 全局配置与模型特定配置

您可以配置所有ActiveRecord模型使用相同的连接，或者为特定模型配置不同的连接。

### 全局配置

```python
# 配置所有模型默认使用此连接
ActiveRecord.configure(config, backend_class=SQLiteBackend)
```

### 模型特定配置

```python
class User(ActiveRecord):
    __table_name__ = 'users'
    id: int
    name: str
    email: str

# 仅配置User模型使用此连接
User.configure(config, backend_class=SQLiteBackend)
```

## 下一步

现在您已经配置了数据库连接，请继续阅读[第一个模型示例](first_model_example.md)以了解如何创建和使用您的第一个ActiveRecord模型。
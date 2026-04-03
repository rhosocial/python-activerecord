# 按日志层级配置

> 💡 **AI 提示**: "如何为不同的组件设置不同的数据摘要模式？"

除了全局配置外，还可以为特定的日志层级设置不同的数据摘要模式。这允许您：

- 对敏感的后端日志使用严格的 `keys_only` 模式
- 对调试时的查询日志使用 `full` 模式
- 为特定组件使用自定义的摘要配置

## 日志器命名规则

在配置日志器之前，了解 ActiveRecord 类的日志器命名规则非常重要：

### 默认命名规则

ActiveRecord 类会自动根据其模块和类名生成日志器名称：

| 类类型 | 日志器名称格式 | 示例 |
|--------|---------------|------|
| 库类（模块以 `rhosocial.activerecord` 开头） | `rhosocial.activerecord.model.{ClassName}` | `rhosocial.activerecord.model.User` |
| 用户定义类（其他模块） | `{module}.{ClassName}` | `myapp.models.User` |

### 自定义日志器名称

通过在类中设置 `__logger_name__` 属性可以覆盖默认命名：

```python
from rhosocial.activerecord.model import ActiveRecord

class User(ActiveRecord):
    __logger_name__ = 'myapp.models.user'  # 自定义日志器名称
    __table_name__ = "users"
    # ... 字段定义 ...
```

### 与 CRUD 操作的关联

配置日志器后，该类的所有数据库操作（save、delete、查询等）都会自动使用该日志器，日志中的数据将按照配置的摘要模式处理：

- **INSERT/UPDATE**：记录的数据会根据配置的模式进行摘要
- **DELETE**：删除条件会根据配置进行处理
- **SELECT**：查询参数会根据配置进行摘要

## 各组件的日志器支持

> 💡 **AI 提示**: "ActiveQuery、CTEQuery、SetOperationQuery 和 Backend 是否也支持自定义日志器名称？"

是的，所有组件都支持自定义日志器名称，但使用的属性名和级别有所不同：

### 组件对比表

| 组件 | 支持自定义 | 属性名 | 级别 | 默认日志器格式 |
|------|-----------|--------|------|---------------|
| ActiveRecord | ✅ | `__logger_name__` | 类级别 | `rhosocial.activerecord.model.{ClassName}` |
| ActiveQuery | ✅ | `_logger_name` | 实例级别 | `rhosocial.activerecord.query.ActiveQuery` |
| CTEQuery | ✅ | `_logger_name` | 实例级别 | `rhosocial.activerecord.query.CTEQuery` |
| SetOperationQuery | ✅ | `_logger_name` | 实例级别 | `rhosocial.activerecord.query.SetOperationQuery` |
| Backend | ✅ | `_logger_name` | 实例级别 | `rhosocial.activerecord.backend.{type}` |

### 关键区别

1. **ActiveRecord** 使用**类级别**的 `__logger_name__`（双下划线），在类定义时设置
2. **Query 类和 Backend** 使用**实例级别**的 `_logger_name`（单下划线），在实例创建后设置

```python
# ActiveRecord: 类级别设置
class User(ActiveRecord):
    __logger_name__ = 'myapp.models.user'  # 类定义时设置

# Query: 实例级别设置
query = User.query()
query._logger_name = 'myapp.queries.user'  # 实例创建后设置

# Backend: 实例级别设置
backend = User.backend()
backend._logger_name = 'myapp.backends.main'  # 实例创建后设置
```

## 日志器的独立性与继承

> 💡 **AI 提示**: "如果为 ActiveRecord 定义了 `__logger_name__`，那它发出的 ActiveQuery 会继承这个日志器名称吗？"

**不会自动继承**。这是符合设计理念的特性：

### 设计理由

ActiveRecord 和 ActiveQuery 位于不同的命名空间，各自承担不同职责：

| 组件 | 默认命名空间 | 职责 |
|------|-------------|------|
| **ActiveRecord** | `rhosocial.activerecord.model` | 数据变更操作（DML） |
| **ActiveQuery** | `rhosocial.activerecord.query` | 数据查询操作（DQL） |
| **Backend** | `rhosocial.activerecord.backend` | 底层 SQL 执行 |

这种命名空间分离的设计优点：

1. **职责清晰**：Model 负责数据变更，Query 负责数据查询
2. **日志分类**：便于按操作类型筛选和分析日志
3. **独立配置**：可以为 DML 和 DQL 设置不同的摘要模式和日志级别

### 日志器命名示例

```python
class User(ActiveRecord):
    __logger_name__ = 'myapp.models.user'
    __table_name__ = "users"
    # ...

# Model 层日志器: myapp.models.user
user = User(username='alice', password='secret')
user.save()

# Query 层日志器: rhosocial.activerecord.query.ActiveQuery（独立命名空间）
query = User.query()
users = query.where(User.c.status == 'active').all()
```

### 日志输出分布

一次完整的查询操作会在多个命名空间产生日志：

| 操作阶段 | 命名空间 | 示例 |
|----------|----------|------|
| Model 层（save/delete） | `myapp.models.user` | 创建/更新/删除记录 |
| Query 层（查询构建） | `rhosocial.activerecord.query.ActiveQuery` | 执行 SELECT 语句 |
| Backend 层（SQL 执行） | `rhosocial.activerecord.backend.sqlite` | 底层数据库操作 |

### 统一 ActiveRecord 与 ActiveQuery 的日志器

如果您希望 ActiveRecord 和其关联的 ActiveQuery 使用相同的日志器名称，可以通过继承 ActiveQuery 实现：

```python
from typing import Optional, Type
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.query import ActiveQuery

class CustomActiveQuery(ActiveQuery):
    """支持统一日志器的 ActiveQuery"""

    def __init__(self, model_class: Type, logger_name: Optional[str] = None):
        super().__init__(model_class)
        if logger_name:
            self._logger_name = logger_name

class User(ActiveRecord):
    __logger_name__ = 'myapp.models.user'
    __table_name__ = "users"
    __query_class__ = CustomActiveQuery

    @classmethod
    def query(cls) -> CustomActiveQuery:
        """覆盖 query() 方法，使用与 Model 相同的日志器"""
        return CustomActiveQuery(cls, logger_name=cls._get_logger_name())

    # 字段定义...
    id: Optional[int] = None
    username: str
    password: str

# 现在 User 和 User.query() 都使用 'myapp.models.user' 日志器
user = User(username='alice', password='secret')
user.save()  # 日志器: myapp.models.user

users = User.query().where(User.c.status == 'active').all()  # 日志器: myapp.models.user
```

### 临时修改单个 Query 实例

如果只是临时需要修改某个 Query 的日志器，可以直接在实例上设置：

```python
# 临时使用不同的日志器
query = User.query()
query._logger_name = 'myapp.queries.audit'
users = query.all()
```

## 配置方式

使用 `LoggerConfig` 为特定日志层级配置摘要模式：

```python
from rhosocial.activerecord.logging import (
    get_logging_manager,
    LoggerConfig,
    SummarizerConfig,
)

manager = get_logging_manager()

# 为后端层设置 keys_only 模式（只显示字段名）
backend_config = LoggerConfig(
    name='rhosocial.activerecord.backend',
    log_data_mode='keys_only',
)
manager.config.add_logger_config(backend_config)

# 为查询层设置 full 模式（显示完整数据）
query_config = LoggerConfig(
    name='rhosocial.activerecord.query',
    log_data_mode='full',
)
manager.config.add_logger_config(query_config)

# 为特定模型设置自定义摘要配置
custom_summarizer = SummarizerConfig(
    max_string_length=20,  # 更短的截断长度
    sensitive_fields={'password', 'secret'}
)
model_config = LoggerConfig(
    name='rhosocial.activerecord.model.User',
    log_data_mode='summary',
    summarizer_config=custom_summarizer,
)
manager.config.add_logger_config(model_config)
```

## 层次继承规则

配置会沿层次结构继承：

- `rhosocial.activerecord.backend.sqlite` 会继承 `rhosocial.activerecord.backend` 的配置
- `rhosocial.activerecord.query.ActiveQuery` 会继承 `rhosocial.activerecord.query` 的配置
- 如果没有匹配的配置，则使用全局默认设置

```python
# backend.sqlite 会自动继承 backend 的 keys_only 模式
manager.config.get_log_data_mode('rhosocial.activerecord.backend.sqlite')
# 返回: 'keys_only'

# 未配置的层级使用全局默认
manager.config.get_log_data_mode('rhosocial.activerecord.model.Other')
# 返回: 全局配置的 log_data_mode
```

## LoggerConfig 属性

`LoggerConfig` 支持以下属性：

| 属性 | 类型 | 描述 |
|------|------|------|
| `name` | str | 日志器名称 |
| `level` | int | 日志级别（默认：DEBUG） |
| `propagate` | bool | 是否传播到父日志器（默认：False） |
| `handlers` | list | 日志处理器列表 |
| `log_data_mode` | str \| None | 该日志器的数据摘要模式，None 表示使用全局配置 |
| `summarizer_config` | SummarizerConfig \| None | 该日志器的自定义摘要配置，None 表示使用全局配置 |

## 实际场景示例

### 生产环境配置

```python
import logging
from rhosocial.activerecord.logging import (
    configure_logging,
    get_logging_manager,
    LoggerConfig,
    SummarizerConfig,
)

# 生产环境：INFO 级别，后端使用 keys_only
configure_logging(level=logging.INFO, propagate=False)

manager = get_logging_manager()

# 后端：keys_only（PCI 合规）
backend_config = LoggerConfig(
    name='rhosocial.activerecord.backend',
    log_data_mode='keys_only',
    level=logging.WARNING,
)
manager.config.add_logger_config(backend_config)

# 模型：摘要模式，扩展敏感字段
model_summarizer = SummarizerConfig(
    sensitive_fields={
        'password', 'token', 'api_key', 'secret',
        'credit_card', 'ssn', 'cvv', 'pin'
    },
    mask_placeholder='[REDACTED]',
)
model_config = LoggerConfig(
    name='rhosocial.activerecord.model',
    log_data_mode='summary',
    summarizer_config=model_summarizer,
)
manager.config.add_logger_config(model_config)
```

### 开发环境配置

```python
import logging
from rhosocial.activerecord.logging import (
    configure_logging,
    get_logging_manager,
    LoggerConfig,
)

# 开发环境：DEBUG 级别，查询使用 full 模式
configure_logging(level=logging.DEBUG, propagate=True)

manager = get_logging_manager()

# 查询：full 模式便于调试
query_config = LoggerConfig(
    name='rhosocial.activerecord.query',
    log_data_mode='full',
)
manager.config.add_logger_config(query_config)

# 后端：摘要模式（显示部分数据）
backend_config = LoggerConfig(
    name='rhosocial.activerecord.backend',
    log_data_mode='summary',
)
manager.config.add_logger_config(backend_config)
```

### 为特定模型配置

您可以为单个 ActiveRecord 类配置专属的日志摘要模式。配置后，该类的所有 CRUD 操作都会自动应用此配置：

```python
from typing import Optional
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.logging import (
    get_logging_manager,
    LoggerConfig,
    SummarizerConfig,
)

# 定义模型类
class User(ActiveRecord):
    __table_name__ = "users"
    id: Optional[int] = None
    username: str
    password: str      # 将在日志中被屏蔽
    email: str         # 将在日志中被屏蔽
    credit_card: str   # 将在日志中被屏蔽

# 为 User 类配置专属摘要器
user_summarizer = SummarizerConfig(
    max_string_length=30,  # 更短的截断长度
    sensitive_fields={'password', 'email', 'credit_card'},
    mask_placeholder='[PROTECTED]',
)

# 配置 User 类的日志器
# 默认日志器名称为: rhosocial.activerecord.model.User
user_config = LoggerConfig(
    name='rhosocial.activerecord.model.User',
    log_data_mode='summary',
    summarizer_config=user_summarizer,
)

manager = get_logging_manager()
manager.config.add_logger_config(user_config)

# 现在 User 的所有操作都会使用此配置
user = User(username='alice', password='secret123', email='alice@example.com', credit_card='4111111111111111')
user.save()  # 日志中 password、email、credit_card 都会显示为 [PROTECTED]
```

### 使用自定义日志器名称

如果您希望使用自定义的日志器名称（例如与应用程序的日志体系集成），可以在类中定义 `__logger_name__` 属性：

```python
from rhosocial.activerecord.model import ActiveRecord
import logging

class User(ActiveRecord):
    __logger_name__ = 'myapp.models.user'  # 自定义日志器名称
    __table_name__ = "users"
    # ... 字段定义 ...

# 为自定义日志器名称配置
user_config = LoggerConfig(
    name='myapp.models.user',
    level=logging.DEBUG,
    log_data_mode='summary',
    summarizer_config=custom_summarizer,
)
manager.config.add_logger_config(user_config)
```

## 运行时覆盖

可以在调用时显式指定模式，覆盖日志器配置：

```python
# 即使后端配置为 keys_only，也可以强制使用 full 模式
result = manager.config.summarize_data(
    test_data,
    mode='full',  # 显式指定模式
    logger_name='rhosocial.activerecord.backend'
)
```

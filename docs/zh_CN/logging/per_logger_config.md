# 按日志层级配置

> 💡 **AI 提示**: "如何为不同的组件设置不同的数据摘要模式？"

除了全局配置外，还可以为特定的日志层级设置不同的数据摘要模式。这允许您：

- 对敏感的后端日志使用严格的 `keys_only` 模式
- 对调试时的查询日志使用 `full` 模式
- 为特定组件使用自定义的摘要配置

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

### 自定义模型日志器

用户自定义的 Model 类可以拥有自己的日志器：

```python
from rhosocial.activerecord.model import ActiveRecord

class User(ActiveRecord):
    __logger_name__ = 'myapp.models.user'  # 自定义日志器名称
    # ...

# 配置自定义日志器
user_config = LoggerConfig(
    name='myapp.models.user',
    level=logging.DEBUG,
    log_data_mode='summary',
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

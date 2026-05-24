# 按日志层级配置

`LoggerConfig` 是某个 `LoggingConfig` 对象内部的 per-logger 规则。ActiveRecord 模型配置和 backend 配置默认独立，除非显式把同一个 `LoggingConfig` 对象传给二者。

## 日志器名称

| 组件 | 默认日志器示例 | 配置归属 |
| ---- | -------------- | -------- |
| ActiveRecord 模型 | `rhosocial.activerecord.model.User` | `ActiveRecord.__logging_config__` 或 `Model.__logging_config__` |
| Query | `rhosocial.activerecord.query.ActiveQuery` | backend `LoggingConfig` |
| Backend | `rhosocial.activerecord.backend.sqlite` | backend `LoggingConfig` |
| Transaction | `rhosocial.activerecord.transaction` | backend `LoggingConfig` |
| Framework worker | `rhosocial.activerecord.worker` | `configure_logging()` 控制的框架默认配置 |

模型可以覆盖输出目标日志器名称：

```python
from rhosocial.activerecord.model import ActiveRecord

class User(ActiveRecord):
    __logger_name__ = "myapp.models.user"
    __table_name__ = "users"
```

`__logger_name__` 只改变日志输出目标；data payload 的展示规则仍来自该模型所属的 `LoggingConfig`。

## 模型 per-logger 规则

```python
from rhosocial.activerecord.logging import LoggerConfig, LoggingConfig, LogDataMode, SummarizerConfig
from rhosocial.activerecord.model import ActiveRecord

model_config = LoggingConfig(log_data_mode=LogDataMode.SUMMARY)
model_config.add_logger_config(
    LoggerConfig(
        name="rhosocial.activerecord.model.User",
        log_data_mode=LogDataMode.KEYS_ONLY,
        summarizer_config=SummarizerConfig(sensitive_fields={"password", "email"}),
    )
)

ActiveRecord.__logging_config__ = model_config
```

具体模型可以拥有独立配置：

```python
class AuditUser(ActiveRecord):
    __table_name__ = "audit_users"
    __logging_config__ = LoggingConfig(log_data_mode=LogDataMode.HIDDEN)
```

## Backend per-logger 规则

backend、query、transaction 日志不由 `ActiveRecord.__logging_config__` 控制：

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
from rhosocial.activerecord.logging import LoggerConfig, LoggingConfig, LogDataMode

backend_config = LoggingConfig(log_data_mode=LogDataMode.KEYS_ONLY)
backend_config.add_logger_config(
    LoggerConfig(
        name="rhosocial.activerecord.query",
        log_data_mode=LogDataMode.FULL,
    )
)

User.configure(SQLiteConnectionConfig(database=":memory:"), SQLiteBackend, logging_config=backend_config)
```

## BackendGroup

```python
from rhosocial.activerecord.connection.group import BackendGroup

backend_config = LoggingConfig(log_data_mode=LogDataMode.KEYS_ONLY)

group = BackendGroup(
    name="main",
    models=[User, Order],
    config=SQLiteConnectionConfig(database=":memory:"),
    backend_class=SQLiteBackend,
    logging_config=backend_config,
)
group.configure()
```

## 层级匹配

per-logger 规则只在同一个 `LoggingConfig` 对象内部按 logger namespace 层级匹配：

```python
backend_config.add_logger_config(
    LoggerConfig(name="rhosocial.activerecord.backend", log_data_mode=LogDataMode.KEYS_ONLY)
)

backend_config.get_log_data_mode("rhosocial.activerecord.backend.sqlite")
# LogDataMode.KEYS_ONLY
```

`backend_config` 中的规则不会影响 `model_config`；`model_config` 中的规则也不会影响 backend/query/transaction 日志。

## 生产配置示例

```python
import logging
from rhosocial.activerecord.logging import LoggerConfig, LoggingConfig, LogDataMode, SummarizerConfig

model_config = LoggingConfig(
    default_level=logging.INFO,
    log_data_mode=LogDataMode.SUMMARY,
    summarizer_config=SummarizerConfig(
        sensitive_fields={"password", "token", "api_key", "credit_card", "ssn", "cvv"},
        mask_placeholder="[REDACTED]",
    ),
)

backend_config = LoggingConfig(default_level=logging.WARNING, log_data_mode=LogDataMode.KEYS_ONLY)
backend_config.add_logger_config(
    LoggerConfig(name="rhosocial.activerecord.transaction", level=logging.INFO, log_data_mode=LogDataMode.SUMMARY)
)
```

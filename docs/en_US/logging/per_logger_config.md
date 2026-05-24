# Per-Logger Configuration

`LoggerConfig` defines per-logger rules inside one owning `LoggingConfig` object. ActiveRecord model config and backend config are independent unless you explicitly pass the same `LoggingConfig` object to both.

## Logger Names

| Component | Default logger example | Config owner |
| --------- | ---------------------- | ------------ |
| ActiveRecord model | `rhosocial.activerecord.model.User` | `ActiveRecord.__logging_config__` or `Model.__logging_config__` |
| Query | `rhosocial.activerecord.query.ActiveQuery` | backend `LoggingConfig` |
| Backend | `rhosocial.activerecord.backend.sqlite` | backend `LoggingConfig` |
| Transaction | `rhosocial.activerecord.transaction` | backend `LoggingConfig` |
| Framework worker | `rhosocial.activerecord.worker` | framework default via `configure_logging()` |

User models can override the emitted logger name:

```python
from rhosocial.activerecord.model import ActiveRecord

class User(ActiveRecord):
    __logger_name__ = "myapp.models.user"
    __table_name__ = "users"
```

Changing `__logger_name__` changes the logger target. Data visibility still comes from the model's `LoggingConfig`.

## Model Per-Logger Rules

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

A concrete model can own a completely separate config:

```python
class AuditUser(ActiveRecord):
    __table_name__ = "audit_users"
    __logging_config__ = LoggingConfig(log_data_mode=LogDataMode.HIDDEN)
```

## Backend Per-Logger Rules

Backend, query, and transaction logs are not controlled by `ActiveRecord.__logging_config__`:

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

## Hierarchical Matching

Per-logger rules match by logger namespace hierarchy inside the same `LoggingConfig` object:

```python
backend_config.add_logger_config(
    LoggerConfig(name="rhosocial.activerecord.backend", log_data_mode=LogDataMode.KEYS_ONLY)
)

backend_config.get_log_data_mode("rhosocial.activerecord.backend.sqlite")
# LogDataMode.KEYS_ONLY
```

Rules in `backend_config` do not affect `model_config`, and rules in `model_config` do not affect backend/query/transaction logs.

## Production Preset

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

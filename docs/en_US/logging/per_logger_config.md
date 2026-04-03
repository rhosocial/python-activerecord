# Per-Logger Configuration

> 💡 **AI Prompt**: "How can I set different data summarization modes for different components?"

In addition to global configuration, you can set different data summarization modes for specific logger levels. This allows you to:

- Use strict `keys_only` mode for sensitive backend logs
- Use `full` mode for debugging query logs
- Use custom summarization configurations for specific components

## Configuration

Use `LoggerConfig` to configure summarization mode for specific logger levels:

```python
from rhosocial.activerecord.logging import (
    get_logging_manager,
    LoggerConfig,
    SummarizerConfig,
)

manager = get_logging_manager()

# Set keys_only mode for backend layer (show field names only)
backend_config = LoggerConfig(
    name='rhosocial.activerecord.backend',
    log_data_mode='keys_only',
)
manager.config.add_logger_config(backend_config)

# Set full mode for query layer (show complete data)
query_config = LoggerConfig(
    name='rhosocial.activerecord.query',
    log_data_mode='full',
)
manager.config.add_logger_config(query_config)

# Set custom summarizer config for a specific model
custom_summarizer = SummarizerConfig(
    max_string_length=20,  # Shorter truncation length
    sensitive_fields={'password', 'secret'}
)
model_config = LoggerConfig(
    name='rhosocial.activerecord.model.User',
    log_data_mode='summary',
    summarizer_config=custom_summarizer,
)
manager.config.add_logger_config(model_config)
```

## Hierarchical Inheritance Rules

Configuration inherits along the hierarchy:

- `rhosocial.activerecord.backend.sqlite` inherits from `rhosocial.activerecord.backend`
- `rhosocial.activerecord.query.ActiveQuery` inherits from `rhosocial.activerecord.query`
- If no matching configuration, global defaults are used

```python
# backend.sqlite automatically inherits backend's keys_only mode
manager.config.get_log_data_mode('rhosocial.activerecord.backend.sqlite')
# Returns: 'keys_only'

# Unconfigured levels use global default
manager.config.get_log_data_mode('rhosocial.activerecord.model.Other')
# Returns: globally configured log_data_mode
```

## LoggerConfig Properties

`LoggerConfig` supports the following properties:

| Property | Type | Description |
|----------|------|-------------|
| `name` | str | Logger name |
| `level` | int | Log level (default: DEBUG) |
| `propagate` | bool | Whether to propagate to parent loggers (default: False) |
| `handlers` | list | List of log handlers |
| `log_data_mode` | str \| None | Data summarization mode for this logger, None means use global config |
| `summarizer_config` | SummarizerConfig \| None | Custom summarizer config for this logger, None means use global config |

## Real-World Scenarios

### Production Environment Configuration

```python
import logging
from rhosocial.activerecord.logging import (
    configure_logging,
    get_logging_manager,
    LoggerConfig,
    SummarizerConfig,
)

# Production: INFO level, backend uses keys_only
configure_logging(level=logging.INFO, propagate=False)

manager = get_logging_manager()

# Backend: keys_only (PCI compliance)
backend_config = LoggerConfig(
    name='rhosocial.activerecord.backend',
    log_data_mode='keys_only',
    level=logging.WARNING,
)
manager.config.add_logger_config(backend_config)

# Model: summary mode with extended sensitive fields
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

### Development Environment Configuration

```python
import logging
from rhosocial.activerecord.logging import (
    configure_logging,
    get_logging_manager,
    LoggerConfig,
)

# Development: DEBUG level, query uses full mode
configure_logging(level=logging.DEBUG, propagate=True)

manager = get_logging_manager()

# Query: full mode for debugging
query_config = LoggerConfig(
    name='rhosocial.activerecord.query',
    log_data_mode='full',
)
manager.config.add_logger_config(query_config)

# Backend: summary mode (show some data)
backend_config = LoggerConfig(
    name='rhosocial.activerecord.backend',
    log_data_mode='summary',
)
manager.config.add_logger_config(backend_config)
```

### Custom Model Logger

User-defined Model classes can have their own loggers:

```python
from rhosocial.activerecord.model import ActiveRecord

class User(ActiveRecord):
    __logger_name__ = 'myapp.models.user'  # Custom logger name
    # ...

# Configure custom logger
user_config = LoggerConfig(
    name='myapp.models.user',
    level=logging.DEBUG,
    log_data_mode='summary',
)
manager.config.add_logger_config(user_config)
```

## Runtime Override

You can explicitly specify mode at call time to override logger configuration:

```python
# Even if backend is configured as keys_only, force full mode
result = manager.config.summarize_data(
    test_data,
    mode='full',  # Explicitly specified mode
    logger_name='rhosocial.activerecord.backend'
)
```

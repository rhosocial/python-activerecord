# 7. Logging System

> 💡 **AI Prompt**: "How does ActiveRecord's logging system prevent sensitive data from appearing in logs?"

The `rhosocial-activerecord` logging system provides intelligent data summarization that automatically truncates large values and masks sensitive fields in log messages.

## Overview

Core principles of the logging system:

1. **Isolated from Root Logger**: Does not modify your application's root logger configuration
2. **Data Summarization**: Automatically truncates long strings and masks sensitive fields
3. **Configurable Modes**: Choose between summary mode, keys-only mode, or full logging mode
4. **Zero Configuration**: Works out of the box with sensible defaults
5. **Hierarchical Naming**: Uses semantic hierarchical logger namespace for unified control and fine-grained tuning

## Chapter Contents

* **[Logger Namespace](namespace.md)**: Hierarchical naming rules, user-defined class handling, inheritance benefits
* **[Data Summarization](data_summarization.md)**: Sensitive field masking, three logging modes, configuration options
* **[Per-Logger Configuration](per_logger_config.md)**: Setting different modes for different components, inheritance rules

## Quick Start

### Basic Usage

The logging system is automatically configured when using ActiveRecord:

```python
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend

# Logging is automatically set up
class User(ActiveRecord):
    __table_name__ = "users"
    id: Optional[int] = None
    username: str
    password: str  # Will be masked in logs

# When saving, password is automatically masked in logs
user = User(username="john", password="secret123")
user.save()
# Log shows: {'username': 'john', 'password': '***MASKED***'}
```

### Customizing Log Level

```python
import logging
from rhosocial.activerecord.logging import configure_logging

# Set log level to INFO
configure_logging(level=logging.INFO)
```

### Quick Data Summarization Setup

```python
from rhosocial.activerecord.logging import (
    SummarizerConfig,
    get_logging_manager,
)

# Define custom sensitive fields
config = SummarizerConfig(
    sensitive_fields={
        'password', 'token', 'api_key',
        'credit_card', 'ssn'
    },
    mask_placeholder='[REDACTED]',
)

manager = get_logging_manager()
manager._config.summarizer_config = config
```

## Example Code

Complete example code is located in the `docs/examples/chapter_07_logging/` directory:

| File | Description |
|------|-------------|
| [01_basic_configuration.py](../../examples/chapter_07_logging/01_basic_configuration.py) | Basic configuration: log level settings, namespace hierarchy, runtime level changes |
| [02_data_summarization.py](../../examples/chapter_07_logging/02_data_summarization.py) | Data summarization: sensitive field masking, string truncation, three logging modes |
| [03_per_logger_config.py](../../examples/chapter_07_logging/03_per_logger_config.py) | Per-logger configuration: different modes for different components, hierarchical inheritance |
| [04_advanced_scenarios.py](../../examples/chapter_07_logging/04_advanced_scenarios.py) | Advanced scenarios: production/development configs, custom logger names, application integration |

Running the examples:

```bash
cd python-activerecord
source .venv3.8/bin/activate
python docs/examples/chapter_07_logging/01_basic_configuration.py
```

## Best Practices

1. **Production**: Use `summary` or `keys_only` mode
2. **Development**: Use `summary` mode with `DEBUG` level
3. **Debugging**: Temporarily use `full` mode, but never commit to production
4. **Custom fields**: Always add application-specific sensitive fields to the configuration
5. **Compliance**: Use `keys_only` mode for GDPR/PCI compliance when possible

## See Also

- [Troubleshooting](../getting_started/troubleshooting.md) - Common logging issues
- [Performance](../performance/README.md) - Logging overhead considerations

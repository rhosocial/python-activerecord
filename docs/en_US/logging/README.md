# Logging System

> 💡 **AI Prompt**: "How does ActiveRecord's logging system prevent sensitive data from appearing in logs?"

The `rhosocial-activerecord` logging system provides intelligent data summarization capabilities that automatically truncate large values and mask sensitive fields in log messages.

## Overview

Key principles of the logging system:

1. **Isolated from root logger**: Does not modify your application's root logger configuration
2. **Data summarization**: Automatically truncates long strings and masks sensitive fields
3. **Configurable modes**: Choose between summary, keys-only, or full logging
4. **Zero setup**: Works out of the box with sensible defaults

## Quick Start

### Basic Usage

The logging system is automatically configured when you use ActiveRecord:

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

## Data Summarization

### How It Works

When logging data (like INSERT/UPDATE parameters), the `DataSummarizer` automatically:

1. **Truncates long strings**: Prevents log bloat from large text fields
2. **Masks sensitive fields**: Hides passwords, tokens, API keys, etc.
3. **Limits collection sizes**: Shows first N items in lists/dicts
4. **Controls nesting depth**: Prevents infinite recursion

### Default Sensitive Fields

The following field names are automatically masked (case-insensitive):

```text
password, passwd, pwd
token, access_token, refresh_token, auth_token
secret, secret_key, api_key, apikey
credential, credentials
private_key, privatekey
```

### Custom Sensitive Fields

```python
from rhosocial.activerecord.logging import (
    SummarizerConfig,
    get_logging_manager,
)

# Define custom sensitive fields
config = SummarizerConfig(
    sensitive_fields={
        'password', 'token', 'api_key',
        'credit_card', 'ssn', 'phone'  # Add your custom fields
    }
)

manager = get_logging_manager()
manager._config.summarizer_config = config
```

### Appending to Default Fields

```python
from rhosocial.activerecord.logging import get_logging_manager, SummarizerConfig

manager = get_logging_manager()
current_fields = manager._config.summarizer_config.sensitive_fields

# Add new fields while keeping defaults
new_config = SummarizerConfig(
    sensitive_fields=current_fields | {'credit_card', 'ssn'}
)
manager._config.summarizer_config = new_config
```

### Disabling Sensitive Field Masking

If you don't need sensitive field masking (for example, in a controlled development environment), you can disable it:

```python
from rhosocial.activerecord.logging import (
    SummarizerConfig,
    get_logging_manager,
)

# Set empty sensitive fields set to disable masking
config = SummarizerConfig(
    sensitive_fields=set()  # Empty set = no fields masked
)

manager = get_logging_manager()
manager._config.summarizer_config = config
```

> ⚠️ **Warning**: Disabling sensitive field masking may cause passwords, tokens, and other sensitive information to appear in logs. Only use this configuration in secure, controlled environments.

## Logging Modes

Three modes control how data is logged:

### 1. Summary Mode (Default)

Truncates long values and masks sensitive fields:

```python
manager._config.log_data_mode = 'summary'

# Result in logs:
# {'title': 'Short', 'content': 'Lorem ipsum...[truncated, 1000 chars total]', 'password': '***MASKED***'}
```

### 2. Keys-Only Mode

Shows only field names with type hints, no actual values:

```python
manager._config.log_data_mode = 'keys_only'

# Result in logs:
# {'title': '<str>', 'content': '<str>', 'password': '***MASKED***'}
```

### 3. Full Mode

Shows complete data without summarization (use with caution):

```python
manager._config.log_data_mode = 'full'

# Result in logs (full data):
# {'title': 'Short', 'content': 'Lorem ipsum dolor...', 'password': 'secret123'}
```

> ⚠️ **Warning**: `full` mode may log sensitive data. Not recommended for production.

## Configuration Options

All available `SummarizerConfig` options:

| Option | Default | Description |
|--------|---------|-------------|
| `max_string_length` | 100 | Maximum string length before truncation |
| `max_bytes_length` | 64 | Maximum bytes length before truncation |
| `max_dict_items` | 10 | Maximum items to show in dicts/lists |
| `max_depth` | 5 | Maximum nesting depth for recursive data |
| `sensitive_fields` | See above | Set of field names to mask |
| `mask_placeholder` | `***MASKED***` | Placeholder for masked fields |
| `string_placeholder` | `...[truncated, {length} chars total]` | Placeholder for truncated strings |
| `show_type_hint` | True | Show type hints in truncation messages |

### Complete Configuration Example

```python
import logging
from rhosocial.activerecord.logging import (
    SummarizerConfig,
    LoggingConfig,
    get_logging_manager,
)

# Create custom configuration
summarizer_config = SummarizerConfig(
    max_string_length=200,
    max_dict_items=5,
    sensitive_fields={
        'password', 'token', 'api_key',
        'credit_card', 'ssn'
    },
    mask_placeholder='[REDACTED]',
)

manager = get_logging_manager()
manager._config.summarizer_config = summarizer_config
manager._config.log_data_mode = 'summary'
manager._config.default_level = logging.DEBUG
```

## Using log_data Methods

The `LoggingMixin` provides convenient methods for logging with summarization:

```python
from rhosocial.activerecord.model import ActiveRecord
import logging

class User(ActiveRecord):
    __table_name__ = "users"
    # ... fields ...

# Log data with automatic summarization
User.log_data(logging.INFO, "Creating user", {
    'username': 'john',
    'password': 'secret123',
    'bio': 'A' * 1000
})

# Log keys only (no values)
User.log_data_keys_only(logging.INFO, "User data", user_dict)

# Log full data (bypass summarization)
User.log_data_full(logging.DEBUG, "Debug user data", user_dict)
```

## Integration with Backends

Backends automatically use data summarization when logging queries:

```python
# SQLite backend logs INSERT with summarization
user = User(username="john", password="secret", bio="Long bio...")
user.save()

# Logs appear as:
# DEBUG - Raw data for insert: {'username': 'john', 'password': '***MASKED***', 'bio': 'Long bio...[truncated, 1000 chars total]'}
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

# Data Summarization

> 💡 **AI Prompt**: "How does ActiveRecord's data summarization prevent sensitive data from appearing in logs?"

When logging data (such as INSERT/UPDATE parameters), `DataSummarizer` automatically:

1. **Truncates Long Strings**: Prevents log bloat from large text fields
2. **Masks Sensitive Fields**: Hides passwords, tokens, API keys, etc.
3. **Limits Collection Size**: Shows only the first N items in lists/dicts
4. **Controls Nesting Depth**: Prevents infinite recursion

## Default Sensitive Fields

The following field names are automatically masked (case-insensitive):

```text
password, passwd, pwd
token, access_token, refresh_token, auth_token
secret, secret_key, api_key, apikey
credential, credentials
private_key, privatekey
```

## Custom Sensitive Fields

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
manager.config.summarizer_config = config
```

### Appending to Default Fields

```python
from rhosocial.activerecord.logging import get_logging_manager, SummarizerConfig

manager = get_logging_manager()
current_fields = manager.config.summarizer_config.sensitive_fields

# Add new fields while preserving defaults
new_config = SummarizerConfig(
    sensitive_fields=current_fields | {'credit_card', 'ssn'}
)
manager.config.summarizer_config = new_config
```

### Disabling Sensitive Field Masking

If you don't need sensitive field masking (e.g., in a controlled development environment), you can disable it:

```python
from rhosocial.activerecord.logging import (
    SummarizerConfig,
    get_logging_manager,
)

# Set empty sensitive fields set to disable masking
config = SummarizerConfig(
    sensitive_fields=set()  # Empty set = no masking
)

manager = get_logging_manager()
manager.config.summarizer_config = config
```

> ⚠️ **Warning**: Disabling sensitive field masking may cause passwords, tokens, and other sensitive information to appear in logs. Only use this configuration in secure, controlled environments.

## Logging Modes

Three modes control how data is logged:

### 1. Summary Mode (Default)

Truncates long values and masks sensitive fields:

```python
manager.config.log_data_mode = 'summary'

# Result in logs:
# {'title': 'Short', 'content': 'Lorem ipsum...[truncated, 1000 chars total]', 'password': '***MASKED***'}
```

### 2. Keys-Only Mode

Shows only field names and type hints, not actual values:

```python
manager.config.log_data_mode = 'keys_only'

# Result in logs:
# {'title': '<str>', 'content': '<str>', 'password': '***MASKED***'}
```

This mode is ideal for production environments and GDPR/PCI compliance scenarios.

### 3. Full Mode

Shows complete data without summarization (use with caution):

```python
manager.config.log_data_mode = 'full'

# Result in logs (complete data):
# {'title': 'Short', 'content': 'Lorem ipsum dolor...', 'password': 'secret123'}
```

> ⚠️ **Warning**: `full` mode may log sensitive data. Not recommended for production environments.

## Configuration Options

All available `SummarizerConfig` options:

| Option | Default | Description |
|--------|---------|-------------|
| `max_string_length` | 100 | Maximum string length before truncation |
| `max_bytes_length` | 64 | Maximum bytes length before truncation |
| `max_dict_items` | 10 | Maximum items to show in dicts/lists |
| `max_depth` | 5 | Maximum nesting depth for recursive data |
| `sensitive_fields` | See above | Set of field names to mask |
| `mask_placeholder` | `***MASKED***` | Placeholder for masked fields (string or callable) |
| `field_maskers` | `{}` | Mapping of field names to custom masker functions |
| `string_placeholder` | `...[truncated, {length} chars total]` | Placeholder for truncated strings |
| `show_type_hint` | True | Show type hints in truncation messages |

### Custom Masker Functions

`mask_placeholder` can be either a string or a callable (like a lambda function). When callable, it receives the original value and returns the masked result:

```python
from rhosocial.activerecord.logging import SummarizerConfig

# Use callable mask_placeholder
config = SummarizerConfig(
    sensitive_fields={'password', 'token'},
    mask_placeholder=lambda v: f'<{len(str(v))} chars hidden>'
)

# Result: {'password': '<9 chars hidden>', 'token': '<12 chars hidden>'}
```

### Field-Specific Custom Maskers

`field_maskers` allows specifying custom masker functions for specific fields, taking precedence over the global `mask_placeholder`:

```python
from rhosocial.activerecord.logging import SummarizerConfig, get_logging_manager

config = SummarizerConfig(
    sensitive_fields={'password', 'email', 'api_key'},
    # Global fallback masker
    mask_placeholder='[REDACTED]',
    # Field-specific custom maskers
    field_maskers={
        # Show first char of local part
        'email': lambda v: v.split('@')[0][:1] + '***@' + v.split('@')[1] if '@' in str(v) else '***',
        # Show password length as asterisks
        'password': lambda v: '*' * min(len(str(v)), 8),
    }
)

manager = get_logging_manager()
manager.config.summarizer_config = config

# Example result:
# {'email': 'jo***@example.com', 'password': '********', 'api_key': '[REDACTED]'}
```

**Masking Priority**:

1. Field-specific `field_maskers` (highest priority)
2. Global `mask_placeholder`
3. Default `***MASKED***` (fallback when masker raises exception)

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
manager.config.summarizer_config = summarizer_config
manager.config.log_data_mode = 'summary'
manager.config.default_level = logging.DEBUG
```

## Using log_data Methods

`LoggingMixin` provides convenient methods for logging data with summarization:

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

# Log keys only (not values)
User.log_data_keys_only(logging.INFO, "User data", user_dict)

# Log full data (bypass summarization)
User.log_data_full(logging.DEBUG, "Debug user data", user_dict)
```

## Backend Integration

Backends automatically use data summarization when logging queries:

```python
# SQLite backend logs INSERT with summarization
user = User(username="john", password="secret", bio="Long bio...")
user.save()

# Logs appear as:
# DEBUG - Raw data for insert: {'username': 'john', 'password': '***MASKED***', 'bio': 'Long bio...[truncated, 1000 chars total]'}
```

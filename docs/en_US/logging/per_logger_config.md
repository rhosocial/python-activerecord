# Per-Logger Configuration

> 💡 **AI Prompt**: "How can I set different data summarization modes for different components?"

In addition to global configuration, you can set different data summarization modes for specific logger levels. This allows you to:

- Use strict `keys_only` mode for sensitive backend logs
- Use `full` mode for debugging query logs
- Use custom summarization configurations for specific components

## Logger Naming Rules

Before configuring loggers, it's important to understand how ActiveRecord classes generate logger names:

### Default Naming Rules

ActiveRecord classes automatically generate logger names based on their module and class name:

| Class Type | Logger Name Format | Example |
|------------|-------------------|---------|
| Library classes (module starts with `rhosocial.activerecord`) | `rhosocial.activerecord.model.{ClassName}` | `rhosocial.activerecord.model.User` |
| User-defined classes (other modules) | `{module}.{ClassName}` | `myapp.models.User` |

### Custom Logger Name

You can override the default naming by setting the `__logger_name__` attribute in your class:

```python
from rhosocial.activerecord.model import ActiveRecord

class User(ActiveRecord):
    __logger_name__ = 'myapp.models.user'  # Custom logger name
    __table_name__ = "users"
    # ... field definitions ...
```

### Association with CRUD Operations

Once a logger is configured, all database operations (save, delete, query, etc.) for that class will automatically use that logger, and data in logs will be processed according to the configured summarization mode:

- **INSERT/UPDATE**: Recorded data will be summarized according to the configured mode
- **DELETE**: Delete conditions will be processed according to the configuration
- **SELECT**: Query parameters will be summarized according to the configuration

## Logger Support Across Components

> 💡 **AI Prompt**: "Do ActiveQuery, CTEQuery, SetOperationQuery, and Backend also support custom logger names?"

Yes, all components support custom logger names, but they use different attribute names and levels:

### Component Comparison Table

| Component | Custom Support | Attribute Name | Level | Default Logger Format |
|-----------|---------------|----------------|-------|----------------------|
| ActiveRecord | ✅ | `__logger_name__` | Class level | `rhosocial.activerecord.model.{ClassName}` |
| ActiveQuery | ✅ | `_logger_name` | Instance level | `rhosocial.activerecord.query.ActiveQuery` |
| CTEQuery | ✅ | `_logger_name` | Instance level | `rhosocial.activerecord.query.CTEQuery` |
| SetOperationQuery | ✅ | `_logger_name` | Instance level | `rhosocial.activerecord.query.SetOperationQuery` |
| Backend | ✅ | `_logger_name` | Instance level | `rhosocial.activerecord.backend.{type}` |

### Key Differences

1. **ActiveRecord** uses **class-level** `__logger_name__` (double underscore), set at class definition time
2. **Query classes and Backend** use **instance-level** `_logger_name` (single underscore), set after instance creation

```python
# ActiveRecord: Class-level setting
class User(ActiveRecord):
    __logger_name__ = 'myapp.models.user'  # Set at class definition

# Query: Instance-level setting
query = User.query()
query._logger_name = 'myapp.queries.user'  # Set after instance creation

# Backend: Instance-level setting
backend = User.backend()
backend._logger_name = 'myapp.backends.main'  # Set after instance creation
```

## Logger Independence vs Inheritance

> 💡 **AI Prompt**: "If I define `__logger_name__` for an ActiveRecord class, will the ActiveQuery it creates inherit this logger name?"

**No, it will not inherit automatically.** This is a design feature that reflects the separation of namespaces:

### Design Rationale

ActiveRecord and ActiveQuery reside in different namespaces with distinct responsibilities:

| Component | Default Namespace | Responsibility |
|-----------|-------------------|----------------|
| **ActiveRecord** | `rhosocial.activerecord.model` | Data modification operations (DML) |
| **ActiveQuery** | `rhosocial.activerecord.query` | Data query operations (DQL) |
| **Backend** | `rhosocial.activerecord.backend` | Low-level SQL execution |

Advantages of this namespace separation:

1. **Clear Responsibilities**: Model handles data changes, Query handles data retrieval
2. **Log Categorization**: Easy to filter and analyze logs by operation type
3. **Independent Configuration**: Different summarization modes and log levels for DML and DQL

### Logger Naming Example

```python
class User(ActiveRecord):
    __logger_name__ = 'myapp.models.user'
    __table_name__ = "users"
    # ...

# Model layer logger: myapp.models.user
user = User(username='alice', password='secret')
user.save()

# Query layer logger: rhosocial.activerecord.query.ActiveQuery (independent namespace)
query = User.query()
users = query.where(User.c.status == 'active').all()
```

### Log Output Distribution

A complete query operation produces logs across multiple namespaces:

| Operation Phase | Namespace | Example |
|-----------------|-----------|---------|
| Model layer (save/delete) | `myapp.models.user` | Create/update/delete records |
| Query layer (query building) | `rhosocial.activerecord.query.ActiveQuery` | Execute SELECT statements |
| Backend layer (SQL execution) | `rhosocial.activerecord.backend.sqlite` | Low-level database operations |

### Unifying ActiveRecord and ActiveQuery Loggers

If you want ActiveRecord and its associated ActiveQuery to use the same logger name, you can achieve this by subclassing ActiveQuery:

```python
from typing import Optional, Type
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.query import ActiveQuery

class CustomActiveQuery(ActiveQuery):
    """ActiveQuery with unified logger support"""

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
        """Override query() to use the same logger as Model"""
        return CustomActiveQuery(cls, logger_name=cls._get_logger_name())

    # Field definitions...
    id: Optional[int] = None
    username: str
    password: str

# Now both User and User.query() use 'myapp.models.user' logger
user = User(username='alice', password='secret')
user.save()  # Logger: myapp.models.user

users = User.query().where(User.c.status == 'active').all()  # Logger: myapp.models.user
```

### Temporarily Modifying a Single Query Instance

If you only need to temporarily change a Query's logger, you can set it directly on the instance:

```python
# Temporarily use a different logger
query = User.query()
query._logger_name = 'myapp.queries.audit'
users = query.all()
```

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

### Configure for a Specific Model

You can configure a dedicated log summarization mode for a single ActiveRecord class. Once configured, all CRUD operations for that class will automatically apply this configuration:

```python
from typing import Optional
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.logging import (
    get_logging_manager,
    LoggerConfig,
    SummarizerConfig,
)

# Define model class
class User(ActiveRecord):
    __table_name__ = "users"
    id: Optional[int] = None
    username: str
    password: str      # Will be masked in logs
    email: str         # Will be masked in logs
    credit_card: str   # Will be masked in logs

# Configure dedicated summarizer for User class
user_summarizer = SummarizerConfig(
    max_string_length=30,  # Shorter truncation length
    sensitive_fields={'password', 'email', 'credit_card'},
    mask_placeholder='[PROTECTED]',
)

# Configure logger for User class
# Default logger name is: rhosocial.activerecord.model.User
user_config = LoggerConfig(
    name='rhosocial.activerecord.model.User',
    log_data_mode='summary',
    summarizer_config=user_summarizer,
)

manager = get_logging_manager()
manager.config.add_logger_config(user_config)

# Now all User operations will use this configuration
user = User(username='alice', password='secret123', email='alice@example.com', credit_card='4111111111111111')
user.save()  # password, email, credit_card will all show as [PROTECTED] in logs
```

### Using Custom Logger Name

If you want to use a custom logger name (e.g., to integrate with your application's logging system), you can define the `__logger_name__` attribute in your class:

```python
from rhosocial.activerecord.model import ActiveRecord
import logging

class User(ActiveRecord):
    __logger_name__ = 'myapp.models.user'  # Custom logger name
    __table_name__ = "users"
    # ... field definitions ...

# Configure for the custom logger name
user_config = LoggerConfig(
    name='myapp.models.user',
    level=logging.DEBUG,
    log_data_mode='summary',
    summarizer_config=custom_summarizer,
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

# Logger Namespace

> 💡 **AI Prompt**: "Why does ActiveRecord use a hierarchical logger namespace? What are the benefits?"

The logging system uses an independent semantic hierarchical namespace that doesn't directly correspond to code module paths:

```text
rhosocial.activerecord                           # Root logger
├── rhosocial.activerecord.model                 # Model layer
│   └── rhosocial.activerecord.model.{ClassName} # Built-in model classes
├── rhosocial.activerecord.backend               # Backend layer
│   ├── rhosocial.activerecord.backend.sqlite    # SQLite backend
│   └── rhosocial.activerecord.backend.mysql     # MySQL backend
├── rhosocial.activerecord.query                 # Query layer
│   ├── rhosocial.activerecord.query.ActiveQuery
│   ├── rhosocial.activerecord.query.CTEQuery
│   └── rhosocial.activerecord.query.SetOperationQuery
└── rhosocial.activerecord.transaction           # Transaction layer
```

## User-Defined Classes

User-defined Model classes use their module namespace, not the library namespace:

```python
# myapp/models.py
class User(ActiveRecord):
    pass
# Logger: myapp.models.User
```

You can also explicitly specify via `__logger_name__`:

```python
class Article(ActiveRecord):
    __logger_name__ = 'myapp.article'
# Logger: myapp.article
```

## Benefits of Hierarchical Naming

### 1. Unified Control

Control all child loggers through parent logger:

```python
# Adjust all activerecord-related log levels at once
logging.getLogger('rhosocial.activerecord').setLevel(logging.WARNING)

# Debug only the model layer
logging.getLogger('rhosocial.activerecord.model').setLevel(logging.DEBUG)
```

### 2. Log Propagation

Child logger messages automatically propagate to parent loggers. Just configure a handler at the root logger to capture all child logger output.

### 3. Flexible Filtering

Set different handlers and filters at different levels:

```python
# Root logger: output to console
console_handler = logging.StreamHandler()
logging.getLogger('rhosocial.activerecord').addHandler(console_handler)

# Backend logs: also output to file
file_handler = logging.FileHandler('backend.log')
logging.getLogger('rhosocial.activerecord.backend').addHandler(file_handler)
```

### 4. Runtime Adjustment

Dynamically adjust log levels for specific components in production:

```python
# Enable DEBUG logging for User model only
logging.getLogger('rhosocial.activerecord.model.User').setLevel(logging.DEBUG)
```

## Relationship with Python logging

This hierarchical naming follows Python logging module best practices:

- Dot-separated names establish parent-child relationships
- Child loggers automatically inherit parent logger configuration
- Supports `propagate` attribute to control log propagation behavior

Major Python libraries use similar approaches:
- SQLAlchemy: `sqlalchemy.engine`, `sqlalchemy.orm`, `sqlalchemy.pool`
- Django: `django.request`, `django.db.backends`

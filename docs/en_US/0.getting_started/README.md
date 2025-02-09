# Getting Started with rhosocial ActiveRecord

rhosocial ActiveRecord is a modern Python implementation of the ActiveRecord pattern, providing an elegant and type-safe interface for database operations. This guide will help you get started with using the library in your projects.

## What is ActiveRecord?

ActiveRecord is a design pattern that wraps database operations in object-oriented classes. Each ActiveRecord object corresponds to a row in a database table, encapsulating database access and adding domain logic to the data.

## Key Features

- Pure Python implementation with no external ORM dependencies
- Type-safe field definitions using Pydantic
- Built-in SQLite support
- Rich relationship support (BelongsTo, HasOne, HasMany)
- Fluent query builder interface
- Advanced transaction support
- Event system for model lifecycle hooks
- Enterprise features like optimistic locking and soft delete

## Example Use Case

Let's look at a common social media application structure:

```python
from rhosocial.activerecord import ActiveRecord
from datetime import datetime

class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: int
    username: str
    email: str
    created_at: datetime

class Post(ActiveRecord):
    __table_name__ = 'posts'
    
    id: int
    user_id: int
    content: str
    created_at: datetime

class Comment(ActiveRecord):
    __table_name__ = 'comments'
    
    id: int
    post_id: int
    user_id: int
    content: str
    created_at: datetime
```

This basic structure shows how ActiveRecord models map to database tables while maintaining type safety through Python type hints.

## Next Steps

1. Check the [Requirements](requirements.md) to ensure your environment is ready
2. Follow the [Installation](installation.md) guide to install the package
3. Configure your database connection using the [Configuration](configuration.md) guide
4. Try out the examples in [Quickstart](quickstart.md)

## Support

If you encounter any issues or need help:
- Check our [Documentation](https://docs.python-activerecord.dev.rho.social/)
- Open an issue on [GitHub](https://github.com/rhosocial/python-activerecord/issues)
- Join our community discussions
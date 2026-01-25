# Quick Start

Let's build a simple blog system to see `rhosocial-activerecord` in action, demonstrating both synchronous and asynchronous implementations with **Sync-Async Parity**.

## 1. Define Models

We will define both synchronous and asynchronous `User` and `Post` models to showcase the **Sync-Async Parity** principle.

### Synchronous Models

```python
import uuid
from typing import ClassVar
from pydantic import Field
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.field import UUIDMixin, TimestampMixin
from rhosocial.activerecord.relation import HasMany, BelongsTo

class User(UUIDMixin, TimestampMixin, ActiveRecord):
    username: str = Field(..., max_length=50)
    email: str

    # Enable type-safe query building
    c: ClassVar[FieldProxy] = FieldProxy()

    # Relations
    posts: ClassVar[HasMany['Post']] = HasMany(foreign_key='user_id', inverse_of='author')

    @classmethod
    def table_name(cls) -> str:
        return 'users'

class Post(UUIDMixin, TimestampMixin, ActiveRecord):
    title: str
    content: str
    user_id: uuid.UUID  # Foreign Key

    # Enable type-safe query building
    c: ClassVar[FieldProxy] = FieldProxy()

    # Relations
    author: ClassVar[BelongsTo['User']] = BelongsTo(foreign_key='user_id', inverse_of='posts')

    @classmethod
    def table_name(cls) -> str:
        return 'posts'
```

### Asynchronous Models

```python
import uuid
from typing import ClassVar
from pydantic import Field
from rhosocial.activerecord.model import AsyncActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.field import UUIDMixin, TimestampMixin
from rhosocial.activerecord.relation import AsyncHasMany, AsyncBelongsTo

class AsyncUser(UUIDMixin, TimestampMixin, AsyncActiveRecord):
    username: str = Field(..., max_length=50)
    email: str

    # Enable type-safe query building
    c: ClassVar[FieldProxy] = FieldProxy()

    # Relations
    posts: ClassVar[AsyncHasMany['AsyncPost']] = AsyncHasMany(foreign_key='user_id', inverse_of='author')

    @classmethod
    def table_name(cls) -> str:
        return 'users'

class AsyncPost(UUIDMixin, TimestampMixin, AsyncActiveRecord):
    title: str
    content: str
    user_id: uuid.UUID  # Foreign Key

    # Enable type-safe query building
    c: ClassVar[FieldProxy] = FieldProxy()

    # Relations
    author: ClassVar[AsyncBelongsTo['AsyncUser']] = AsyncBelongsTo(foreign_key='user_id', inverse_of='posts')

    @classmethod
    def table_name(cls) -> str:
        return 'posts'
```

## 2. Setup Database

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig, AsyncSQLiteBackend
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

# Configure synchronous models
sync_config = SQLiteConnectionConfig(database=':memory:')
User.configure(sync_config, SQLiteBackend)
Post.__backend__ = User.__backend__  # Share connection

# Configure asynchronous models
async_config = SQLiteConnectionConfig(database=':memory:')
AsyncUser.configure(async_config, AsyncSQLiteBackend)
AsyncPost.__backend__ = AsyncUser.__backend__  # Share connection

# Create Tables
# Note: In production, use a migration tool. Here we use raw SQL for simplicity.
schema_sql_users = """
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    username VARCHAR(50),
    email VARCHAR(100),
    created_at TEXT,
    updated_at TEXT,
    version INTEGER DEFAULT 1
);
"""
schema_sql_posts = """
CREATE TABLE posts (
    id TEXT PRIMARY KEY,
    title VARCHAR(200),
    content TEXT,
    user_id TEXT,
    created_at TEXT,
    updated_at TEXT,
    version INTEGER DEFAULT 1
);
"""
User.backend().execute(schema_sql_users, options=ExecutionOptions(stmt_type=StatementType.DDL))
User.backend().execute(schema_sql_posts, options=ExecutionOptions(stmt_type=StatementType.DDL))
```

## 3. CRUD Operations

### Synchronous Operations

```python
# Create
alice = User(username="alice", email="alice@example.com")
alice.save()

# Create Related
post = Post(title="Hello World", content="My first post", user_id=alice.id)
post.save()

# Read
user = User.find_one({'username': 'alice'})
print(f"Found user: {user.username}")

# Read Related
# Note: Use the method call syntax for relations
user_posts = user.posts()
print(f"User has {len(user_posts)} posts")

# Update
user.email = "new_email@example.com"
user.save()

# Delete
post.delete()
```

### Asynchronous Operations

```python
import asyncio

async def async_crud_operations():
    # Create
    bob = AsyncUser(username="bob", email="bob@example.com")
    await bob.save()

    # Create Related
    post = AsyncPost(title="Async Hello World", content="My first async post", user_id=bob.id)
    await post.save()

    # Read
    user = await AsyncUser.find_one({'username': 'bob'})
    print(f"Found async user: {user.username}")

    # Read Related
    # Note: Use the method call syntax for relations
    user_posts = await user.posts()
    print(f"Async user has {len(user_posts)} posts")

    # Update
    user.email = "new_async_email@example.com"
    await user.save()

    # Delete
    await post.delete()

# Run the async operations
# asyncio.run(async_crud_operations())
```

## 4. Sync-Async Parity in Action

Notice how the synchronous and asynchronous implementations follow the same patterns:

*   **Method Signatures**: Both `User.save()` and `AsyncUser.save()` have the same parameters and return types (with the exception of `async`/`await`)
*   **Query Interface**: Both `User.find_one()` and `AsyncUser.find_one()` accept the same parameters
*   **Relation Handling**: Both synchronous and asynchronous relations work similarly
*   **Functionality**: Every feature available in the synchronous version is also available in the asynchronous version

This **Sync-Async Parity** allows you to seamlessly transition between synchronous and asynchronous contexts without learning different APIs or sacrificing functionality.

This simple example demonstrates the core workflow: Define -> Configure -> Interact, with both synchronous and asynchronous implementations showcasing the **Sync-Async Parity** principle.

# Quick Start

Let's build a simple blog system to see `rhosocial-activerecord` in action.

## 1. Define Models

We will define a `User` and a `Post` model.

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

## 2. Setup Database

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

# Configure
config = SQLiteConnectionConfig(database=':memory:')
User.configure(config, SQLiteBackend)
Post.__backend__ = User.__backend__  # Share connection

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

This simple example demonstrates the core workflow: Define -> Configure -> Interact.

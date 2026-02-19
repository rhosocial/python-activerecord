# Quick Start

Let's build a simple blog system to see `rhosocial-activerecord` in action, demonstrating both synchronous and asynchronous implementations with **Sync-Async Parity**.

> 💡 **AI Prompt Example**: "I want to quickly understand how to build a blog system using rhosocial-activerecord, can you give me a complete example?"

## 1. Define Models

In this step, we will define the core models for our blog system: User and Post. We will create both synchronous and asynchronous versions of the models to demonstrate the **Sync-Async Parity** principle.

### Synchronous Models

Synchronous models use the `ActiveRecord` base class, suitable for traditional synchronous programming scenarios.

> 💡 **AI Prompt Example**: "I want to create a blog system with user and post relationships, how should I define the models?"

```python
# Import necessary modules
import uuid
from typing import ClassVar
from pydantic import Field
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.field import UUIDMixin, TimestampMixin
from rhosocial.activerecord.relation import HasMany, BelongsTo

# User class represents users in the blog system
# Inheriting UUIDMixin automatically adds UUID primary key, TimestampMixin adds creation and update time fields
# ActiveRecord is the base class for synchronous models
class User(UUIDMixin, TimestampMixin, ActiveRecord):
    # Username field, maximum 50 characters, required
    username: str = Field(..., max_length=50)
    # Email field, no length limit
    email: str

    # FieldProxy enables type-safe query building
    # Type-safe field references can be made through User.c.username
    c: ClassVar[FieldProxy] = FieldProxy()

    # Define one-to-many relationship between users and posts
    # One user can have multiple posts
    # ClassVar ensures this relationship is not treated as a model field by Pydantic
    # foreign_key specifies the foreign key field name, inverse_of specifies the inverse relationship name
    posts: ClassVar[HasMany['Post']] = HasMany(foreign_key='user_id', inverse_of='author')

    # Return database table name, if not defined it defaults to lowercase plural form of class name
    @classmethod
    def table_name(cls) -> str:
        return 'users'

# Post class represents posts in the blog system
class Post(UUIDMixin, TimestampMixin, ActiveRecord):
    # Post title field
    title: str
    # Post content field
    content: str
    # Foreign key field linking to User table's id field
    user_id: uuid.UUID

    # FieldProxy enables type-safe query building
    c: ClassVar[FieldProxy] = FieldProxy()

    # Define one-to-one relationship (many-to-one) between posts and users
    # One post belongs to one user
    author: ClassVar[BelongsTo['User']] = BelongsTo(foreign_key='user_id', inverse_of='posts')

    # Return database table name
    @classmethod
    def table_name(cls) -> str:
        return 'posts'
```

> 💡 **AI Prompt Example**: "Why should I use ClassVar to define relationships in models? What are the benefits?"

### Asynchronous Models

Asynchronous models use the `AsyncActiveRecord` base class, suitable for high-concurrency asynchronous programming scenarios.

> 💡 **AI Prompt Example**: "What are the differences between synchronous and asynchronous models in definition? Why use different relationship classes?"

```python
# Import necessary modules
import uuid
from typing import ClassVar
from pydantic import Field
from rhosocial.activerecord.model import AsyncActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.field import UUIDMixin, TimestampMixin
from rhosocial.activerecord.relation import AsyncHasMany, AsyncBelongsTo

# AsyncUser class is the asynchronous version of User
# Inherits the same Mixins, but base class is AsyncActiveRecord
class AsyncUser(UUIDMixin, TimestampMixin, AsyncActiveRecord):
    # Username field, same as synchronous version
    username: str = Field(..., max_length=50)
    # Email field, same as synchronous version
    email: str

    # FieldProxy enables type-safe query building, same as synchronous version
    c: ClassVar[FieldProxy] = FieldProxy()

    # Use AsyncHasMany to define asynchronous one-to-many relationship
    # Same functionality as HasMany, but suitable for asynchronous environments
    posts: ClassVar[AsyncHasMany['AsyncPost']] = AsyncHasMany(foreign_key='user_id', inverse_of='author')

    # Return database table name, same as synchronous version
    @classmethod
    def table_name(cls) -> str:
        return 'users'

# AsyncPost class is the asynchronous version of Post
class AsyncPost(UUIDMixin, TimestampMixin, AsyncActiveRecord):
    # Post title field, same as synchronous version
    title: str
    # Post content field, same as synchronous version
    content: str
    # Foreign key field, same as synchronous version
    user_id: uuid.UUID

    # FieldProxy enables type-safe query building, same as synchronous version
    c: ClassVar[FieldProxy] = FieldProxy()

    # Use AsyncBelongsTo to define asynchronous one-to-one relationship
    # Same functionality as BelongsTo, but suitable for asynchronous environments
    author: ClassVar[AsyncBelongsTo['AsyncUser']] = AsyncBelongsTo(foreign_key='user_id', inverse_of='posts')

    # Return database table name, same as synchronous version
    @classmethod
    def table_name(cls) -> str:
        return 'posts'
```

## 2. Setup Database

In this step, we will configure database connections and create the necessary table structures. We will configure database backends separately for synchronous and asynchronous models.

> 💡 **AI Prompt Example**: "Should I use in-memory database or file database for development and testing? What are the pros and cons?"

```python
# Import database backend related modules
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig, AsyncSQLiteBackend
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

# Configure database connection for synchronous models
# Use in-memory database (:memory:), data will be lost when program ends, suitable for testing
sync_config = SQLiteConnectionConfig(database=':memory:')
# Configure SQLite backend for User model, Post model will share the same backend connection
User.configure(sync_config, SQLiteBackend)
Post.__backend__ = User.__backend__  # Share connection to ensure transaction consistency

# Configure database connection for asynchronous models
# Also use in-memory database
async_config = SQLiteConnectionConfig(database=':memory:')
# Configure asynchronous SQLite backend for AsyncUser model, AsyncPost model will share the same backend connection
AsyncUser.configure(async_config, AsyncSQLiteBackend)
AsyncPost.__backend__ = AsyncUser.__backend__  # Share connection to ensure transaction consistency

# Create database table structures
# Note: In production, use a migration tool. Here we use raw SQL for simplicity.

> 💡 **AI Prompt Example**: "How should I manage database schema changes in production? Are there recommended migration tools?"

# Define SQL structure for users table
# Includes UUID primary key, username, email, creation time, update time, and version number fields
schema_sql_users = """
CREATE TABLE users (
    id TEXT PRIMARY KEY,           -- UUID primary key
    username VARCHAR(50),          -- Username, maximum 50 characters
    email VARCHAR(100),            -- Email, maximum 100 characters
    created_at TEXT,               -- Creation time
    updated_at TEXT,               -- Update time
    version INTEGER DEFAULT 1      -- Version number, for optimistic locking
);
"""

# Define SQL structure for posts table
# Includes UUID primary key, title, content, foreign key, creation time, update time, and version number fields
schema_sql_posts = """
CREATE TABLE posts (
    id TEXT PRIMARY KEY,           -- UUID primary key
    title VARCHAR(200),            -- Title, maximum 200 characters
    content TEXT,                  -- Content, text type
    user_id TEXT,                  -- Foreign key, linking to id field of users table
    created_at TEXT,               -- Creation time
    updated_at TEXT,               -- Update time
    version INTEGER DEFAULT 1      -- Version number, for optimistic locking
);
"""

# Execute SQL statements to create tables
# Use ExecutionOptions to specify statement type as DDL (Data Definition Language)
User.backend().execute(schema_sql_users, options=ExecutionOptions(stmt_type=StatementType.DDL))
User.backend().execute(schema_sql_posts, options=ExecutionOptions(stmt_type=StatementType.DDL))
```

## 3. CRUD Operations

In this step, we will demonstrate basic Create, Read, Update, Delete (CRUD) operations, including both synchronous and asynchronous approaches.

### Synchronous Operations

Synchronous operations use traditional blocking calls, suitable for simple application scenarios.

> 💡 **AI Prompt Example**: "How to implement complex query conditions in rhosocial-activerecord? For example, finding articles published within a certain time period?"

```python
# Create - Create a new user
# Instantiate User object and call save() method to persist to database
alice = User(username="alice", email="alice@example.com")
# save() method executes INSERT operation and persists data to database
alice.save()

# Create related data - Create a new post and associate it with the user
# Use previously created user ID as foreign key
post = Post(title="Hello World", content="My first post", user_id=alice.id)
# save() method executes INSERT operation and persists data to database
post.save()

# Read - Find a single user by condition
# find_one() method finds the first matching record based on specified conditions
user = User.find_one({'username': 'alice'})
# Output the found username
print(f"Found user: {user.username}")

# Read related data - Get all posts of the user
# Note: Use method call syntax () to access relationships, this triggers database query
# posts() method executes SELECT operation to query all posts of this user
user_posts = user.posts()
print(f"User has {len(user_posts)} posts")

# Update - Modify user information
# Directly modify model attributes
user.email = "new_email@example.com"
# Call save() method to execute UPDATE operation and save changes to database
user.save()

# Delete - Delete post
# delete() method executes DELETE operation to remove record from database
post.delete()
```

### Asynchronous Operations

Asynchronous operations use non-blocking calls, suitable for high-concurrency application scenarios.

> 💡 **AI Prompt Example**: "What are the differences between async and sync operations in usage? When should async operations be used?"

```python
# Import asyncio module to support asynchronous operations
import asyncio

# Define asynchronous CRUD operations function
async def async_crud_operations():
    # Create - Create a new user
    # Use AsyncUser class to instantiate object
    bob = AsyncUser(username="bob", email="bob@example.com")
    # Use await keyword to wait for save() operation to complete
    # await ensures asynchronous operation completes before continuing execution
    await bob.save()

    # Create related data - Create a new post and associate it with the user
    post = AsyncPost(title="Async Hello World", content="My first async post", user_id=bob.id)
    # Use await keyword to wait for save() operation to complete
    await post.save()

    # Read - Find a single user by condition
    # Use await keyword to wait for find_one() operation to complete
    user = await AsyncUser.find_one({'username': 'bob'})
    print(f"Found async user: {user.username}")

    # Read related data - Get all posts of the user
    # Use await keyword to wait for posts() operation to complete
    # posts() method executes asynchronous SELECT operation to query all posts of this user
    user_posts = await user.posts()
    print(f"Async user has {len(user_posts)} posts")

    # Update - Modify user information
    # Directly modify model attributes (same as synchronous operation)
    user.email = "new_async_email@example.com"
    # Use await keyword to wait for save() operation to complete
    await user.save()

    # Delete - Delete post
    # Use await keyword to wait for delete() operation to complete
    await post.delete()

# Run asynchronous operations
# Uncomment the following line to execute asynchronous operations in actual applications
# asyncio.run(async_crud_operations())
```

## 4. Sync-Async Parity in Action

Notice how the synchronous and asynchronous implementations follow the same patterns, demonstrating the **Sync-Async Parity** principle:

> 💡 **AI Prompt Example**: "What is the Sync-Async Parity principle? Why is this principle important for development?"

*   **Method Signatures**: Both `User.save()` and `AsyncUser.save()` have the same parameters and return types (with the exception of `async`/`await`)
*   **Query Interface**: Both `User.find_one()` and `AsyncUser.find_one()` accept the same parameters
*   **Relation Handling**: Both synchronous and asynchronous relations work similarly
*   **Functionality**: Every feature available in the synchronous version is also available in the asynchronous version

This **Sync-Async Parity** allows you to seamlessly transition between synchronous and asynchronous contexts without learning different APIs or sacrificing functionality.

This simple example demonstrates the core workflow: Define -> Configure -> Interact, with both synchronous and asynchronous implementations showcasing the **Sync-Async Parity** principle.
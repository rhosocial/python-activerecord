"""
Chapter 3: Modeling Data - Example Code
Demonstrates core concepts:
1. Field Definitions & FieldProxy
2. Mixin Reusability (UUID, Timestamp, Custom ContentMixin)
3. Validation & Lifecycle Hooks
"""

import uuid
from typing import ClassVar, Annotated, Optional, List
from pydantic import Field, field_validator
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy, UseColumn
from rhosocial.activerecord.field import UUIDMixin, TimestampMixin
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

# --- Mixins ---

class ContentMixin(ActiveRecord):
    """Reusable content fields"""
    title: str = Field(..., min_length=1, max_length=200)
    content: str
    
    @property
    def summary(self) -> str:
        return self.content[:100] + "..." if len(self.content) > 100 else self.content

# --- Models ---

class User(UUIDMixin, TimestampMixin, ActiveRecord):
    """User Model"""
    username: str = Field(..., max_length=50)
    email: str
    is_active: bool = True
    
    # Mapping legacy database column name example
    legacy_id: Annotated[Optional[int], UseColumn("old_db_id")] = None

    # Type-safe query proxy
    c: ClassVar[FieldProxy] = FieldProxy()

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if "@" not in v:
            raise ValueError("Invalid email format")
        return v

    @classmethod
    def table_name(cls) -> str:
        return "users"

class Post(UUIDMixin, TimestampMixin, ContentMixin, ActiveRecord):
    """Post Model"""
    user_id: uuid.UUID  # Foreign Key
    views: int = 0
    reading_time: int = 0

    c: ClassVar[FieldProxy] = FieldProxy()

    @classmethod
    def table_name(cls) -> str:
        return "posts"

    def before_save(self):
        """Lifecycle Hook: Automatically calculate reading time"""
        word_count = len(self.content.split())
        self.reading_time = max(1, word_count // 200)
        super().before_save()

# --- Main Execution ---

def main():
    # 1. Configure Database (Use in-memory database)
    config = SQLiteConnectionConfig(database=':memory:')
    User.configure(config, SQLiteBackend)
    # Share the backend to ensure both models access the same in-memory database
    Post.__backend__ = User.backend()

    # 2. Create Tables (For demonstration only; use migration tools in production)
    backend = User.backend()
    backend.execute("""
        CREATE TABLE users (
            id TEXT PRIMARY KEY,
            username VARCHAR(50),
            email VARCHAR(100),
            is_active BOOLEAN,
            old_db_id INTEGER,
            created_at TEXT,
            updated_at TEXT,
            version INTEGER DEFAULT 1
        )
    """, options=ExecutionOptions(stmt_type=StatementType.DDL))
    backend.execute("""
        CREATE TABLE posts (
            id TEXT PRIMARY KEY,
            title VARCHAR(200),
            content TEXT,
            user_id TEXT,
            views INTEGER,
            reading_time INTEGER,
            created_at TEXT,
            updated_at TEXT,
            version INTEGER DEFAULT 1
        )
    """, options=ExecutionOptions(stmt_type=StatementType.DDL))

    # 3. Create User
    alice = User(username="alice", email="alice@example.com")
    alice.save()
    print(f"Created user: {alice.username} (ID: {alice.id})")

    # 4. Create Post (Triggering before_save)
    post = Post(
        title="Hello World",
        content="This is a long content " * 50,  # Simulating long content
        user_id=alice.id
    )
    post.save()
    print(f"Created post: {post.title}")
    print(f"Calculated reading time: {post.reading_time} min")

    # 5. Use FieldProxy for Querying
    found_user = User.find_one(User.c.username == 'alice')
    assert found_user.id == alice.id
    print("Successfully found user using FieldProxy")

if __name__ == "__main__":
    main()

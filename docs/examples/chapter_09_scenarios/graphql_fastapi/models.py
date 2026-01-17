import uuid
from typing import Optional, ClassVar

from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
from rhosocial.activerecord.field import UUIDMixin, TimestampMixin
from rhosocial.activerecord.relation import BelongsTo, HasMany


class User(UUIDMixin, TimestampMixin, ActiveRecord):
    username: str
    email: str
    
    # Field Proxy
    c: ClassVar[FieldProxy] = FieldProxy()
    
    # Relations
    posts: ClassVar[HasMany['Post']] = HasMany(foreign_key='user_id')
    comments: ClassVar[HasMany['Comment']] = HasMany(foreign_key='user_id')

    @classmethod
    def table_name(cls) -> str:
        return "users"


class Post(UUIDMixin, TimestampMixin, ActiveRecord):
    user_id: uuid.UUID
    title: str
    content: str
    
    # Relations
    user: ClassVar[BelongsTo['User']] = BelongsTo(foreign_key='user_id')
    comments: ClassVar[HasMany['Comment']] = HasMany(foreign_key='post_id')
    
    # Field Proxy
    c: ClassVar[FieldProxy] = FieldProxy()

    @classmethod
    def table_name(cls) -> str:
        return "posts"


class Comment(UUIDMixin, TimestampMixin, ActiveRecord):
    user_id: uuid.UUID
    post_id: uuid.UUID
    content: str
    
    # Field Proxy
    c: ClassVar[FieldProxy] = FieldProxy()
    
    # Relations
    user: ClassVar[BelongsTo['User']] = BelongsTo(foreign_key='user_id')
    post: ClassVar[BelongsTo['Post']] = BelongsTo(foreign_key='post_id')
    
    @classmethod
    def table_name(cls) -> str:
        return "comments"


def setup_database():
    """Initialize the database and create tables."""
    backend = SQLiteBackend(connection_config=SQLiteConnectionConfig(
        database="graphql_example.db",
        options={"check_same_thread": False}
    ))
    # Share the backend across models
    User.__backend__ = backend
    Post.__backend__ = backend
    Comment.__backend__ = backend
    
    # Simple table creation (in a real app, use migrations)
    with backend.connection as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                email TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                post_id TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(post_id) REFERENCES posts(id)
            )
        """)

def seed_data():
    """Seed some initial data."""
    if User.count() > 0:
        return

    alice = User(username="alice", email="alice@example.com")
    alice.save()
    
    bob = User(username="bob", email="bob@example.com")
    bob.save()
    
    post1 = Post(user_id=alice.id, title="Hello GraphQL", content="This is a post about GraphQL.")
    post1.save()
    
    post2 = Post(user_id=alice.id, title="FastAPI Integration", content="FastAPI + Graphene is cool.")
    post2.save()
    
    comment1 = Comment(user_id=bob.id, post_id=post1.id, content="Great post!")
    comment1.save()
    
    comment2 = Comment(user_id=alice.id, post_id=post1.id, content="Thanks Bob!")
    comment2.save()


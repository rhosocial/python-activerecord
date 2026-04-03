"""
Serialization Chapter: Example 3 - Related Data
Demonstrates core concepts:
1. Serializing with relationship data
2. Using computed properties for derived values
3. Nested serialization patterns
4. Manual serialization of relationships
"""

from datetime import datetime
from typing import Optional, ClassVar
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.relation import HasMany, BelongsTo
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType
import json

# --- Models ---

class User(ActiveRecord):
    """User model with posts relationship."""
    __table_name__ = "users"
    id: Optional[int] = None
    username: str
    email: str
    bio: Optional[str] = None
    created_at: Optional[datetime] = None

    # Relationships
    posts: ClassVar[HasMany['Post']] = HasMany(foreign_key='author_id')

    @property
    def display_name(self) -> str:
        """Computed property for display name."""
        return f"@{self.username}"


class Post(ActiveRecord):
    """Post model with author and comments relationships."""
    __table_name__ = "posts"
    id: Optional[int] = None
    author_id: int
    title: str
    content: str
    published: bool = False
    created_at: Optional[datetime] = None

    # Relationships
    author: ClassVar[BelongsTo['User']] = BelongsTo(foreign_key='author_id')
    comments: ClassVar[HasMany['Comment']] = HasMany(foreign_key='post_id')

    @property
    def excerpt(self) -> str:
        """Computed property for post excerpt."""
        return self.content[:50] + "..." if len(self.content) > 50 else self.content


class Comment(ActiveRecord):
    """Comment model."""
    __table_name__ = "comments"
    id: Optional[int] = None
    post_id: int
    author_name: str
    content: str
    created_at: Optional[datetime] = None

    # Relationships
    post: ClassVar[BelongsTo['Post']] = BelongsTo(foreign_key='post_id')

# --- Helper Functions ---

def print_json(data: dict, title: str = ""):
    """Pretty print JSON data."""
    if title:
        print(f"\n{title}:")
    print(json.dumps(data, indent=2, default=str))

# --- Main Execution ---

def main():
    print("=" * 60)
    print("Example 3: Related Data Serialization")
    print("=" * 60)

    # Configure database
    config = SQLiteConnectionConfig(database=':memory:')
    User.configure(config, SQLiteBackend)
    Post.configure(config, SQLiteBackend)
    Comment.configure(config, SQLiteBackend)

    # Create tables
    backend = User.backend()
    backend.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50),
            email VARCHAR(100),
            bio TEXT,
            created_at TIMESTAMP
        )
    """, options=ExecutionOptions(stmt_type=StatementType.DDL))

    post_backend = Post.backend()
    post_backend.execute("""
        CREATE TABLE posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author_id INTEGER,
            title VARCHAR(200),
            content TEXT,
            published BOOLEAN,
            created_at TIMESTAMP
        )
    """, options=ExecutionOptions(stmt_type=StatementType.DDL))

    comment_backend = Comment.backend()
    comment_backend.execute("""
        CREATE TABLE comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER,
            author_name VARCHAR(50),
            content TEXT,
            created_at TIMESTAMP
        )
    """, options=ExecutionOptions(stmt_type=StatementType.DDL))

    # Create test data
    user = User(
        username="alice",
        email="alice@example.com",
        bio="Software developer",
        created_at=datetime.now()
    )
    user.save()

    post1 = Post(
        author_id=user.id,
        title="First Post",
        content="This is my first post about Python and ActiveRecord patterns.",
        published=True,
        created_at=datetime.now()
    )
    post1.save()

    post2 = Post(
        author_id=user.id,
        title="Second Post",
        content="Today I want to share some thoughts about clean code practices.",
        published=True,
        created_at=datetime.now()
    )
    post2.save()

    # Add comments
    for i in range(3):
        Comment(
            post_id=post1.id,
            author_name=f"reader{i}",
            content=f"Great post #{i+1}!",
            created_at=datetime.now()
        ).save()

    # 1. Basic serialization (no relationships)
    print("\n" + "-" * 40)
    print("Basic serialization (no relationships):")
    print("-" * 40)

    user_data = user.model_dump()
    print(f"Keys: {list(user_data.keys())}")
    print("Note: 'posts' not included by default")

    # 2. Computed properties
    print("\n" + "-" * 40)
    print("Computed properties (manual inclusion):")
    print("-" * 40)

    user_data = user.model_dump()
    user_data['display_name'] = user.display_name  # Manually add computed property
    print(f"display_name: {user_data['display_name']}")

    post_data = post1.model_dump()
    post_data['excerpt'] = post1.excerpt  # Manually add computed property
    print("\nPost computed property:")
    print(f"excerpt: {post_data['excerpt']}")

    # 3. Manual relationship serialization
    print("\n" + "-" * 40)
    print("Manual relationship serialization:")
    print("-" * 40)

    def serialize_user_with_posts(user: User) -> dict:
        """Serialize user with their posts."""
        data = user.model_dump()
        data['posts'] = [p.model_dump() for p in user.posts()]
        return data

    user_with_posts = serialize_user_with_posts(user)
    print_json(user_with_posts, "User with posts")

    # 4. Nested serialization
    print("\n" + "-" * 40)
    print("Deep nested serialization:")
    print("-" * 40)

    def serialize_post_full(post: Post) -> dict:
        """Serialize post with author and comments."""
        data = post.model_dump()
        data['author'] = post.author().model_dump(include={'id', 'username', 'email'})
        data['comments'] = [c.model_dump() for c in post.comments()]
        return data

    post_full = serialize_post_full(post1)
    print_json(post_full, "Post with author and comments")

    # 5. API response pattern
    print("\n" + "-" * 40)
    print("API response patterns:")
    print("-" * 40)

    def user_summary(user: User) -> dict:
        """Lightweight user summary for lists."""
        data = user.model_dump(include={'id', 'username'})
        data['display_name'] = user.display_name  # Add computed property
        return data

    def post_summary(post: Post) -> dict:
        """Lightweight post summary for lists."""
        data = post.model_dump(include={'id', 'title', 'published', 'created_at'})
        data['excerpt'] = post.excerpt  # Add computed property
        data['author'] = user_summary(post.author())
        # Get comment count
        comments = list(post.comments())
        data['comment_count'] = len(comments)
        return data

    def user_detail(user: User) -> dict:
        """Full user detail with posts."""
        data = user.model_dump(exclude={'bio'})
        data['posts'] = [post_summary(p) for p in user.posts()]
        return data

    summary = user_summary(user)
    print_json(summary, "User summary")

    detail = user_detail(user)
    print_json(detail, "User detail with post summaries")

if __name__ == "__main__":
    main()

"""
Chapter 4: Relationships - Example Code
Demonstrates:
1. One-to-One (User <-> Profile)
2. One-to-Many (User <-> Post)
3. Many-to-Many (Post <-> Tag via PostTag)
4. Eager Loading (Solving N+1 Problem)
"""
import uuid
from typing import ClassVar, Optional, List
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.relation import HasOne, BelongsTo, HasMany
from rhosocial.activerecord.field import UUIDMixin, TimestampMixin
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

# --- Models ---

class User(UUIDMixin, TimestampMixin, ActiveRecord):
    username: str
    
    @classmethod
    def table_name(cls) -> str:
        return "users"
    
    # 1:1 Relationship
    profile: ClassVar[HasOne['Profile']] = HasOne(foreign_key='user_id', inverse_of='user')
    # 1:N Relationship
    posts: ClassVar[HasMany['Post']] = HasMany(foreign_key='user_id', inverse_of='author')

class Profile(UUIDMixin, TimestampMixin, ActiveRecord):
    user_id: uuid.UUID
    bio: str
    
    @classmethod
    def table_name(cls) -> str:
        return "profiles"
    
    # Inverse of 1:1
    user: ClassVar[BelongsTo['User']] = BelongsTo(foreign_key='user_id', inverse_of='profile')

class Post(UUIDMixin, TimestampMixin, ActiveRecord):
    user_id: uuid.UUID
    title: str
    content: str
    
    @classmethod
    def table_name(cls) -> str:
        return "posts"
    
    # Inverse of 1:N
    author: ClassVar[BelongsTo['User']] = BelongsTo(foreign_key='user_id', inverse_of='posts')
    
    # 1:N to Comments
    comments: ClassVar[HasMany['Comment']] = HasMany(foreign_key='post_id', inverse_of='post')
    
    # N:N to Tags (via intermediate model)
    post_tags: ClassVar[HasMany['PostTag']] = HasMany(foreign_key='post_id', inverse_of='post')

class Comment(UUIDMixin, TimestampMixin, ActiveRecord):
    post_id: uuid.UUID
    user_id: uuid.UUID
    body: str
    
    post: ClassVar[BelongsTo['Post']] = BelongsTo(foreign_key='post_id', inverse_of='comments')
    author: ClassVar[BelongsTo['User']] = BelongsTo(foreign_key='user_id') # No inverse defined on User for simplicity

class Tag(UUIDMixin, TimestampMixin, ActiveRecord):
    name: str
    
    @classmethod
    def table_name(cls) -> str:
        return "tags"
    
    post_tags: ClassVar[HasMany['PostTag']] = HasMany(foreign_key='tag_id', inverse_of='tag')

class PostTag(UUIDMixin, TimestampMixin, ActiveRecord):
    post_id: uuid.UUID
    tag_id: uuid.UUID
    
    @classmethod
    def table_name(cls) -> str:
        return "post_tags"
    
    post: ClassVar[BelongsTo['Post']] = BelongsTo(foreign_key='post_id', inverse_of='post_tags')
    tag: ClassVar[BelongsTo['Tag']] = BelongsTo(foreign_key='tag_id', inverse_of='post_tags')


def main():
    # 1. Setup Database
    config = SQLiteConnectionConfig(database=':memory:')
    User.configure(config, SQLiteBackend)
    
    # Share backend
    backend = User.backend()
    for model in [Profile, Post, Comment, Tag, PostTag]:
        model.__backend__ = backend
        
    # 2. Create Tables
    backend.execute("""
        CREATE TABLE users (id TEXT PRIMARY KEY, username TEXT, created_at INTEGER, updated_at INTEGER)
    """, options=ExecutionOptions(stmt_type=StatementType.DDL))
    backend.execute("""
        CREATE TABLE profiles (id TEXT PRIMARY KEY, user_id TEXT, bio TEXT, created_at INTEGER, updated_at INTEGER)
    """, options=ExecutionOptions(stmt_type=StatementType.DDL))
    backend.execute("""
        CREATE TABLE posts (id TEXT PRIMARY KEY, user_id TEXT, title TEXT, content TEXT, created_at INTEGER, updated_at INTEGER)
    """, options=ExecutionOptions(stmt_type=StatementType.DDL))
    backend.execute("""
        CREATE TABLE comments (id TEXT PRIMARY KEY, post_id TEXT, user_id TEXT, body TEXT, created_at INTEGER, updated_at INTEGER)
    """, options=ExecutionOptions(stmt_type=StatementType.DDL))
    backend.execute("""
        CREATE TABLE tags (id TEXT PRIMARY KEY, name TEXT, created_at INTEGER, updated_at INTEGER)
    """, options=ExecutionOptions(stmt_type=StatementType.DDL))
    backend.execute("""
        CREATE TABLE post_tags (id TEXT PRIMARY KEY, post_id TEXT, tag_id TEXT, created_at INTEGER, updated_at INTEGER)
    """, options=ExecutionOptions(stmt_type=StatementType.DDL))
    
    print("Tables created.")
    
    # 3. Create Data
    alice = User(username="alice")
    alice.save()
    
    profile = Profile(user_id=alice.id, bio="I love coding")
    profile.save()
    
    post1 = Post(user_id=alice.id, title="First Post", content="Hello World")
    post1.save()
    
    post2 = Post(user_id=alice.id, title="Second Post", content="Python is great")
    post2.save()
    
    tag_python = Tag(name="python")
    tag_python.save()
    
    PostTag(post_id=post2.id, tag_id=tag_python.id).save()
    
    # 4. Access Relationships
    
    # 1:1
    fetched_user = User.find_one(alice.id)
    if fetched_user:
        print(f"User: {fetched_user.username}")
        # Lazy load profile
        user_profile = fetched_user.profile()
        if user_profile:
            print(f"Bio: {user_profile.bio}")
        
    # 1:N
    if fetched_user:
        user_posts = fetched_user.posts()
        print(f"Posts count: {len(user_posts)}")
        for p in user_posts:
            print(f" - {p.title}")
        
    # N:M (Manual traversal)
    print("Tags for Post 2:")
    links = post2.post_tags()
    for link in links:
        t = link.tag() # N+1 if not careful
        if t:
            print(f" - {t.name}")
            
    # 5. Eager Loading (Solving N+1)
    print("\n--- Eager Loading ---")
    # Load User with Profile and Posts
    # Note: Currently supports with_('relation_name')
    users = User.query().with_('profile').with_('posts').all()
    
    for u in users:
        print(f"User: {u.username}")
        # These accessors should not trigger new queries if implementation supports it fully
        # (Note: Current implementation of with_ puts data in cache, relation descriptor checks cache)
        if u.profile():
            print(f"  Bio: {u.profile().bio}")
        print(f"  Posts: {len(u.posts())}")

if __name__ == "__main__":
    main()

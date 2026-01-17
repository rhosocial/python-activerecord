"""
Chapter 6: Performance - Example Code
Demonstrates:
1. Strict vs Raw Mode (Speed comparison)
2. Concurrency Control (Optimistic Locking)
3. Caching (Relation Cache)
"""
import time
import logging
import uuid
from typing import ClassVar, List
from rhosocial.activerecord import ActiveRecord, FieldProxy
from rhosocial.activerecord.field import OptimisticLockMixin, UUIDMixin, TimestampMixin
from rhosocial.activerecord.relation import HasMany, BelongsTo
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.backend.errors import StaleObjectError

# --- Models ---

class User(UUIDMixin, TimestampMixin, ActiveRecord):
    username: str
    
    c: ClassVar[FieldProxy] = FieldProxy()
    
    @classmethod
    def table_name(cls) -> str:
        return "users"
        
    posts: ClassVar[HasMany['Post']] = HasMany(foreign_key='user_id')

class Post(OptimisticLockMixin, UUIDMixin, TimestampMixin, ActiveRecord):
    user_id: uuid.UUID
    title: str
    content: str
    
    c: ClassVar[FieldProxy] = FieldProxy()
    
    @classmethod
    def table_name(cls) -> str:
        return "posts"
        
    author: ClassVar[BelongsTo['User']] = BelongsTo(foreign_key='user_id')

def setup_database():
    config = SQLiteConnectionConfig(database=':memory:')
    User.configure(config, SQLiteBackend)
    Post.__backend__ = User.backend()
    
    User.backend().execute("""
        CREATE TABLE users (id TEXT PRIMARY KEY, username TEXT, created_at INTEGER, updated_at INTEGER)
    """, options=ExecutionOptions(stmt_type=StatementType.DDL))
    
    Post.backend().execute("""
        CREATE TABLE posts (
            id TEXT PRIMARY KEY, 
            user_id TEXT, 
            title TEXT, 
            content TEXT, 
            version INTEGER DEFAULT 1,
            created_at INTEGER, 
            updated_at INTEGER
        )
    """, options=ExecutionOptions(stmt_type=StatementType.DDL))

def main():
    setup_database()
    
    print("--- 1. Strict vs Raw Mode ---")
    
    # Seed data
    print("Seeding 1000 users...")
    users_to_create = [User(username=f"user_{i}") for i in range(1000)]
    # Batch save would be better, but loop is fine for demonstration
    for u in users_to_create:
        u.save()
        
    # Benchmark Strict
    start = time.time()
    users_strict = User.query().all()
    strict_time = time.time() - start
    print(f"Strict Mode (Pydantic objects): {strict_time:.4f}s")
    print(f"Count: {len(users_strict)}")
    
    # Benchmark Raw
    start = time.time()
    users_raw = User.query().aggregate()
    raw_time = time.time() - start
    print(f"Raw Mode (Dictionaries): {raw_time:.4f}s")
    print(f"Count: {len(users_raw)}")
    
    if strict_time > 0:
        print(f"Speedup: {strict_time / raw_time:.2f}x")
        
    print("\n--- 2. Concurrency Control (Optimistic Locking) ---")
    
    user = users_strict[0]
    post = Post(user_id=user.id, title="Original Title", content="Content")
    post.save()
    print(f"Post created with version: {post.version}")
    
    # Simulate two users fetching the same post
    post_user1 = Post.find_one_or_fail(post.id)
    post_user2 = Post.find_one_or_fail(post.id)
    
    print(f"User 1 fetches post (v{post_user1.version})")
    print(f"User 2 fetches post (v{post_user2.version})")
    
    # User 1 updates
    post_user1.title = "Title by User 1"
    post_user1.save()
    print(f"User 1 updated post. New version: {post_user1.version}")
    
    # User 2 tries to update
    print("User 2 attempting update...")
    try:
        post_user2.title = "Title by User 2"
        post_user2.save()
    except StaleObjectError:
        print("Success! StaleObjectError caught. User 2's update was prevented.")
        print("User 2 should refresh the data.")
        
    print("\n--- 3. Caching ---")
    
    # First access - triggers query
    print("Accessing user.posts (1st time)...")
    posts1 = user.posts()
    print(f"Got {len(posts1)} posts.")
    
    # Create a new post directly in DB (bypass relation to test cache)
    Post(user_id=user.id, title="Hidden Post", content="...").save()
    
    # Second access - should return cached result (1 post) not 2
    print("Accessing user.posts (2nd time)...")
    posts2 = user.posts()
    print(f"Got {len(posts2)} posts. (Should be same as before due to cache)")
    
    # Clear cache
    print("Clearing cache...")
    user.clear_relation_cache('posts')
    
    # Third access - triggers query
    print("Accessing user.posts (3rd time)...")
    posts3 = user.posts()
    print(f"Got {len(posts3)} posts. (Should be updated)")

if __name__ == "__main__":
    main()

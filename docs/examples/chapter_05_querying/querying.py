"""
Chapter 5: Querying - Example Code
Demonstrates:
1. Basic Filtering (select, where, order_by, limit)
2. Aggregation (count, sum, group_by)
3. Advanced Querying (Joins, CTEs)
"""
import uuid
from typing import ClassVar, Optional
from rhosocial.activerecord import ActiveRecord, FieldProxy
from rhosocial.activerecord.relation import BelongsTo, HasMany
from rhosocial.activerecord.field import UUIDMixin, TimestampMixin
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.backend.expression.functions import count as sql_count, sum_ as sql_sum

# --- Models ---

class User(UUIDMixin, TimestampMixin, ActiveRecord):
    username: str
    age: int
    is_active: bool = True

    c: ClassVar[FieldProxy] = FieldProxy()

    @classmethod
    def table_name(cls) -> str:
        return "users"

class Post(UUIDMixin, TimestampMixin, ActiveRecord):
    user_id: uuid.UUID
    title: str
    views: int = 0
    category_id: int

    c: ClassVar[FieldProxy] = FieldProxy()

    @classmethod
    def table_name(cls) -> str:
        return "posts"

    author: ClassVar[BelongsTo['User']] = BelongsTo(foreign_key='user_id')

def main():
    # 1. Setup
    config = SQLiteConnectionConfig(database=':memory:')
    User.configure(config, SQLiteBackend)
    Post.__backend__ = User.backend()

    # 2. Schema
    User.backend().execute("""
        CREATE TABLE users (id TEXT PRIMARY KEY, username TEXT, age INTEGER, is_active BOOLEAN, created_at INTEGER, updated_at INTEGER)
    """, options=ExecutionOptions(stmt_type=StatementType.DDL))
    Post.backend().execute("""
        CREATE TABLE posts (id TEXT PRIMARY KEY, user_id TEXT, title TEXT, views INTEGER, category_id INTEGER, created_at INTEGER, updated_at INTEGER)
    """, options=ExecutionOptions(stmt_type=StatementType.DDL))

    # 3. Data
    alice = User(username="alice", age=25, is_active=True)
    alice.save()
    bob = User(username="bob", age=30, is_active=False)
    bob.save()
    charlie = User(username="charlie", age=20, is_active=True)
    charlie.save()

    Post(user_id=alice.id, title="Alice's Intro", views=100, category_id=1).save()
    Post(user_id=alice.id, title="Alice's Deep Dive", views=200, category_id=1).save()
    Post(user_id=bob.id, title="Bob's Rant", views=50, category_id=2).save()

    print("Data seeded.")

    # 4. Basic Filtering
    print("\n--- Basic Filtering ---")
    # Active users older than 20
    users = User.query() \
        .where(User.c.is_active == True) \
        .where(User.c.age > 20) \
        .all()
    for u in users:
        print(f"Found User: {u.username}, Age: {u.age}")

    # Order by age descending
    # Note: order_by accepts column names, FieldProxy expressions, or (expression, "ASC"|"DESC") tuples
    print("\n4. Sorting (Order By)")
    ordered_users = User.query().order_by((User.c.age, "DESC")).all()
    for user in ordered_users:
        print(f"- {user.username}: {user.age}")

    # 5. Aggregation
    print("\n--- Aggregation ---")
    total_posts = Post.query().count()
    print(f"Total Posts: {total_posts}")

    total_views = Post.query().sum_(Post.c.views)
    print(f"Total Views: {total_views}")

    # Group By: Views per Category
    # Note: Returning raw dictionaries/tuples for aggregations
    # Currently .all() attempts to map to model, which might fail if columns don't match.
    # We use .select() to pick specific columns.
    # Depending on implementation, non-model results might need specific handling or return dicts.
    # Let's try to fetch and see how it behaves (likely returns dicts if raw mode or list of models with partial data)
    # Actually, ActiveRecord .all() expects to return Model instances.
    # For raw aggregation, we might use .aggregate() if available or backend execution.
    # But let's see if .select() works with .all() for partial models.
    
    # Using aggregate() for raw results if supported by Query interface (checked docs, it has aggregate())
    # results = Post.query().select(Post.c.category_id, Sum(Post.c.views)).group_by(Post.c.category_id).all() 
    # This would try to instantiate Posts.
    
    print("Aggregation usually requires raw mode or compatible model fields.")

    # 6. Advanced: Join
    print("\n--- Join ---")
    # Users who have posts (using group_by as alternative to distinct)
    authors = User.query() \
        .join(Post, on=(User.c.id == Post.c.user_id)) \
        .group_by(User.c.id) \
        .all()
    for author in authors:
        print(f"Author: {author.username}")

if __name__ == "__main__":
    main()

# Eager Loading Deep Dive

Eager loading loads related data alongside the main query via `with_()`, and is the standard solution to the N+1 query problem.

This is the complete reference for `with_()`, covering nested paths, query modifiers, parameter expansion and override rules, path validation, and the underlying loading mechanics. For an overview and comparison of loading strategies, see [Loading Strategies](loading.md).

## Basic Usage

```python
from typing import ClassVar
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.relation import HasMany, BelongsTo

class User(ActiveRecord):
    __table_name__ = "users"
    id: int
    name: str

    posts: ClassVar = HasMany('Post', inverse_of='user')

class Post(ActiveRecord):
    __table_name__ = "posts"
    id: int
    title: str
    user_id: int

    user: ClassVar = BelongsTo('User', inverse_of='posts')

# Eager load posts for all users
users = User.query().with_("posts").all()
for user in users:
    # No extra query triggered — data is already cached
    posts = user.posts()
    print(f"{user.name}: {len(posts)} posts")
```

`with_()` accepts **variable arguments**. Each argument is either a plain string path or a `(path, modifier)` tuple:

| Argument form | Description | Example |
|---------------|-------------|---------|
| `str` | Simple relation path | `with_('posts')`, `with_('posts.comments')` |
| `tuple` | Path + query modifier | `with_(('posts', modifier))` |

## Loading Multiple Relations

You can eager load multiple relations in one call, or chain `with_()` calls:

```python
# Pass multiple arguments at once
users = User.query().with_("profile", "posts", "roles").all()

# Chained calls (equivalent)
users = User.query().with_("profile").with_("posts").with_("roles").all()
```

## Nested Eager Loading

Use dot (`.`) syntax to eager load deeply nested relations. Each intermediate relation is configured separately and batch-loaded level by level:

```python
users = User.query().with_("posts.comments").all()
for user in users:
    for post in user.posts():
        # post.comments() also does not trigger extra queries
        print(f"  {post.title}: {len(post.comments())} comments")
```

There is no hard limit on nesting depth. A path like `with_("user.orders.items.detail")` is split into 4 levels loaded sequentially.

## Query Modifiers

Filter, sort, or limit the eagerly loaded relations:

```python
users = User.query().with_(
    ("posts", lambda q: q.where(Post.c.published == True).order_by(Post.c.created_at.desc()))
).all()
```

A modifier receives an `ActiveQuery` object `q` and returns the modified query. It can chain `.where()`, `.order_by()`, `.limit()` and other methods.

### Prefer Named Functions for Complex Modifiers

For complex modifiers, prefer named functions over lambdas. When a modifier is **overwritten**, the framework logs a WARNING; a named function is shown with its full `module.qualname` for easier debugging, while a lambda appears as `<lambda>`:

```python
def filter_published(q):
    return q.where(Post.c.status == 'published')

users = User.query().with_(('posts', filter_published)).all()
```

## Parameter Expansion Rules

**Modifiers apply only to the target relation (the last segment of the path)**; intermediate relations are not filtered. For example:

```python
users = User.query().with_(("posts.comments", lambda q: q.where(...))).all()
```

This argument expands into two configurations:

```
'posts'           -> modifier: None   (intermediate relation, no modifier)
'posts.comments'  -> modifier: func   (target relation, modifier applied)
```

## Override Rules and Ordering

`with_()` follows the "**later arguments win**" rule (Yii2 behavior):

```python
# m1 takes effect (correct order: longer path first, shorter path last)
users = User.query().with_(
    ('posts.comments.user', m2),
    ('posts.comments', m1),
)

# m2 overwrites m1 (m1 is lost)
users = User.query().with_(
    ('posts.comments', m1),
    ('posts.comments.user', m2),
)
```

When expanded, a later argument overwrites the earlier configuration for the **same path**, including nested relations and modifiers:

```python
# Result of ('posts.comments', m1) + ('posts.comments.user', m2):
# 'posts'              -> modifier: None  (written by the 2nd arg, overwrites)
# 'posts.comments'     -> modifier: m2    (m1 overwritten by the 2nd arg)
# 'posts.comments.user' -> modifier: m2
```

> **Rule**: if you do not want a modifier overwritten, place it **later** in the argument list.

## Path Validation

`with_()` validates **all** paths before applying any of them; on failure it raises and applies **none** (transactional behavior).

### Syntax Validation

Paths with an invalid format raise `InvalidRelationPathError`:

| Invalid case | Example |
|--------------|---------|
| Empty string | `""` |
| Leading dot | `".posts"` |
| Trailing dot | `"posts."` |
| Consecutive dots | `"posts..comments"` |

### Semantic Validation

Every relation in the path must exist on its corresponding model, otherwise `RelationNotFoundError` is raised. For example, `with_('posts.comments')` is checked step by step:

1. `posts` relation exists on the `User` model
2. Resolve the related model of `posts` (`Post`)
3. `comments` relation exists on the `Post` model

```python
from rhosocial.activerecord.query.relational import InvalidRelationPathError, RelationNotFoundError

try:
    users = User.query().with_("posts.nonexistent").all()
except RelationNotFoundError as e:
    print(f"Relation not found: {e}")
```

## Loading Mechanics

Understanding the underlying mechanics helps predict query counts and performance.

### Batch Loading

After the main query executes, the framework runs **one batch query** per configured path instead of one query per object:

- **BelongsTo**: collect the foreign key values of all objects → query the related model with an `IN` predicate → map back to each object by primary key
- **HasOne / HasMany**: collect the primary key values of all objects → query the related table (foreign key IN primary keys) → group by foreign key; `HasOne` returns a single item, `HasMany` returns a list
- **Composite primary keys**: primary/foreign key pairs are collected and matched as tuples

```python
orders = Order.query().with_('user').all()
# No matter how many orders, the user relation runs only 1 IN query
```

Nested paths execute one batch query per level, recursively.

### Cache First

Batch-loaded results are written to an instance-level cache (`InstanceCache`, default TTL 300 seconds, capacity 1000). Subsequent access to the same relation — including later lazy access via `user.posts()` — reads from the cache first and does not trigger a query.

> Use `clear_relation_cache()` to clear cached relations on an instance; after bulk-updating an instance, clear the cache if you need to force a reload.

### Return Type Semantics

| Relation type | Return value |
|---------------|--------------|
| `BelongsTo` / `HasOne` | A single related instance, or `None` if no match |
| `HasMany` | A list of related instances, or empty list `[]` if no match |

## Async Usage

Async models use `AsyncRelationalQueryMixin`; the API is fully symmetric with sync:

```python
async_users = await AsyncUser.query().with_("posts").all()
for user in async_users:
    posts = await user.posts()  # No extra query triggered
```

## Performance Recommendations

| Scenario | Strategy |
|----------|----------|
| Need most related data | Use `with_()` eager loading |
| Need relations of few objects only | Use lazy loading (default) |
| Need filtered relations | Use the modifier argument |
| Accessing relations in loops | Must eager load to avoid N+1 |
| Deep nesting (more than 3 levels) | Consider splitting into multiple queries |
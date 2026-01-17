# Advanced Features

## Joins

Explicitly join other tables.

```python
# Find all users who have published posts
users = User.query() \
    .join(Post, on=(User.c.id == Post.c.user_id)) \
    .group_by(User.c.id) \
    .all()
```

## CTE (Common Table Expressions)

For complex queries, CTEs can make logic clearer.

```python
from rhosocial.activerecord.query import CTEQuery

# Define CTE: Find recently active users
recent_users_cte = User.query().where(User.c.last_login > '2023-01-01')

# Use CTE
query = CTEQuery(User.backend()) \
    .with_cte('recent_users', recent_users_cte) \
    .query(
        User.query().join('recent_users', on='users.id = recent_users.id')
    )

results = query.aggregate()
```

## Window Functions

Requires backend support (SQLite 3.25+).

```python
from rhosocial.activerecord.backend.expression.window import Window, Rank

# Rank posts by views within each category
window = Window.partition_by(Post.c.category_id).order_by((Post.c.views, "DESC"))
rank_col = Rank().over(window).as_('rank')

results = Post.query().select(Post.c.title, rank_col).aggregate()
```

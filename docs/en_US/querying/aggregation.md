# Aggregation

## Basic Functions

Standard SQL aggregation functions are supported: `count`, `sum_`, `avg`, `min_`, `max_`.

```python
# Count total users
total = User.query().count()

# Calculate total views of all posts
total_views = Post.query().sum_(Post.c.views)
```

## Group By

Count posts for each user:

```python
from rhosocial.activerecord.backend.expression import functions

# SELECT user_id, COUNT(*) FROM posts GROUP BY user_id
results = Post.query() \
    .select(Post.c.user_id, functions.count('*')) \
    .group_by(Post.c.user_id) \
    .aggregate()
```

> **Note**: Group by queries usually return dictionaries or tuples, rather than model instances, unless the results can be fully mapped back to the model.

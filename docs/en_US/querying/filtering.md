# Basic Filtering (Filtering & Sorting)

## Starting a Query

Each model has a `query()` method (or `find()` / `find_all()` class methods).

```python
# Get query object
q = User.query()
```

## Filtering (Where)

Supports method chaining. Using `Model.c.field` for type-safe comparisons is recommended.

```python
# Find all active users older than 18
users = User.query() \
    .where(User.c.is_active == True) \
    .where(User.c.age > 18) \
    .all()
```

Dictionary style (implicit AND) is also supported:

```python
users = User.find_all({'is_active': True, 'age': 20})
```

## Sorting (Order By)

```python
# Order by created_at descending
posts = Post.query().order_by((Post.c.created_at, "DESC")).all()
```

## Pagination (Limit & Offset)

```python
# Get page 2, 20 items per page
posts = Post.query().limit(20).offset(20).all()
```

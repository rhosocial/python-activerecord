# Loading Strategies

## The N+1 Query Problem

When you iterate through a list and access its relationships, it may trigger a massive amount of database queries.

```python
users = User.find_all()  # 1 query
for user in users:
    print(user.profile().bio)  # N queries!
```

This is the famous N+1 problem.

## Eager Loading

Using the `with_()` method allows you to load related data alongside the main query.

```python
# Tell the ORM we need to load profile as well
users = User.query().with_('profile').all()

for user in users:
    # No more DB query triggered here, reading directly from cache
    print(user.profile().bio)
```

## Lazy Loading

By default, relationships are lazily loaded. SQL is executed only when you call the relationship method (like `user.profile()`). This is more efficient for scenarios where you don't need to access all related data.

## Batch Loading

Even without `with_`, some advanced loaders support automatically batch loading relationships for all other elements in the list when accessing the relationship of the first element (This library currently does not enable this by default, mainly relying on `with_`).

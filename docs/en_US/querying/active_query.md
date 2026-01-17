# ActiveQuery (Model Query)

`ActiveQuery` is the most commonly used query object in `rhosocial-activerecord`, designed for querying and manipulating `ActiveRecord` models. It provides rich query capabilities by mixing in several functionality modules.

By default, `ActiveQuery` returns model instances.

## BaseQueryMixin (Basic Building Blocks)

Provides the basic building blocks for SQL queries.

### `select(*columns)`

Specify columns to select. If not specified, selects all columns (`SELECT *`).

*   **Usage Examples**:

```python
# Select all columns
users = User.query().all()

# Select specific columns
users = User.query().select(User.c.id, User.c.name).all()

# Use alias (as_)
users = User.query().select(User.c.name.as_("username"), User.c.email).all()
```

*   **Notes**:
    *   If only a subset of columns is selected, unselected fields in the returned model instances will be default values or `None` (depending on model definition).
    *   In strict mode, if subsequent logic relies on unselected fields, errors may occur.

### `where(condition)`

Add filtering conditions (AND logic).

*   **Usage Examples**:

```python
# Simple condition
User.query().where(User.c.id == 1)

# Combined conditions (AND)
User.query().where((User.c.age >= 18) & (User.c.is_active == True))

# Combined conditions (OR) - Note: Must use | operator
User.query().where((User.c.role == 'admin') | (User.c.role == 'moderator'))

# Dictionary arguments (Automatically treated as AND)
User.query().where({"name": "Alice", "age": 25})
```

*   **Notes**:
    *   **Precedence Issue**: When using `&` (AND) and `|` (OR), **always use parentheses** around each sub-condition, as bitwise operators have higher precedence in Python.
    *   **None Handling**: If dictionary arguments contain `None`, it is automatically converted to `IS NULL` check.

### `order_by(*columns)`

Specify sort order.

*   **Usage Examples**:

```python
# Single column ascending
User.query().order_by(User.c.created_at)

# Multiple columns (First by role ascending, then by age descending)
User.query().order_by(User.c.role, (User.c.age, "DESC"))
```

### `limit(limit, offset=None)` / `offset(offset)`

Pagination query.

*   **Usage Examples**:

```python
# Get first 10 records
User.query().limit(10)

# Skip first 20, take 10 (i.e., Page 3)
User.query().limit(10, offset=20)
# Or
User.query().offset(20).limit(10)
```

### `group_by(*columns)` / `having(condition)`

Group statistics.

*   **Usage Examples**:

```python
# Count users per role
# SELECT role, COUNT(*) FROM users GROUP BY role HAVING COUNT(*) > 5
User.query() \
    .select(User.c.role, func.count().as_("count")) \
    .group_by(User.c.role) \
    .having(func.count() > 5) \
    .aggregate()
```

### `distinct(enable=True)`

Remove duplicate rows.

```python
# Get all distinct roles
User.query().select(User.c.role).distinct().all()
```

### `explain()`

Get query execution plan for performance analysis.

```python
plan = User.query().where(User.c.id == 1).explain()
print(plan)
```

### Window Functions

The `select` method supports Window Functions.

```python
from rhosocial.activerecord.backend.expression.window import Window, Rank

# Rank posts by views within each category
window = Window.partition_by(Post.c.category_id).order_by((Post.c.views, "DESC"))
rank_col = Rank().over(window).as_('rank')

results = Post.query().select(Post.c.title, rank_col).aggregate()
```

## JoinQueryMixin (Join Query)

Provides multi-table join capabilities.

*   `join(target, on=None, alias=None)`: Inner join (INNER JOIN).
*   `left_join(target, on=None, alias=None)`: Left outer join (LEFT JOIN).
*   `right_join(target, on=None, alias=None)`: Right outer join (RIGHT JOIN).
*   `full_join(target, on=None, alias=None)`: Full outer join (FULL JOIN).
*   `cross_join(target, alias=None)`: Cross join (CROSS JOIN).

*   **Usage Examples**:

```python
# Inner Join: Find users who have published posts
User.query().join(Post, on=(User.c.id == Post.c.user_id))

# Left Join: Find all users and their posts (if any)
User.query().left_join(Post, on=(User.c.id == Post.c.user_id))

# Aliased Join (Self Join)
# Find employees and their managers
Manager = User.c.with_table_alias("manager")
User.query().join(User, on=(User.c.manager_id == Manager.id), alias="manager")
```

*   **Notes**:
    *   When referencing columns in join queries, it is recommended to explicitly specify the table name (e.g., `User.c.id`) to avoid ambiguity.
    *   When using aliases, ensure `on` conditions reference columns from the aliased object.

## AggregateQueryMixin (Aggregation)

Provides data statistics and aggregation capabilities.

### Simple Aggregation
Returns scalar values directly.

*   `count(column=None)`: Count rows.
*   `sum(column)`: Calculate sum.
*   `avg(column)`: Calculate average.
*   `min(column)`: Find minimum value.
*   `max(column)`: Find maximum value.

### Complex Aggregation
*   `aggregate(**kwargs)`: Execute complex aggregation queries, returning a dictionary.

*   **Usage Examples**:

```python
# Simple stats
total_users = User.query().count()
max_age = User.query().max(User.c.age)

# Complex aggregation: Calculate total score and average score simultaneously
stats = User.query().aggregate(
    total_score=User.c.score.sum(),
    avg_score=User.c.score.avg()
)
# Returns: {'total_score': 1000, 'avg_score': 85.5}
```

## RangeQueryMixin (Range & Convenience Filtering)

Provides common convenience filtering methods, which are internally converted to `where` conditions.

*   `in_list(column, values)`: `IN` query.
*   `not_in(column, values)`: `NOT IN` query.
*   `between(column, start, end)`: `BETWEEN` query.
*   `not_between(column, start, end)`: `NOT BETWEEN` query.
*   `like(column, pattern)` / `not_like(...)`: Case-sensitive pattern matching.
*   `ilike(column, pattern)` / `not_ilike(...)`: Case-insensitive pattern matching.
*   `is_null(column)` / `is_not_null(column)`: NULL check.

*   **Usage Examples**:

```python
# ID in list
User.query().in_list(User.c.id, [1, 2, 3])

# Name starts with "A"
User.query().like(User.c.name, "A%")

# Age between 20 and 30
User.query().between(User.c.age, 20, 30)
```

*   **Notes**:
    *   `like` and `ilike` require manually including wildcards `%` or `_` in the pattern.
    *   `in_list` with an empty list may generate a `FALSE` condition (depending on dialect).

## RelationalQueryMixin (Eager Loading)

Provides relationship eager loading capabilities to solve the N+1 query problem.

*   `with_(*relations)`: Eager load relationships.
*   `includes(*relations)`: Alias for `with_`.

*   **Usage Examples**:

```python
# Eager load user's posts
users = User.query().with_("posts").all()

for user in users:
    # No extra SQL query triggered here
    print(len(user.posts)) 

# Nested eager loading: User's posts, and comments of posts
User.query().with_("posts", "posts.comments").all()
```

*   **Notes**:
    *   Relation names must match `HasOne`, `HasMany`, `BelongsTo` field names defined in the model.
    *   Filtering on eager loaded relations (e.g., `with_("posts", lambda q: q.where(...))`) is currently not supported.

## Set Operation Initiation

`ActiveQuery` can serve as the left operand for set operations.

*   `union(other)`: Initiate a UNION operation.
*   `intersect(other)`: Initiate an INTERSECT operation.
*   `except_(other)`: Initiate an EXCEPT operation.

## Execution Methods

These methods trigger database queries and return results.

*   `all() -> List[Model]`: Return a list of all matching model instances.
*   `one() -> Optional[Model]`: Return the first matching record, or None if none found.
*   `one_or_fail() -> Model`: Return the first matching record, or raise `RecordNotFound`.
*   `first() -> Optional[Model]`: Alias for `one()`.
*   `exists() -> bool`: Check if matching records exist.
*   `scalar() -> Any`: Return the value of the first column of the first row (useful for aggregations).
*   `to_sql() -> Tuple[str, List[Any]]`: Return the generated SQL statement and parameters (does not execute query).

*   **Debugging Tips**:
    *   Call `to_sql()` before `all()` or `one()` to inspect the generated SQL, which is very helpful for troubleshooting.

```python
sql, params = User.query().where(User.c.id == 1).to_sql()
print(sql, params)
# SELECT * FROM users WHERE id = ? [1]
```

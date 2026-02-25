# Query Cheatsheet

A quick reference for common query patterns in rhosocial-activerecord.

> 💡 **AI Prompt:** "Show me common SQL query patterns and how to write them using rhosocial-activerecord ActiveQuery, including filtering, sorting, pagination, and aggregation."

---

## Prerequisites: FieldProxy

All examples below use `User.c.field_name` syntax, where `c` is a **user-defined** `FieldProxy` instance. This is not built-in—you must define it yourself in your model:

```python
from typing import ClassVar
from rhosocial.activerecord.base import FieldProxy

class User(ActiveRecord):
    # Define your own field proxy (can be any name, 'c' is just a convention)
    c: ClassVar[FieldProxy] = FieldProxy()
    
    id: int
    name: str
    email: str
```

You can name it anything (`c`, `fields`, `col`, etc.). All examples in this document assume you've defined it as `c`.

**Why can FieldProxy fields support comparisons and operations?**

When you access a field via `User.c.name`, the FieldProxy returns a `Column` expression object. This object inherits from multiple Mixin classes that implement Python operator overloading:

- **ComparisonMixin**: Implements `==`, `!=`, `>`, `<`, `>=`, `<=` operators → returns comparison predicates
- **StringMixin**: Implements `.like()`, `.ilike()`, `.length()`, `.lower()`, `.upper()` methods → only available on string fields
- **ArithmeticMixin**: Implements `+`, `-`, `*`, `/` operators → for numeric calculations
- **LogicalMixin**: Implements `&` (AND), `|` (OR), `~` (NOT) operators → for combining conditions

These Mixins are only mixed into the `Column` class for field types that support them. For example, `StringMixin` is only available for `str` fields—so calling `.like()` on a numeric field will raise an error.

> 🔮 **Future Enhancement**: FieldProxy will also support backend-specific field types. When you define a field using PostgreSQL-specific types (e.g., from `rhosocial-activerecord-postgres`), additional operations will become available:
> - PostgreSQL's `VARCHAR` fields support `.ilike()` (case-insensitive LIKE)
> - Geometric types (POINT, POLYGON, etc.) support spatial operations (distance, containment, etc.)
> - JSON/JSONB types support `.json_extract()`, `.json_path()` operations
> - See [rhosocial-activerecord-postgres](https://github.com/rhosocial/python-activerecord-postgres) documentation for details.

---

## Field Types and Available Operations

Different field types support different operations. This is because the FieldProxy returns different expression types based on the field's Python type:

| Field Type | Available Operations |
|------------|---------------------|
| **All types** | `==`, `!=`, `.in_()`, `.not_in()`, `.is_null()`, `.is_not_null()` |
| **String (`str`)** | `.like()`, `.ilike()`, `.not_like()`, `.not_ilike()`, `.length()`, `.lower()`, `.upper()` |
| **Numeric (`int`, `float`)** | `>`, `<`, `>=`, `<=`, BETWEEN operations |
| **DateTime** | `>`, `<`, `>=`, `<=`, date range operations |

```python
# All fields: equality checks
users = User.query().where(User.c.name == 'John').all()
users = User.query().where(User.c.id.in_([1, 2, 3])).all()

# String fields: LIKE patterns (numeric fields don't support this!)
users = User.query().where(User.c.name.like('%John%')).all()
users = User.query().where(User.c.email.ilike('%@GMAIL.COM')).all()

# Numeric fields: comparisons (string fields can't do this!)
users = User.query().where(User.c.age >= 18).all()
users = User.query().where((User.c.score >= 0) & (User.c.score <= 100)).all()
```

---

## Comparison Operators

| SQL Pattern | rhosocial-activerecord | Example |
|-------------|------------------------|---------|
| `=` (equal) | `==` | `User.c.name == 'John'` |
| `!=` (not equal) | `!=` | `User.c.status != 'deleted'` |
| `>` (greater than) | `>` | `User.c.age > 18` |
| `<` (less than) | `<` | `User.c.created_at < datetime.now()` |
| `>=` (greater or equal) | `>=` | `User.c.score >= 100` |
| `<=` (less or equal) | `<=` | `User.c.age <= 65` |

```python
# Equal
users = User.query().where(User.c.name == 'John').all()

# Not equal
users = User.query().where(User.c.status != 'inactive').all()

# Range queries (chain multiple .where() for AND - recommended)
users = User.query().where(User.c.age >= 18).where(User.c.age <= 65).all()

# Or use & operator for AND
users = User.query().where(
    (User.c.age >= 18) & (User.c.age <= 65)
).all()
```

---

## IN and NOT IN

```python
# IN - Match any value in a list
user_ids = [1, 2, 3, 4, 5]
users = User.query().where(User.c.id.in_(user_ids)).all()

# NOT IN - Exclude values
banned_ids = [99, 100]
users = User.query().where(User.c.id.not_in(banned_ids)).all()
```

---

## LIKE and Pattern Matching

```python
# Contains (LIKE '%text%')
users = User.query().where(User.c.name.like('%John%')).all()

# Starts with (LIKE 'text%')
users = User.query().where(User.c.email.like('admin@%')).all()

# Ends with (LIKE '%text')
users = User.query().where(User.c.name.like('%Smith')).all()

# Case-insensitive pattern matching
users = User.query().where(User.c.name.ilike('%john%')).all()
```

---

## NULL Checks

```python
# IS NULL - Find records with NULL values
users = User.query().where(User.c.phone == None).all()

# IS NOT NULL - Find records with values
users = User.query().where(User.c.phone != None).all()

# Alternative using FieldProxy methods
users = User.query().where(User.c.phone.is_(None)).all()
users = User.query().where(User.c.phone.is_not(None)).all()
```

---

## Logical Operators (AND, OR, NOT)

Use Python bitwise operators for logical combinations. **Important**: Always use parentheses around each condition due to operator precedence.

```python
# AND - All conditions must be true (& operator)
users = User.query().where(
    (User.c.age >= 18) & (User.c.status == 'active')
).all()

# OR - Any condition can be true (| operator)
users = User.query().where(
    (User.c.role == 'admin') | (User.c.role == 'moderator')
).all()

# NOT - Negate a condition (~ operator)
users = User.query().where(
    ~(User.c.status == 'banned')
).all()

# Complex combinations
users = User.query().where(
    (User.c.age >= 18) & 
    ((User.c.role == 'admin') | (User.c.is_verified == True))
).all()
```

> ⚠️ **Critical**: Python's bitwise operators `&` and `|` have higher precedence than comparison operators. **Always wrap each condition in parentheses**, or you'll get unexpected results:
> ```python
> # ❌ WRONG: This will fail
> User.query().where(User.c.age >= 18 & User.c.is_active == True)
> 
> # ✅ CORRECT: Wrap each condition
> User.query().where((User.c.age >= 18) & (User.c.is_active == True))
> ```

---

## Sorting (ORDER BY)

```python
# Single column ascending (default)
users = User.query().order_by(User.c.name).all()

# Single column descending
users = User.query().order_by((User.c.created_at, 'DESC')).all()

# Multiple columns
users = User.query().order_by(
    (User.c.status, 'ASC'),
    (User.c.created_at, 'DESC')
).all()

# Random order (database-specific)
# Note: Use with caution on large datasets
users = User.query().order_by('RANDOM()').all()  # SQLite/PostgreSQL
```

---

## Pagination (LIMIT/OFFSET)

```python
# Limit - Get first N records
users = User.query().limit(10).all()

# Offset - Skip first N records
users = User.query().offset(20).all()

# Pagination - Get page 3 with 10 items per page
page = 3
per_page = 10
users = User.query().offset((page - 1) * per_page).limit(per_page).all()

# Common pagination pattern
def get_paginated(page: int = 1, per_page: int = 20):
    offset = (page - 1) * per_page
    return User.query().offset(offset).limit(per_page).all()
```

---

## Aggregate Functions

> ⚠️ **Naming Note**: `sum_`, `min_`, `max_` use underscore suffix to avoid conflict with Python's built-in functions `sum()`, `min()`, `max()`. Use `count` and `avg` without underscore.

```python
from rhosocial.activerecord.backend.expression import count, sum_, avg, max_, min_

# COUNT - Total number of records
total = User.query().aggregate(count()).scalar()

# COUNT with condition
active_users = User.query().where(
    User.c.status == 'active'
).aggregate(count()).scalar()

# SUM - Total of a column
total_sales = Order.query().aggregate(sum_(Order.c.amount)).scalar()

# AVG - Average value
avg_age = User.query().aggregate(avg(User.c.age)).scalar()

# MAX/MIN - Extreme values
max_score = Game.query().aggregate(max_(Game.c.score)).scalar()
min_score = Game.query().aggregate(min_(Game.c.score)).scalar()

# Multiple aggregates
result = User.query().aggregate(
    count().as_('total'),
    avg(User.c.age).as_('avg_age'),
    max(User.c.created_at).as_('latest')
).one()

print(f"Total: {result.total}, Avg Age: {result.avg_age}")
```

---

## Date/Time Queries

```python
from datetime import datetime, timedelta

# Today
today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
today_users = User.query().where(
    User.c.created_at >= today
).all()

# Last 7 days
week_ago = datetime.now() - timedelta(days=7)
recent_users = User.query().where(
    User.c.created_at >= week_ago
).all()

# Specific date range (chain .where() for AND - recommended)
start_date = datetime(2024, 1, 1)
end_date = datetime(2024, 12, 31)
users = User.query().where(
    User.c.created_at >= start_date
).where(
    User.c.created_at <= end_date
).all()

# Before a specific date
old_users = User.query().where(
    User.c.created_at < datetime(2020, 1, 1)
).all()
```

---

## String Operations

```python
# String length (if supported by dialect)
long_names = User.query().where(
    User.c.name.length() > 50
).all()

# String concatenation (if supported)
# Note: Check your dialect for string concat support
```

---

## Existence Checks

```python
# Check if any record exists
has_users = User.query().exists()

# Check with condition
has_admins = User.query().where(User.c.role == 'admin').exists()

# Use in conditional logic
if User.query().where(User.c.email == 'test@example.com').exists():
    print("User already exists!")
```

---

## Selecting Specific Columns

```python
# Select only specific columns (recommended: use FieldProxy)
users = User.query().select(User.c.id, User.c.name, User.c.email).all()

# Alternative: use field names as strings (if you know the column names)
users = User.query().select('id', 'name', 'email').all()

# Exclude specific columns (select all except)
users = User.query().select(exclude=['password_hash']).all()

# Note: When selecting specific columns, you get dict-like objects
# instead of full model instances
```

---

## Distinct Values

```python
# Get distinct values for a column
roles = User.query().distinct(User.c.role).all()

# Distinct with multiple columns
# (Returns unique combinations)
results = User.query().distinct(User.c.country, User.c.city).all()
```

---

## Raw SQL (When Needed)

```python
# Execute raw SQL for complex queries
result = User.__backend__.execute(
    "SELECT * FROM users WHERE custom_condition = ?",
    ('value',),
    options=ExecutionOptions(stmt_type=StatementType.DQL)
)

# Convert to models
users = [User(**row) for row in result.rows]
```

> ⚠️ **Warning:** Use raw SQL sparingly. It reduces portability across database backends.

---

## Quick Reference Card

```python
# Most common patterns in one place

# Basic fetch
User.query().all()                           # All records (list)
User.query().one()                           # First matching record or None

# Filtering
User.query().where(User.c.id == 1).one()
User.query().where(User.c.age > 18).all()
User.query().where(User.c.name.in_(['A', 'B'])).all()

# Logical operators (use & | ~, not and or not)
User.query().where((User.c.age >= 18) & (User.c.is_active == True)).all()
User.query().where((User.c.role == 'admin') | (User.c.role == 'moderator')).all()
User.query().where(~(User.c.status == 'deleted')).all()

# Sorting
User.query().order_by(User.c.name).all()
User.query().order_by((User.c.age, 'DESC')).all()

# Pagination
User.query().limit(10).all()
User.query().offset(20).limit(10).all()

# Counting
User.query().count()
User.query().where(User.c.active == True).count()

# Aggregates
from rhosocial.activerecord.backend.expression import count, sum_, avg
User.query().aggregate(count()).scalar()
Order.query().aggregate(sum_(Order.c.amount)).scalar()
```

---

## See Also

- [ActiveQuery](./active_query.md) - Complete ActiveQuery documentation
- [Query Recipes](./recipes.md) - Complex query examples
- [Query Optimization](./optimization.md) - Performance tips

# Frequently Asked Questions

This guide addresses common questions and issues you might encounter when getting started with rhosocial ActiveRecord.

## General Questions

### What is the difference between ActiveRecord and other ORMs?

rhosocial ActiveRecord follows the ActiveRecord pattern, which combines data access and business logic in a single object. This differs from other ORMs like SQLAlchemy, which often separate these concerns. Key differences include:

- **Integration with Pydantic**: rhosocial ActiveRecord leverages Pydantic for type validation and conversion
- **Simpler API**: Designed to be intuitive and require less boilerplate code
- **Fluent Query Interface**: Provides a chainable API for building complex queries
- **Built-in SQLite Support**: Works out of the box with SQLite

For a detailed comparison, see the [ORM Comparison](../1.introduction) document.

### Can I use ActiveRecord with existing databases?

Yes, rhosocial ActiveRecord works with existing databases. Simply define your models to match your existing table structure. You don't need to use the `create_table` method if your tables already exist.

## Installation and Setup

### Why am I getting "SQLite version too old" errors?

rhosocial ActiveRecord requires SQLite 3.25 or higher due to its use of window functions and other modern SQL features. You can check your SQLite version with:

```python
import sqlite3
print(sqlite3.sqlite_version)
```

If your version is too old, you may need to:
- Update your Python installation
- Install a newer version of SQLite and recompile Python's sqlite3 module
- Use a different database backend

### How do I connect to multiple databases?

You can configure different models to use different database connections:

```python
# Configure User model to use one database
User.configure(
    ConnectionConfig(database='users.sqlite3'),
    backend_class=SQLiteBackend
)

# Configure Product model to use another database
Product.configure(
    ConnectionConfig(database='products.sqlite3'),
    backend_class=SQLiteBackend
)
```

## Model Definition

### How do I define a primary key?

By default, rhosocial ActiveRecord uses a field named `id` as the primary key. You can customize this by setting the `__primary_key__` attribute:

```python
class User(ActiveRecord):
    __table_name__ = 'users'
    __primary_key__ = 'user_id'  # Custom primary key field
    
    user_id: int
    name: str
```

### How do I handle auto-incrementing fields?

For SQLite, integer primary keys are automatically auto-incrementing. For other field types or databases, you may need to use specific field types or database features.

### Can I use UUID primary keys?

Yes, rhosocial ActiveRecord supports UUID primary keys through the `UUIDField` mixin:

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field.uuid import UUIDField
from uuid import UUID

class User(UUIDField, ActiveRecord):
    __table_name__ = 'users'
    
    id: UUID  # UUID primary key
    name: str
```

## Database Operations

### How do I perform raw SQL queries?

You can access the database backend through the model class's `.backend()` method and then use the backend's `.execute()` method to run raw SQL queries:

```python
# Get the database backend
backend = User.backend()

# Execute a SELECT query and get results
result = backend.execute(
    "SELECT * FROM users WHERE age > ?", 
    params=(18,),
    returning=True,  # or use ReturningOptions.all_columns()
    column_types=None  # optional: specify column type mapping
)

# Process query results
if result and result.data:
    for row in result.data:
        print(row)  # each row is returned as a dictionary

# Execute INSERT/UPDATE/DELETE operations
result = backend.execute(
    "UPDATE users SET status = 'active' WHERE last_login > date('now', '-30 days')"
)
print(f"Affected rows: {result.affected_rows}")

# Use convenience method to get a single record
user = backend.fetch_one("SELECT * FROM users WHERE id = ?", params=(1,))

# Get multiple records
users = backend.fetch_all("SELECT * FROM users WHERE status = ?", params=('active',))
```

Parameters for the `execute()` method:
- `sql`: SQL statement string
- `params`: Query parameters (optional), passed as a tuple
- `returning`: Controls RETURNING clause behavior (optional)
- `column_types`: Column type mapping for result type conversion (optional)

The returned `QueryResult` object contains the following attributes:
- `data`: Query result data (list of dictionaries)
- `affected_rows`: Number of affected rows
- `last_insert_id`: Last inserted ID (if applicable)
- `duration`: Query execution time (seconds)

### How do I handle database migrations?

rhosocial ActiveRecord doesn't include a built-in migration system in the core package. For simple schema changes, you can use methods like `create_table`, `add_column`, etc. For more complex migrations, consider:

1. Using the optional migration package: `pip install rhosocial-activerecord[migration]`
2. Using a dedicated migration tool like Alembic
3. Managing migrations manually with SQL scripts

## Performance

### How do I optimize queries for large datasets?

For large datasets, consider these optimization techniques:

1. **Use pagination**: Limit the number of records retrieved at once
   ```python
   users = User.query().limit(100).offset(200).all()
   ```

2. **Select only needed columns**:
   ```python
   users = User.query().select('id', 'name').all()
   ```
   
   **Note**: When selecting specific columns, be aware of Pydantic validation rules. Fields not marked as optional (`Optional` type) cannot be `None`. If you're selecting a subset of columns for model instantiation, ensure all required fields are included or use `to_dict()` to bypass model validation.

3. **Use proper indexing**: Ensure your database tables have appropriate indexes

4. **Use eager loading for relationships**: Load related data in a single query

5. **Use dictionary results when appropriate**: When you only need data and not model functionality
   ```python
   # Returns dictionaries instead of model instances
   users = User.query().to_dict().all()
   
   # For JOIN queries or when model validation would fail
   results = User.query()\
       .join("JOIN orders ON users.id = orders.user_id")\
       .select("users.id", "users.name", "orders.total")\
       .to_dict(direct_dict=True)\
       .all()
   ```

### How can I return dictionary results instead of model instances?

When you need raw data access without model validation or when working with complex queries that return columns not defined in your model, use the `to_dict()` method:

```python
# Standard usage - models are instantiated first, then converted to dictionaries
users = User.query().to_dict().all()

# For JOIN queries - bypass model instantiation entirely
results = User.query()\
    .join("JOIN orders ON users.id = orders.user_id")\
    .select("users.id", "users.name", "orders.total")\
    .to_dict(direct_dict=True)\
    .all()

# Include only specific fields
users = User.query().to_dict(include={'id', 'name', 'email'}).all()

# Exclude specific fields
users = User.query().to_dict(exclude={'password', 'secret_token'}).all()
```

**Important Note:** The `to_dict()` method can only be placed at the end of an ActiveQuery call chain, and after calling it, you can only execute `all()`, `one()`, or `to_sql()` methods. After calling `to_dict()`, the returned object is no longer associated with the original ActiveQuery.

The `direct_dict=True` parameter is particularly useful when:
1. Working with JOIN queries that return columns not in your model schema
2. You need to bypass model validation
3. You're only interested in the data, not model functionality

## Troubleshooting

### Why are my changes not being saved to the database?

Common reasons include:

1. **Forgetting to call `save()`**: Changes to model attributes aren't automatically saved
2. **Transaction rollback**: If an exception occurs in a transaction, changes are rolled back
3. **Validation failures**: If validation fails, the save operation is aborted

Check for exceptions and ensure you're calling `save()` after making changes.

### How do I debug SQL queries?

You can enable SQL logging to see the queries being executed:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger('rhosocial.activerecord.backend').setLevel(logging.DEBUG)
```

This will print all SQL queries to the console, which can help identify performance issues or bugs.

## Next Steps

If your question isn't answered here, consider:

1. Exploring the full documentation for more detailed information
2. Checking the project's GitHub issues for similar problems
3. Joining the community discussion forums
4. Contributing to the project by improving documentation or reporting bugs
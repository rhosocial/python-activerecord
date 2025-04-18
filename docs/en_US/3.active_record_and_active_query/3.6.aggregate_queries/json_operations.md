# JSON Operations

rhosocial ActiveRecord provides a comprehensive set of database-agnostic JSON operations that allow you to work with JSON data stored in your database. These operations are particularly useful for working with semi-structured data and flexible schemas.

## JSON Support in Databases

JSON support varies across different database systems:

- **PostgreSQL**: Extensive native JSON and JSONB support (from version 9.2+)
- **MySQL/MariaDB**: Good JSON support (from MySQL 5.7+ and MariaDB 10.2+)
- **SQLite**: Basic JSON support through JSON1 extension (from version 3.9+)

rhosocial ActiveRecord abstracts these differences, providing a consistent API across all supported databases.

## JSON Operation Methods

The following JSON operation methods are available in the `AggregateQueryMixin` class:

| Method | Description |
|--------|-------------|
| `json_extract` | Extract a value from a JSON path |
| `json_extract_text` | Extract a value as text from a JSON path |
| `json_contains` | Check if JSON contains a specific value at a path |
| `json_exists` | Check if a JSON path exists |
| `json_type` | Get the type of a value at a JSON path |
| `json_length` | Get the length of a JSON array or object |
| `json_keys` | Get the keys of a JSON object |
| `json_remove` | Remove a value at a JSON path |
| `json_insert` | Insert a value at a JSON path if it doesn't exist |
| `json_replace` | Replace a value at a JSON path if it exists |
| `json_set` | Set a value at a JSON path (insert or replace) |

## Basic JSON Extraction

The most common JSON operation is extracting values from JSON data:

```python
# Extract a simple value from a JSON column
user_settings = User.query()\
    .select('id', 'name')\
    .json_extract('settings', '$.theme', 'theme')\
    .json_extract('settings', '$.notifications.email', 'email_notifications')\
    .all()

# Extract as text (removes quotes from JSON strings)
user_preferences = User.query()\
    .select('id')\
    .json_extract_text('preferences', '$.language', 'language')\
    .all()
```

## Filtering with JSON Conditions

You can use JSON operations in WHERE clauses to filter data:

```python
# Find users with a specific theme
dark_theme_users = User.query()\
    .where("JSON_EXTRACT(settings, '$.theme') = ?", ('dark',))\
    .all()

# Alternative using json_extract in a subquery
dark_theme_users = User.query()\
    .select('id', 'name')\
    .json_extract('settings', '$.theme', 'theme')\
    .where('theme = ?', ('dark',))\
    .all()

# Find users with email notifications enabled
email_users = User.query()\
    .where("JSON_EXTRACT(settings, '$.notifications.email') = ?", (True,))\
    .all()
```

## Checking JSON Containment and Existence

You can check if JSON data contains specific values or if paths exist:

```python
# Check if a user has a specific role
admins = User.query()\
    .select('id', 'name')\
    .json_contains('roles', '$', 'admin', 'is_admin')\
    .where('is_admin = ?', (1,))\
    .all()

# Check if a configuration path exists
configured_users = User.query()\
    .select('id', 'name')\
    .json_exists('settings', '$.theme', 'has_theme')\
    .where('has_theme = ?', (1,))\
    .all()
```

## Getting JSON Metadata

You can retrieve metadata about JSON values:

```python
# Get the type of a JSON value
settings_types = User.query()\
    .select('id')\
    .json_type('settings', '$.notifications', 'notifications_type')\
    .all()

# Get the length of a JSON array
role_counts = User.query()\
    .select('id')\
    .json_length('roles', '$', 'role_count')\
    .all()

# Get the keys of a JSON object
settings_keys = User.query()\
    .select('id')\
    .json_keys('settings', '$', 'available_settings')\
    .all()
```

## Modifying JSON Data

Some databases support modifying JSON data directly in queries:

```python
# Remove a JSON path
User.query()\
    .update({
        'settings': User.query().json_remove('settings', '$.old_setting')
    })\
    .where('id = ?', (123,))\
    .execute()

# Insert a new JSON value (only if path doesn't exist)
User.query()\
    .update({
        'settings': User.query().json_insert('settings', '$.new_setting', 'value')
    })\
    .where('id = ?', (123,))\
    .execute()

# Replace an existing JSON value (only if path exists)
User.query()\
    .update({
        'settings': User.query().json_replace('settings', '$.theme', 'light')
    })\
    .where('id = ?', (123,))\
    .execute()

# Set a JSON value (insert or replace)
User.query()\
    .update({
        'settings': User.query().json_set('settings', '$.theme', 'light')
    })\
    .where('id = ?', (123,))\
    .execute()
```

## Aggregating JSON Data

You can combine JSON operations with aggregate functions:

```python
# Count users by theme preference
theme_counts = User.query()\
    .json_extract('settings', '$.theme', 'theme')\
    .group_by('theme')\
    .count('id', 'user_count')\
    .aggregate()

# Average score by user role
role_scores = User.query()\
    .join('JOIN user_scores ON users.id = user_scores.user_id')\
    .json_extract('users.roles', '$[0]', 'primary_role')  # Extract first role\
    .group_by('primary_role')\
    .avg('user_scores.score', 'average_score')\
    .aggregate()
```

## Working with JSON Arrays

JSON arrays can be accessed using array indices in the path:

```python
# Extract the first item from a JSON array
first_address = Customer.query()\
    .select('id', 'name')\
    .json_extract('addresses', '$[0].street', 'primary_street')\
    .json_extract('addresses', '$[0].city', 'primary_city')\
    .all()

# Count items in a JSON array
address_counts = Customer.query()\
    .select('id')\
    .json_length('addresses', '$', 'address_count')\
    .all()
```

## Complex JSON Path Expressions

JSON path expressions can be quite sophisticated:

```python
# Extract nested array elements
product_tags = Product.query()\
    .select('id', 'name')\
    .json_extract('metadata', '$.categories[*].tags[0]', 'primary_tags')\
    .all()

# Extract values with conditions (PostgreSQL-specific)
if database_is_postgresql():
    active_features = Product.query()\
        .select('id', 'name')\
        .json_extract('features', '$.items[?(@.active==true)].name', 'active_feature_names')\
        .all()
```

## Error Handling

JSON operations will raise appropriate exceptions when used with unsupported database backends:

```python
try:
    results = User.query()\
        .json_extract('settings', '$.theme', 'theme')\
        .all()
except JsonOperationNotSupportedError as e:
    print(f"JSON operations not supported: {e}")
    # Fallback to non-JSON implementation
```

## Performance Considerations

- JSON operations can be less efficient than operations on regular columns
- Consider indexing JSON paths for frequently queried values (supported in PostgreSQL and MySQL)
- For frequently accessed JSON properties, consider extracting them to dedicated columns
- Complex JSON path expressions can be resource-intensive
- Test JSON queries with EXPLAIN to understand their execution plan

## Database-Specific Notes

### PostgreSQL

- Offers both `json` and `jsonb` types (prefer `jsonb` for better performance)
- Supports GIN indexes on JSONB columns for efficient querying
- Has the most comprehensive JSON path expression syntax

### MySQL/MariaDB

- Supports functional indexes on JSON expressions
- Good performance for basic JSON operations
- Limited support for complex JSON path expressions

### SQLite

- JSON support through the JSON1 extension
- Basic JSON functionality with simpler path expressions
- Limited indexing capabilities for JSON data

rhosocial ActiveRecord abstracts these differences where possible, providing a consistent API across different database backends.
# Debugging Techniques

Debugging rhosocial ActiveRecord applications currently relies on standard Python debugging techniques combined with basic logging capabilities.

## Using Python Debuggers

The most effective way to debug ActiveRecord applications is using standard Python debugging tools:

- `pdb` - Python's built-in debugger
- `breakpoint()` - Built-in function to set breakpoints (Python 3.7+)
- IDE debuggers (PyCharm, VS Code, etc.)

## Basic Logging for Debugging

Basic logging support is available through Python's standard logging module:

```python
import logging
from rhosocial.activerecord import ActiveRecord

# Enable logging to see SQL queries
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('rhosocial.activerecord')

# Example debugging approach
def debug_model_operations():
    user = User(name="Debug User", email="debug@example.com")
    print(f"User created: {user.name}, {user.email}")
    
    result = user.save()
    print(f"Save result: {result}")
    print(f"User ID after save: {user.id}")
```

## Query Debugging

Currently, query debugging is done by:

- Examining generated SQL strings (if available)
- Using print statements to inspect values
- Using Python debuggers to step through the code

## Common Debugging Approaches

1. **Model Validation Issues**: Print model values before and after validation
2. **Database Connection Issues**: Check connection parameters and database availability
3. **Query Issues**: Inspect query parameters and expected vs. actual results

## Limitations

- No built-in query profiling
- No advanced debugging tools specifically for ActiveRecord
- Limited query inspection capabilities
- No automatic debugging helpers

Debugging tools will be enhanced in future releases with more ActiveRecord-specific functionality.

## Using Logging for Debugging

Logging is one of the most powerful tools for debugging ActiveRecord applications. rhosocial ActiveRecord provides comprehensive logging capabilities to help you understand what's happening under the hood.

### Configuring Logging

```python
import logging
from rhosocial.activerecord import configure_logging

# Configure logging at the application level
configure_logging(level=logging.DEBUG)

# Or configure logging for specific components
configure_logging(level=logging.DEBUG, component="query")
```

### Log Levels

rhosocial ActiveRecord uses standard Python logging levels:

- `DEBUG`: Detailed information, typically useful only for diagnosing problems
- `INFO`: Confirmation that things are working as expected
- `WARNING`: Indication that something unexpected happened, but the application still works
- `ERROR`: Due to a more serious problem, the application has not been able to perform a function
- `CRITICAL`: A serious error indicating that the application itself may be unable to continue running

### What to Log

When debugging ActiveRecord applications, consider logging:

1. **SQL Queries**: Log the actual SQL being executed, along with parameters
2. **Query Execution Time**: Log how long queries take to execute
3. **Model Operations**: Log model creation, updates, and deletions
4. **Transaction Boundaries**: Log when transactions start, commit, or rollback
5. **Relationship Loading**: Log when relationships are loaded

### Example: Logging SQL Queries

```python
import logging
from rhosocial.activerecord import configure_logging

# Enable SQL query logging
configure_logging(level=logging.DEBUG, component="query")

# Now all SQL queries will be logged
users = User.where("age > ?", (25,)).order_by("created_at DESC").limit(10).all()

# Example log output:
# DEBUG:rhosocial.activerecord.query:Executing SQL: SELECT * FROM users WHERE age > ? ORDER BY created_at DESC LIMIT 10 with params (25,)
```

## Inspecting Query Execution

Understanding how ActiveRecord translates your code into SQL queries is crucial for debugging performance issues and unexpected results.

### Using explain() Method

The `explain()` method shows how the database will execute a query, helping you understand the execution plan and performance characteristics:

```python
from rhosocial.activerecord.backend.dialect import ExplainType, ExplainFormat

# Get basic query execution plan
explanation = User.where("age > ?", (25,)).order_by("created_at DESC").explain()
print(explanation)

# Use specific type of execution plan (SQLite-specific QUERYPLAN type)
query_plan = User.where("age > ?", (25,)).explain(type=ExplainType.QUERYPLAN).all()
print(query_plan)  # Outputs more readable query plan

# Use detailed options (depending on database support)
detailed_explanation = User.where("age > ?", (25,)).explain(
    type=ExplainType.BASIC,  # Basic execution plan
    format=ExplainFormat.TEXT,  # Text format output
    verbose=True  # Detailed information
).all()
print(detailed_explanation)
```

#### Supported Parameters

The `explain()` method supports the following parameters:

- **type**: Type of execution plan
  - `ExplainType.BASIC`: Basic execution plan (default)
  - `ExplainType.ANALYZE`: Include actual execution statistics
  - `ExplainType.QUERYPLAN`: Query plan only (SQLite specific)

- **format**: Output format
  - `ExplainFormat.TEXT`: Human readable text (default, supported by all databases)
  - `ExplainFormat.JSON`: JSON format (supported by some databases)
  - `ExplainFormat.XML`: XML format (supported by some databases)
  - `ExplainFormat.YAML`: YAML format (supported by PostgreSQL)
  - `ExplainFormat.TREE`: Tree format (supported by MySQL)

- **Other options**:
  - `costs=True`: Show estimated costs
  - `buffers=False`: Show buffer usage
  - `timing=True`: Include timing information
  - `verbose=False`: Show additional information
  - `settings=False`: Show modified settings (PostgreSQL)
  - `wal=False`: Show WAL usage (PostgreSQL)

#### Database Differences

Different databases have varying levels of support for `explain()`:

- **SQLite**: Supports `BASIC` and `QUERYPLAN` types, only supports `TEXT` format
- **PostgreSQL**: Supports more options like `buffers`, `settings`, and `wal`
- **MySQL**: Supports `TREE` format output

Note that if you specify options not supported by a particular database, those options will be ignored or may raise an error.

### Analyzing Query Performance

To identify slow queries:

```python
import time

# Measure query execution time
start_time = time.time()
result = User.where("age > ?", (25,)).order_by("created_at DESC").all()
end_time = time.time()

print(f"Query took {end_time - start_time:.6f} seconds")
print(f"Retrieved {len(result)} records")
```

### Debugging Complex Queries

For complex queries with joins, eager loading, or aggregations:

```python
# Get the raw SQL without executing the query
query = User.joins("posts").where("posts.published = ?", (True,)).group("users.id")
raw_sql, params = query.to_sql()  # Note: to_sql() returns both SQL and parameters
print(f"Generated SQL: {raw_sql}")
print(f"Parameters: {params}")

# Execute with debug logging
result = query.all()
```

#### Incremental Debugging with Chain Calls

For complex chain calls, you can debug each step by examining the SQL after each method call:

```python
# Start with a basic query
query = User.where("active = ?", (True,))
sql, params = query.to_sql()
print(f"After where: {sql} with params {params}")

# Add a join
query = query.joins("posts")
sql, params = query.to_sql()
print(f"After join: {sql} with params {params}")

# Add a condition on the joined table
query = query.where("posts.published = ?", (True,))
sql, params = query.to_sql()
print(f"After second where: {sql} with params {params}")

# Add grouping
query = query.group("users.id")
sql, params = query.to_sql()
print(f"After grouping: {sql} with params {params}")

# Finally execute
result = query.all()
```

This approach helps you understand how each method in the chain affects the final SQL query, making it easier to identify where issues might be occurring.

## Debugging Relationship Issues

Relationship issues are common in ActiveRecord applications. Here are techniques to debug them:

### Inspecting Loaded Relationships

```python
# Check if a relationship is loaded
user = User.find_by_id(1)
print(f"Is posts relationship loaded? {'_loaded_relations' in dir(user) and 'posts' in user._loaded_relations}")

# Inspect the loaded relationship data
if hasattr(user, '_loaded_relations') and 'posts' in user._loaded_relations:
    print(f"Loaded posts: {user._loaded_relations['posts']}")
```

### Debugging Eager Loading

```python
# Enable detailed logging for relationship loading
configure_logging(level=logging.DEBUG, component="relation")

# Use with_ to eager load relationships
user = User.with_("posts.comments").find_by_id(1)

# You can also debug the SQL generated for eager loading
sql, params = User.with_("posts.comments").to_sql()
print(f"Eager loading SQL: {sql}")
print(f"Parameters: {params}")

# Inspect the loaded relationships
print(f"User has {len(user.posts)} posts")
for post in user.posts:
    print(f"Post {post.id} has {len(post.comments)} comments")
```

#### Dot Notation for Relationship Names

When using eager loading with `with_()`, you can use dot notation to specify nested relationships. Understanding this naming convention is crucial for effective debugging:

```python
# Load a single relationship
users = User.with_("posts").all()

# Load multiple relationships at the same level
users = User.with_("posts", "profile", "settings").all()

# Load nested relationships (posts and their comments)
users = User.with_("posts.comments").all()

# Load deeply nested relationships
users = User.with_("posts.comments.author.profile").all()

# Load multiple nested paths
users = User.with_("posts.comments", "posts.tags", "profile.settings").all()
```

Each dot in the relationship path represents a level of nesting. The system will generate the appropriate JOIN statements to fetch all the required data in the minimum number of queries.

## Troubleshooting Common Issues

### N+1 Query Problem

The N+1 query problem occurs when you fetch N records and then execute N additional queries to fetch related data:

```python
# Enable query logging
configure_logging(level=logging.DEBUG, component="query")

# Bad approach (causes N+1 queries)
users = User.all()  # 1 query to fetch all users
for user in users:  # If there are 100 users, this will trigger 100 more queries
    print(f"User {user.username} has {len(user.posts)} posts")  # Each access to user.posts triggers a query
# Total: 101 queries (1 + N)

# Better approach (uses eager loading)
users = User.with_("posts").all()  # 1 query for users + 1 query for all related posts
for user in users:  # No matter how many users, no additional queries
    print(f"User {user.username} has {len(user.posts)} posts")  # No additional queries
# Total: 2 queries
```

#### Debugging N+1 Problems

To identify N+1 problems, watch for patterns in your logs where the same type of query is repeated many times with different parameters:

```python
# Enable detailed query logging
configure_logging(level=logging.DEBUG, component="query")

# Execute code that might have N+1 issues
users = User.all()
for user in users:
    _ = user.posts  # This will trigger N separate queries if not eager loaded
```

#### Database Indexing for Relationship Performance

Proper database indexing is crucial for relationship performance:

```python
# Example of creating indexes in a migration
def up(self):
    # Create index on foreign key columns
    self.add_index("posts", "user_id")  # Speeds up User.posts relationship
    
    # Create composite indexes for multiple conditions
    self.add_index("posts", ["user_id", "published"])  # Speeds up User.posts.where(published=True)
```

When debugging relationship performance issues:

1. Check if appropriate indexes exist on foreign key columns
2. Use `explain()` to see if your indexes are being used
3. Consider adding composite indexes for frequently filtered relationships
4. Monitor query execution time with and without indexes to measure improvement

### Unexpected Query Results

When queries return unexpected results:

```python
# Enable query logging to see the actual SQL
configure_logging(level=logging.DEBUG, component="query")

# Check the query conditions
query = User.where("age > ?", [25]).where("active = ?", [True])
print(f"Query conditions: {query._where_conditions}")

# Execute and inspect results
results = query.all()
print(f"Found {len(results)} results")
for user in results:
    print(f"User: {user.username}, Age: {user.age}, Active: {user.active}")
```

### Transaction Issues

Debugging transaction problems:

```python
# Enable transaction logging
configure_logging(level=logging.DEBUG, component="transaction")

try:
    with db_connection.transaction():
        user = User(username="test_user", email="test@example.com")
        user.save()
        
        # Simulate an error
        if not user.validate_email():
            raise ValueError("Invalid email")
            
        # This won't execute if an error occurs
        print("Transaction completed successfully")
except Exception as e:
    print(f"Transaction failed: {e}")
```

### Database Connection Issues

Troubleshooting database connection problems:

```python
# Check connection status
try:
    db_connection.execute("SELECT 1")
    print("Database connection is working")
except Exception as e:
    print(f"Database connection error: {e}")
    
# Check connection pool status (if using connection pooling)
if hasattr(db_connection, "pool"):
    print(f"Active connections: {db_connection.pool.active_connections}")
    print(f"Available connections: {db_connection.pool.available_connections}")
```

## Using Python Debuggers

Python's built-in debugging tools can be invaluable for ActiveRecord debugging.

### Using pdb

```python
import pdb

# Set a breakpoint
def process_user_data():
    users = User.where("age > ?", [25]).all()
    pdb.set_trace()  # Execution will pause here
    for user in users:
        # Process user data
        pass
```

### Using IPython's Debugger

If you're using IPython, you can use its enhanced debugger:

```python
from IPython.core.debugger import set_trace

def process_user_data():
    users = User.where("age > ?", [25]).all()
    set_trace()  # IPython debugger
    for user in users:
        # Process user data
        pass
```

## Debugging Tools and Extensions

### Database-Specific Tools

Many databases provide their own debugging tools:

- **SQLite**: SQLite Browser, SQLite Analyzer
- **PostgreSQL**: pgAdmin, pg_stat_statements
- **MySQL**: MySQL Workbench, EXPLAIN ANALYZE

### IDE Integration

Modern IDEs provide excellent debugging support:

- **PyCharm**: Integrated debugger with database tools
- **VS Code**: Python debugger extension with breakpoints and variable inspection
- **Jupyter Notebooks**: Interactive debugging with `%debug` magic command

## Best Practices for Debugging

1. **Start Simple**: Begin with the simplest possible test case that reproduces the issue

2. **Isolate the Problem**: Determine if the issue is in your code, the ActiveRecord library, or the database

3. **Use Logging Strategically**: Enable detailed logging only for the components you're debugging

4. **Check Your Assumptions**: Verify that variables contain what you expect them to contain

5. **Read the Error Messages**: ActiveRecord error messages often contain valuable information about what went wrong

6. **Examine the Generated SQL**: Always check the actual SQL being executed

7. **Test in Isolation**: Test individual queries or operations in isolation to pinpoint issues

8. **Use Version Control**: Make small, incremental changes and commit frequently to make it easier to identify when issues were introduced

9. **Write Regression Tests**: Once you fix a bug, write a test to ensure it doesn't reappear

10. **Document Your Findings**: Keep notes on bugs you encounter and how you resolved them
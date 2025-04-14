# Debugging Techniques

Effective debugging is essential for developing and maintaining ActiveRecord applications. This guide covers common debugging strategies, tools, and techniques to help you identify and resolve issues in your ActiveRecord code.

## Using Logging for Debugging

Logging is one of the most powerful tools for debugging ActiveRecord applications. Python ActiveRecord provides comprehensive logging capabilities to help you understand what's happening under the hood.

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

Python ActiveRecord uses standard Python logging levels:

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
users = User.where("age > ?", [25]).order("created_at DESC").limit(10).all()

# Example log output:
# DEBUG:rhosocial.activerecord.query:Executing SQL: SELECT * FROM users WHERE age > ? ORDER BY created_at DESC LIMIT 10 with params [25]
```

## Inspecting Query Execution

Understanding how ActiveRecord translates your code into SQL queries is crucial for debugging performance issues and unexpected results.

### Using explain() Method

The `explain()` method shows how the database will execute a query:

```python
# Get the query execution plan
explanation = User.where("age > ?", [25]).order("created_at DESC").explain()
print(explanation)

# For more detailed output (if supported by the database)
detailed_explanation = User.where("age > ?", [25]).explain(analyze=True, verbose=True)
print(detailed_explanation)
```

### Analyzing Query Performance

To identify slow queries:

```python
import time

# Measure query execution time
start_time = time.time()
result = User.where("age > ?", [25]).order("created_at DESC").all()
end_time = time.time()

print(f"Query took {end_time - start_time:.6f} seconds")
print(f"Retrieved {len(result)} records")
```

### Debugging Complex Queries

For complex queries with joins, eager loading, or aggregations:

```python
# Get the raw SQL without executing the query
query = User.joins("posts").where("posts.published = ?", [True]).group("users.id")
raw_sql = query.to_sql()
print(f"Generated SQL: {raw_sql}")

# Execute with debug logging
result = query.all()
```

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

# Inspect the loaded relationships
print(f"User has {len(user.posts)} posts")
for post in user.posts:
    print(f"Post {post.id} has {len(post.comments)} comments")
```

## Troubleshooting Common Issues

### N+1 Query Problem

The N+1 query problem occurs when you fetch N records and then execute N additional queries to fetch related data:

```python
# Enable query logging
configure_logging(level=logging.DEBUG, component="query")

# Bad approach (causes N+1 queries)
users = User.all()
for user in users:
    print(f"User {user.username} has {len(user.posts)} posts")  # Each access to user.posts triggers a query

# Better approach (uses eager loading)
users = User.with_("posts").all()
for user in users:
    print(f"User {user.username} has {len(user.posts)} posts")  # No additional queries
```

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
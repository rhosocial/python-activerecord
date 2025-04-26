# Debugging Techniques

Effective debugging is essential for developing and maintaining ActiveRecord applications. This guide covers common debugging strategies, tools, and techniques to help you identify and resolve issues in your ActiveRecord code.

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

The `explain()` method is a **marker method** that doesn't directly return the execution plan but marks the current query to return the execution plan. You need to combine it with an execution method (like `all()`, `one()`, etc.) to get information about how the database will execute a query:

```python
from rhosocial.activerecord.backend.dialect import ExplainType, ExplainFormat

# Get basic query execution plan
explanation = User.where("age > ?", (25,)).order_by("created_at DESC").explain().all()
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
query = User.joins("posts").where("posts.published = ?", (True,)).group_by("users.id")
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
query = query.group_by("users.id")
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
user = User.find_one(1)  # Note: use find_one instead of find_by_id
print(f"Is posts relationship loaded? {'_loaded_relations' in dir(user) and 'posts' in user._loaded_relations}")

# Inspect the loaded relationship data
if hasattr(user, '_loaded_relations') and 'posts' in user._loaded_relations:
    print(f"Loaded posts: {user._loaded_relations['posts']}")
```

### Debugging Eager Loading

```python
# Enable verbose logging for relationship loading
configure_logging(level=logging.DEBUG, component="relation")

# Use with_ to eager load relationships
user = User.with_("posts.comments").find_one(1)  # Note: use find_one instead of find_by_id

# You can also debug the SQL generated for eager loading
sql, params = User.with_("posts.comments").to_sql()
print(f"Eager loading SQL: {sql}")
print(f"Parameters: {params}")

# Inspect loaded relationships
print(f"User has {len(user.posts())} posts")  # Note: use posts() not posts
for post in user.posts():
    print(f"Post {post.id} has {len(post.comments())} comments")  # Note: use comments() not comments
```

## Troubleshooting Common Issues

### N+1 Query Problem

The N+1 query problem occurs when you fetch N records and then execute N additional queries to fetch related data:

```python
# Enable query logging
configure_logging(level=logging.DEBUG, component="query")

# Bad approach (causes N+1 queries)
users = User.all()  # 1 query to get all users
for user in users:  # If there are 100 users, this will trigger 100 additional queries
    print(f"User {user.username} has {len(user.posts())} posts")  # Each access to user.posts() triggers a query
# Total: 101 queries (1 + N)

# Better approach (using eager loading)
users = User.with_("posts").all()  # 1 query for users + 1 query for all related posts
for user in users:  # No matter how many users, no additional queries
    print(f"User {user.username} has {len(user.posts())} posts")  # No additional queries
# Total: 2 queries
```

#### Dot Notation for Relationship Names

When using `with_()` for eager loading, you can use dot notation to specify nested relationships. Understanding this naming convention is crucial for effective debugging:

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

Each dot in the relationship path represents one level of nesting. The system will generate appropriate JOIN statements to fetch all required data with the minimum number of queries.

#### Debugging N+1 Issues

To identify N+1 issues, look for patterns in the logs where the same type of query is repeated multiple times with different parameters:

```python
# Enable verbose query logging
configure_logging(level=logging.DEBUG, component="query")

# Execute code that might have N+1 issues
users = User.all()
for user in users:
    _ = user.posts()  # If not eager loaded, this will trigger N separate queries
```

#### Database Indexes for Relationship Performance

Proper database indexes are crucial for relationship performance:

```python
# Example of creating indexes in a migration
def up(self):
    # Create index on foreign key column
    self.add_index("posts", "user_id")  # Speeds up User.posts relationship
    
    # Create composite index for multiple conditions
    self.add_index("posts", ["user_id", "published"])  # Speeds up User.posts.where(published=True)
```

When debugging relationship performance issues:

1. Check if appropriate indexes exist on foreign key columns
2. Use `explain()` to see if indexes are being used
3. Consider adding composite indexes for frequently filtered relationships
4. Monitor query execution times with and without indexes to measure improvements

### Unexpected Query Results

When queries return unexpected results:

```python
# Enable query logging to see the actual SQL
configure_logging(level=logging.DEBUG, component="query")

# Inspect query conditions
query = User.where("age > ?", [25]).where("active = ?", [True])
print(f"Query conditions: {query._where_conditions}")

# Execute and inspect results
results = query.all()
print(f"Found {len(results)} results")
for user in results:
    print(f"User: {user.username}, Age: {user.age}, Active: {user.active}")
```

## How Relationship Eager Loading Works

Understanding the internal workings of relationship eager loading is crucial for effective debugging and query optimization.

### The Nature of Eager Loading

Eager Loading is an optimization technique that improves performance by reducing the number of database queries. When you use the `with_()` method, ActiveRecord performs the following steps:

1. Execute the main query to get the parent records (e.g., users)
2. Collect all primary key values from the parent records
3. Execute a single query to get all related records (e.g., all posts for those users)
4. Associate the related records with their parent records in memory

This approach reduces the number of queries from N+1 (1 main query + N relationship queries) to 2 (1 main query + 1 relationship query).

### Practical Example of Eager Loading

Here's a detailed example of how eager loading works:

```python
# Without eager loading (N+1 problem)
users = User.where("active = ?", [True]).all()  # 1 query

# Generated SQL:
# SELECT * FROM users WHERE active = ?

for user in users:  # Assuming 3 users are returned
    posts = user.posts()  # 1 query per user
    # Generated SQL (repeated 3 times, each with different user.id):
    # SELECT * FROM posts WHERE user_id = ?

# Total: 4 queries (1 + 3)

# With eager loading
users = User.where("active = ?", [True]).with_("posts").all()  # 2 queries

# Generated SQL:
# Query 1: SELECT * FROM users WHERE active = ?
# Query 2: SELECT * FROM posts WHERE user_id IN (1, 2, 3)  # Assuming user IDs are 1, 2, and 3

for user in users:
    posts = user.posts()  # No additional queries, uses already loaded data

# Total: 2 queries
```

### How Nested Eager Loading Works

Nested eager loading (e.g., `with_("posts.comments")`) works in a similar way but executes additional queries to load the nested relationships:

```python
users = User.where("active = ?", [True]).with_("posts.comments").all()  # 3 queries

# Generated SQL:
# Query 1: SELECT * FROM users WHERE active = ?
# Query 2: SELECT * FROM posts WHERE user_id IN (1, 2, 3)
# Query 3: SELECT * FROM comments WHERE post_id IN (101, 102, 103, ...)  # Assuming post IDs are 101, 102, 103, etc.
```

### Conditional Eager Loading

You can use query modifiers to limit the related records that are eager loaded:

```python
# Eager load only published posts
users = User.with_(("posts", lambda q: q.where("published = ?", [True]))).all()

# Generated SQL:
# Query 1: SELECT * FROM users
# Query 2: SELECT * FROM posts WHERE user_id IN (1, 2, 3) AND published = ?
```

### Relationship Query Methods

In addition to directly accessing relationships (like `user.posts()`), you can use relationship query methods (like `user.posts_query()`) to further customize relationship queries:

```python
# Get a user
user = User.find_one(1)

# Use relationship query method
posts_query = user.posts_query()  # Returns a query object, not yet executed

# Customize the query
recent_posts = posts_query.where("created_at > ?", [one_week_ago]).order_by("created_at DESC").limit(5).all()
```

This approach allows you to apply additional filtering, sorting, and limiting on top of the relationship without loading all related records.

## Pagination for Large Data Sets

When dealing with large amounts of data, pagination is an important optimization technique. Here are several approaches to implement pagination in ActiveRecord:

### Basic Pagination

Use `limit` and `offset` for basic pagination:

```python
# Get page 2, with 10 records per page
page = 2
per_page = 10
offset = (page - 1) * per_page

users = User.order_by("created_at DESC").limit(per_page).offset(offset).all()
```

### Pagination for Relationship Queries

Pagination can also be applied to relationship queries:

```python
# Get a user
user = User.find_one(1)

# Paginate the user's posts
page = 2
per_page = 10
offset = (page - 1) * per_page

posts = user.posts_query().order_by("created_at DESC").limit(per_page).offset(offset).all()
```

### Combining Eager Loading with Pagination

When using eager loading, you might want to limit the number of related records that are loaded:

```python
# Get users and eager load their 5 most recent posts
users = User.with_(("posts", lambda q: q.order_by("created_at DESC").limit(5))).all()

# Now each user has at most 5 most recent posts eager loaded
for user in users:
    recent_posts = user.posts()  # Contains at most 5 most recent posts
```

### Cursor-Based Pagination

For very large datasets, cursor-based pagination is often more efficient than offset-based pagination:

```python
# Initial query (first page)
first_page = User.order_by("id ASC").limit(10).all()

# If there are results, get the last ID as the cursor
if first_page:
    last_id = first_page[-1].id
    
    # Get the next page (using the cursor)
    next_page = User.where("id > ?", [last_id]).order_by("id ASC").limit(10).all()
```

### Calculating Total Record Count

To implement pagination UI, you typically need to know the total number of records:

```python
# Get total record count
total_count = User.count()

# Calculate total pages
per_page = 10
total_pages = (total_count + per_page - 1) // per_page  # Ceiling division

print(f"Total records: {total_count}, Total pages: {total_pages}")
```

### Pagination Performance Optimizations

1. **Add appropriate indexes**: Ensure indexes on columns used for sorting and filtering
2. **Avoid large offsets**: For large datasets, avoid using large `offset` values, consider cursor-based pagination
3. **Limit eager loaded data**: Use conditional eager loading to limit the number of records loaded for each relationship
4. **Cache counts**: For frequent count queries, consider caching the total record count

## Using Python Debuggers

Python's built-in debugging tools are valuable for ActiveRecord debugging.

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

If you use IPython, you can use its enhanced debugger:

```python
from IPython.core.debugger import set_trace

def process_user_data():
    users = User.where("age > ?", [25]).all()
    set_trace()  # IPython debugger
    for user in users:
        # Process user data
        pass
```

## Summary

Effective debugging is key to developing high-quality ActiveRecord applications. By using the techniques described in this guide, you can more easily identify and resolve common issues, including:

- Understanding query execution with logging and the `explain()` method
- Solving N+1 query problems with eager loading
- Customizing relationship queries with relationship query methods
- Implementing effective pagination strategies for large datasets
- Leveraging Python debugging tools for in-depth debugging

Remember that good debugging practices not only help solve problems but also help you write more efficient and maintainable code.
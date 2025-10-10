# Performance Analysis

Currently, rhosocial ActiveRecord does not include built-in performance profiling tools. Performance analysis relies on general Python profiling tools and manual techniques.

## Using Standard Python Profilers

For performance analysis of ActiveRecord applications, use standard Python profiling tools:

### cProfile
```python
import cProfile
import pstats
from rhosocial.activerecord import ActiveRecord

def performance_test():
    # Your ActiveRecord operations here
    users = User.find_all().limit(100).all()
    for user in users:
        user.email = f"updated_{user.email}"
        user.save()

# Profile the function
profiler = cProfile.Profile()
profiler.enable()
performance_test()
profiler.disable()

# Print stats
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats()
```

### Using line_profiler (if installed)
```python
# Add @profile decorator to functions you want to analyze
@profile
def slow_function():
    # ActiveRecord operations
    pass
```

## Basic Performance Measurement

For simple timing measurements:

```python
import time
from rhosocial.activerecord import ActiveRecord

def time_operation():
    start_time = time.time()
    
    # ActiveRecord operation
    users = User.find_all().limit(1000).all()
    
    end_time = time.time()
    print(f"Operation took {end_time - start_time:.2f} seconds")
```

## Query Performance

Currently, query performance analysis relies on:
- Examining SQL queries manually
- Using database-specific tools to analyze query plans
- Timing query execution with standard Python timing functions

## Current Limitations

- No built-in query timing
- No automatic performance metrics
- No query plan analysis tools
- No ActiveRecord-specific profiling tools

Performance profiling features will be added as the framework matures.

## Query Profiling

### Built-in Query Statistics

rhosocial ActiveRecord provides built-in query statistics to help you identify slow queries:

```python
from rhosocial.activerecord import stats

# Enable query statistics
stats.enable()

# Execute some queries
users = User.find_all()
posts = Post.find_by_user_id(user_id)

# Get query statistics
query_stats = stats.get_stats()
print(f"Total queries executed: {query_stats['total_queries']}")
print(f"Average query time: {query_stats['avg_query_time']}ms")

# Get the slowest queries
slow_queries = stats.get_slow_queries(limit=5)
for query in slow_queries:
    print(f"Query: {query['sql']}")
    print(f"Execution time: {query['execution_time']}ms")
    print(f"Parameters: {query['params']}")
    print("---")

# Reset statistics
stats.reset()
```

### Using Database Tools

Most database systems provide tools for analyzing query performance:

- **MySQL**: EXPLAIN command and Performance Schema
- **PostgreSQL**: EXPLAIN ANALYZE command
- **SQLite**: EXPLAIN QUERY PLAN command

Example: Using EXPLAIN to analyze a query:

```python
from rhosocial.activerecord import raw_sql

# Get the execution plan for a query
query = User.where(status='active').order_by('created_at').limit(10).to_sql()
explain_result = raw_sql(f"EXPLAIN {query}")

# Analyze the results
for row in explain_result:
    print(row)
```

## Memory Usage Analysis

### Tracking Object Allocations

Large ActiveRecord applications may encounter memory usage issues, especially when dealing with large result sets:

```python
import tracemalloc

# Start memory tracking
tracemalloc.start()

# Perform some ActiveRecord operations
users = User.find_all(include=['posts', 'comments'])

# Get memory snapshot
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')

# Display memory usage
print("Top memory usage locations:")
for stat in top_stats[:10]:
    print(f"{stat.count} blocks: {stat.size / 1024:.1f} KiB")
    print(f"  {stat.traceback.format()[0]}")

# Stop tracking
tracemalloc.stop()
```

### Tips for Reducing Memory Usage

- Use iterators instead of loading all records
- Select only the fields you need
- Process large datasets in batches
- Use lazy loading relationships appropriately

## Integration with Python Profilers

### Using cProfile

Python's built-in profiler cProfile can help identify performance bottlenecks in your code:

```python
import cProfile
import pstats

# Run code with profiler
def run_queries():
    for i in range(100):
        User.find_by_id(i)
        Post.find_by_user_id(i)

# Create profiler and run function
profiler = cProfile.Profile()
profiler.enable()
run_queries()
profiler.disable()

# Analyze results
stats = pstats.Stats(profiler).sort_stats('cumtime')
stats.print_stats(20)  # Print top 20 results
```

### Using line_profiler for Line-Level Profiling

For more detailed analysis, you can use the line_profiler package for line-level profiling:

```bash
pip install line_profiler
```

```python
# Add decorator in your code
from line_profiler import profile

@profile
def complex_query_function():
    users = User.where(status='active')
    result = []
    for user in users:
        posts = user.posts.where(published=True).order_by('-created_at')
        result.append((user, posts[:5]))
    return result

# Run the function
result = complex_query_function()
```

Then run the script with kernprof:

```bash
kernprof -l script.py
python -m line_profiler script.py.lprof
```

## Performance Monitoring Tools

### Integrating APM Tools

For production environments, consider using Application Performance Monitoring (APM) tools:

- **New Relic**
- **Datadog**
- **Prometheus + Grafana**

These tools can provide real-time performance monitoring, query analysis, and alerting capabilities.

### Custom Performance Metrics

rhosocial ActiveRecord allows you to define and collect custom performance metrics:

```python
from rhosocial.activerecord import metrics

# Register custom metric
metrics.register('user_query_time', 'histogram')

# Record metric in code
with metrics.timer('user_query_time'):
    users = User.find_all()

# Export metrics
all_metrics = metrics.export()
print(all_metrics)
```

## Best Practices

- Perform profiling regularly, not just when problems arise
- Establish performance baselines so you can compare performance before and after changes
- Focus on the most frequently executed queries and the slowest queries
- Use appropriate indexes to optimize database queries
- Consider using caching to reduce database load
- Test with production-like loads in development environments

## Conclusion

Performance profiling is an ongoing process, not a one-time activity. By using the tools and techniques described in this guide, you can identify and address performance bottlenecks in your ActiveRecord applications, ensuring your application runs efficiently under various load conditions.
# Performance Analysis and Monitoring

Identifying performance bottlenecks is a critical step in optimizing database applications. This document explores various tools and techniques for analyzing and monitoring the performance of rhosocial ActiveRecord applications.

## Introduction

Performance analysis and monitoring help you understand how your application interacts with the database, identify slow queries, and measure the impact of optimization efforts. rhosocial ActiveRecord provides several built-in tools to assist with these tasks.

## Query Profiling

### Basic Query Profiling

rhosocial ActiveRecord includes a `QueryProfiler` class that helps you track and analyze database queries:

```python
from rhosocial.activerecord.models import User
from rhosocial.activerecord.profiler import QueryProfiler

# Profile a specific operation
with QueryProfiler() as profiler:
    users = User.objects.filter(status='active').order_by('name').all()

# View profiling results
print(f"Total queries: {profiler.query_count}")
print(f"Total duration: {profiler.total_duration_ms} ms")
print(f"Average duration: {profiler.average_duration_ms} ms")

# Examine individual queries
for i, query in enumerate(profiler.queries, 1):
    print(f"Query {i}: {query.sql}")
    print(f"Parameters: {query.params}")
    print(f"Duration: {query.duration_ms} ms")
    print(f"Rows: {query.row_count}")
```

### Detailed Query Analysis

```python
from rhosocial.activerecord.profiler import QueryProfiler

# Profile with detailed analysis
with QueryProfiler(analyze=True) as profiler:
    # Perform multiple operations
    users = User.objects.all()
    for user in users:
        user.articles.filter(status='published').all()

# Get a summary report
report = profiler.summary()
print(report)

# Identify N+1 query patterns
n_plus_one = profiler.detect_n_plus_one()
for pattern in n_plus_one:
    print(f"N+1 pattern detected: {pattern.description}")
    print(f"Main query: {pattern.main_query}")
    print(f"Repeated queries: {pattern.repeated_query} (executed {pattern.count} times)")
    print(f"Suggested fix: {pattern.suggestion}")
```

## Execution Plan Analysis

Database execution plans provide insights into how queries are executed:

```python
from rhosocial.activerecord.models import Article

# Get the execution plan for a query
query = Article.objects.filter(status='published').order_by('-published_at')
execution_plan = query.explain()
print(execution_plan)

# Get a more detailed execution plan with actual execution statistics
detailed_plan = query.explain(analyze=True)
print(detailed_plan)

# Format the plan for easier reading
formatted_plan = query.explain(format='json')
import json
print(json.dumps(formatted_plan, indent=2))
```

### Interpreting Execution Plans

Key elements to look for in execution plans:

1. **Sequential Scans**: Full table scans that can be slow for large tables
2. **Index Scans**: Faster access using indexes
3. **Join Types**: Nested loops, hash joins, merge joins
4. **Sort Operations**: Can be expensive for large datasets
5. **Temporary Tables**: May indicate complex operations

```python
from rhosocial.activerecord.models import Article
from rhosocial.activerecord.profiler import ExplainAnalyzer

# Analyze an execution plan
query = Article.objects.filter(status='published').join('author').order_by('-published_at')
plan = query.explain(analyze=True)

analyzer = ExplainAnalyzer(plan)
print(f"Potential issues: {analyzer.issues}")
print(f"Recommendations: {analyzer.recommendations}")
```

## Database Monitoring

### Connection Pool Monitoring

```python
from rhosocial.activerecord.connection import connection_pool

# Get connection pool statistics
stats = connection_pool.stats()
print(f"Total connections: {stats.total}")
print(f"Active connections: {stats.active}")
print(f"Idle connections: {stats.idle}")
print(f"Waiting threads: {stats.waiting}")
print(f"Max connections: {stats.max}")
print(f"Connection checkout time: {stats.checkout_time_ms} ms (avg)")
```

### Query Statistics

```python
from rhosocial.activerecord.stats import QueryStats

# Get global query statistics
stats = QueryStats.get()
print(f"Total queries: {stats.total}")
print(f"Select queries: {stats.select}")
print(f"Insert queries: {stats.insert}")
print(f"Update queries: {stats.update}")
print(f"Delete queries: {stats.delete}")
print(f"Average duration: {stats.average_duration_ms} ms")

# Reset statistics
QueryStats.reset()
```

## Application Performance Metrics

### Model-level Metrics

```python
from rhosocial.activerecord.models import User
from rhosocial.activerecord.stats import ModelStats

# Get statistics for a specific model
stats = ModelStats.get(User)
print(f"Total loads: {stats.loads}")
print(f"Total saves: {stats.saves}")
print(f"Total deletes: {stats.deletes}")
print(f"Average load time: {stats.average_load_time_ms} ms")
print(f"Average save time: {stats.average_save_time_ms} ms")
```

### Cache Performance Metrics

```python
from rhosocial.activerecord.cache import CacheStats

# Get cache statistics
stats = CacheStats.get()
print(f"Hits: {stats.hits}")
print(f"Misses: {stats.misses}")
print(f"Hit ratio: {stats.hit_ratio:.2f}")

# Get model cache statistics
model_stats = CacheStats.get_model_stats(User)
print(f"User model cache hit ratio: {model_stats.hit_ratio:.2f}")

# Get query cache statistics
query_stats = CacheStats.get_query_stats()
print(f"Query cache hit ratio: {query_stats.hit_ratio:.2f}")
```

## Identifying N+1 Query Problems

The N+1 query problem is a common performance issue in ORM frameworks:

```python
from rhosocial.activerecord.models import User
from rhosocial.activerecord.profiler import QueryProfiler

# Example of N+1 problem
with QueryProfiler() as profiler:
    users = User.objects.all()  # 1 query
    for user in users:
        articles = user.articles.all()  # N queries, one per user

# Detect N+1 problems
n_plus_one = profiler.detect_n_plus_one()
if n_plus_one:
    print("N+1 query problem detected!")
    for pattern in n_plus_one:
        print(f"Fix suggestion: {pattern.suggestion}")

# Solution: Use eager loading
with QueryProfiler() as profiler:
    users = User.objects.prefetch_related('articles').all()  # 2 queries total
    for user in users:
        articles = user.articles  # No additional queries

print(f"Total queries with eager loading: {profiler.query_count}")
```

## Performance Testing Methodologies

### Benchmarking Queries

```python
from rhosocial.activerecord.models import Article
from rhosocial.activerecord.benchmark import benchmark

# Define queries to benchmark
queries = {
    'basic': lambda: Article.objects.filter(status='published').all(),
    'with_join': lambda: Article.objects.filter(status='published').join('author').all(),
    'with_eager_loading': lambda: Article.objects.filter(status='published').prefetch_related('comments').all()
}

# Run benchmark
results = benchmark(queries, iterations=100)

# View results
for name, result in results.items():
    print(f"Query: {name}")
    print(f"Average time: {result.average_ms} ms")
    print(f"Min time: {result.min_ms} ms")
    print(f"Max time: {result.max_ms} ms")
    print(f"Queries per second: {result.qps}")
```

### Load Testing

```python
from rhosocial.activerecord.models import Article
from rhosocial.activerecord.benchmark import load_test
import asyncio

# Define test scenarios
async def scenario_read_articles():
    # Simulate a user reading articles
    articles = await Article.objects.async_filter(status='published').limit(10).async_all()
    for article in articles:
        await asyncio.sleep(0.1)  # Simulate reading
        comments = await article.comments.async_all()

# Run load test
results = load_test(
    scenario_read_articles,
    concurrency=50,  # 50 concurrent users
    duration=60      # Run for 60 seconds
)

# View results
print(f"Total executions: {results.total_executions}")
print(f"Executions per second: {results.executions_per_second}")
print(f"Average response time: {results.average_response_time_ms} ms")
print(f"95th percentile response time: {results.p95_response_time_ms} ms")
print(f"Error rate: {results.error_rate:.2f}%")
```

## Integration with External Monitoring Tools

### Logging for Analysis

```python
from rhosocial.activerecord import set_log_level
import logging

# Enable detailed query logging
set_log_level(logging.DEBUG)

# Configure a file handler for analysis
handler = logging.FileHandler('activerecord_queries.log')
handler.setLevel(logging.DEBUG)
logging.getLogger('rhosocial.activerecord').addHandler(handler)
```

### Prometheus Integration

```python
from rhosocial.activerecord.monitoring import PrometheusExporter

# Set up Prometheus metrics exporter
exporter = PrometheusExporter()
exporter.start(port=8000)

# Metrics will be available at http://localhost:8000/metrics
```

### APM Integration

```python
from rhosocial.activerecord.monitoring import APMIntegration

# Set up APM integration (e.g., New Relic, Datadog)
APMIntegration.setup(service_name='my_application')
```

## Performance Optimization Workflow

1. **Measure**: Establish performance baselines
2. **Identify**: Find bottlenecks using profiling tools
3. **Optimize**: Implement improvements
4. **Verify**: Measure again to confirm improvements
5. **Monitor**: Continuously track performance

```python
from rhosocial.activerecord.models import Article
from rhosocial.activerecord.profiler import QueryProfiler
from rhosocial.activerecord.benchmark import benchmark

# Step 1: Measure baseline performance
baseline_query = lambda: Article.objects.filter(status='published').order_by('-published_at').all()
baseline_result = benchmark({'baseline': baseline_query}, iterations=100)
print(f"Baseline average time: {baseline_result['baseline'].average_ms} ms")

# Step 2: Identify bottlenecks
with QueryProfiler() as profiler:
    baseline_query()
print(profiler.summary())

# Step 3: Optimize
optimized_query = lambda: Article.objects.filter(status='published')\
                                      .select('id', 'title', 'published_at')\
                                      .order_by('-published_at')\
                                      .all()

# Step 4: Verify improvement
optimized_result = benchmark({'optimized': optimized_query}, iterations=100)
print(f"Optimized average time: {optimized_result['optimized'].average_ms} ms")

improvement = (baseline_result['baseline'].average_ms - 
               optimized_result['optimized'].average_ms) / \
              baseline_result['baseline'].average_ms * 100
print(f"Performance improvement: {improvement:.2f}%")
```

## Best Practices Summary

1. **Profile Regularly**: Make performance profiling a regular part of your development workflow

2. **Analyze Execution Plans**: Use execution plans to understand how your queries are processed

3. **Monitor Connection Pools**: Ensure your connection pool is properly sized for your application

4. **Track Cache Performance**: Monitor cache hit ratios and adjust caching strategies accordingly

5. **Identify N+1 Problems**: Actively look for and fix N+1 query patterns

6. **Benchmark Critical Paths**: Regularly benchmark performance-critical parts of your application

7. **Use Appropriate Logging**: Configure logging to capture performance-related information

8. **Integrate with Monitoring Tools**: Use external tools for long-term performance monitoring

9. **Establish Performance Budgets**: Define acceptable performance thresholds for key operations

10. **Implement Continuous Monitoring**: Set up alerts for performance regressions

By implementing these performance analysis and monitoring practices, you can ensure your rhosocial ActiveRecord applications maintain optimal performance as they evolve and grow.
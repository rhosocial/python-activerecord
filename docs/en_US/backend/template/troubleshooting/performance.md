# Performance Issues

## Overview

This document covers common performance issues and their solutions for the {backend} backend.

## Slow Query Analysis

### Enable Slow Query Logging

<!-- Document backend-specific slow query logging. Examples:

#### MySQL

```sql
SET GLOBAL slow_query_log = 1;
SET GLOBAL long_query_time = 1;
SET GLOBAL slow_query_log_file = '/var/log/mysql/slow.log';
```

#### PostgreSQL

```sql
ALTER SYSTEM SET log_min_duration_statement = 1000;  -- 1 second
SELECT pg_reload_conf();
```

-->

### Using EXPLAIN

Analyze slow queries with EXPLAIN:

```python
# Get the execution plan
result = User.query().where(User.c.age >= 18).explain()

for line in result:
    print(line)
```

See [EXPLAIN](../backend_specific_features/explain.md) for detailed usage.

## Common Performance Issues

### Missing Index

**Symptom**: Full table scans on large tables.

**Solution**: Add appropriate indexes:

```python
class User(ActiveRecord):
    @classmethod
    def indexes(cls) -> list:
        return [
            {'columns': ['email'], 'unique': True},
            {'columns': ['created_at']},
        ]
```

### SELECT * Overhead

**Symptom**: Fetching more data than needed.

**Solution**: Select only the columns you need:

```python
# ❌ Bad: fetches all columns
users = User.query().all()

# Good: select specific columns
users = User.query().select(User.c.id, User.c.username).all()
```

### N+1 Query Problem

**Symptom**: Many small queries instead of one joined query.

**Solution**: Use eager loading:

```python
# ❌ Bad: N+1 queries
users = User.query().all()
for user in users:
    posts = user.posts()  # separate query for each user

# Good: eager loading with with_()
users = User.query().with_('posts').all()
```

## Connection Timeouts

If queries are timing out:

```python
config = {Backend}ConnectionConfig(
    host='localhost',
    port={port},
    database='myapp',
    username='app',
    password='secret',
    connect_timeout=30,
    read_timeout=60,
    write_timeout=60,
)
```

## See Also

- [EXPLAIN](../backend_specific_features/explain.md) — query plan analysis
- [Indexing](../backend_specific_features/indexing.md) — index optimization
- [Core: Performance](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/performance)

💡 *AI Prompt:* "How do I optimize a slow {database} query?"

# Connection Pool Examples

This directory contains examples for testing the connection pool with different backends.

## Available Examples

### SQLite (included in python-activerecord)

- **connection_pool_stress_test_sync.py** - Synchronous stress test for SQLite connection pool
- **connection_pool_stress_test_async.py** - Asynchronous stress test for SQLite connection pool
- **connection_pool_basic_usage.py** - Basic usage examples
- **connection_pool_async_usage.py** - Async usage examples
- **connection_pool_context_awareness.py** - Context awareness examples

### Usage

Run SQLite examples in python-activerecord virtual environment:

```bash
# Activate virtual environment
.venv3.10\Scripts\activate

# Run sync stress test
python docs\examples\chapter_06_connection\connection_pool_stress_test_sync.py

# Run async stress test
python docs\examples\chapter_06_connection\connection_pool_stress_test_async.py
```

### MySQL (in python-activerecord-mysql project)

See `python-activerecord-mysql/docs/examples/` directory for MySQL-specific examples.

### PostgreSQL (in python-activerecord-postgres project)

See `python-activerecord-postgres/docs/examples/` directory for PostgreSQL-specific examples.

## Test Description

Each stress test:
1. Creates a connection pool with configurable min/max size (default: min=5, max=20)
2. Outputs backend threadsafety value for verification
3. Tests connection_mode (auto-detect based on threadsafety)
4. Runs multiple workers (default: 10 workers, 20 iterations each) that repeatedly acquire/release connections
5. Reports statistics (connections created/acquired/released)

### Current Test Parameters

| Parameter | Value |
|-----------|-------|
| min_size | 5 |
| max_size | 20 |
| workers | 10 |
| iterations | 20 |
| total queries | 200 |

### Expected Output

```
Pool configuration:
  min_size: 5
  max_size: 20
  connection_mode: auto
  validate_on_borrow: True
  validation_query: SELECT 1

Effective connection mode: transient  (for SQLite threadsafety=1)

Stress test results:
Total connections created: 10
Total acquired: 200
Total released: 200
Current available: 10
Current in use: 0
```

The test verifies:
- threadsafety value matches expected (SQLite=1, MySQL=1, PostgreSQL=2)
- connection_mode is correctly detected (transient for threadsafety<2, persistent for threadsafety>=2)
- All 200 queries execute successfully
- No connection leaks
- Pool closes cleanly
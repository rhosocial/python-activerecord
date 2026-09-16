# Backend Testing Guide

Backend projects typically need to verify code correctness at three different levels, each trading off between execution speed and realism. Understanding when to use each level helps you write tests that are both fast and thorough.

## Unit Testing: DummyBackend

Most business logic — query construction, field expression generation, validation rules — does not require a real database. rhosocial-activerecord ships with a built-in `DummyBackend` that is the default backend for all models. You never need to configure it.

When you build a query on a model that has not been configured with any backend, it automatically uses `DummyBackend`. You can call `to_sql()` at any point to get the exact SQL string and parameter tuple that would be sent to the database. This makes unit tests extremely fast — no I/O at all — and suitable for CI pipelines where database services are unavailable.

```python
from rhosocial.activerecord.model import ActiveRecord

class User(ActiveRecord):
    __table_name__ = "users"
    id: int
    username: str
    email: str

# No configuration needed — DummyBackend is the default

def test_user_query_generation():
    query = User.query().where(User.c.username == "alice")
    sql, params = query.to_sql()

    assert 'WHERE "users"."username" = ?' in sql
    assert params == ("alice",)
```

The limitation is obvious: you cannot execute queries. Calling `find()`, `save()`, or `all()` on a model with the default DummyBackend raises `DatabaseError: No backend configured`. For code that touches actual database operations, you need the next level.

## Integration Testing: SQLite Backend

When your tests need to verify that INSERT, SELECT, UPDATE, and DELETE actually work — or when you need to test transaction behavior, relation loading, or complex query execution — you explicitly configure the SQLite backend with an in-memory database.

This is the first point where you call `configure()`. Unlike DummyBackend, SQLite requires a configuration step because it needs to know where to find (or create) the database.

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig

config = SQLiteConnectionConfig(database=':memory:')
User.configure(config, SQLiteBackend)

# Now you can actually execute operations
user = User(username='alice', email='alice@example.com')
user.save()
assert user.id is not None

loaded = User.query().where(User.c.username == 'alice').one()
assert loaded.email == 'alice@example.com'
```

SQLite in-memory databases are created and destroyed within each test, so there is no cross-test contamination. They also run entirely in memory, making them fast enough for most integration test suites.

The trade-off is that SQLite behaves differently from MySQL or PostgreSQL in several important ways: it uses file-level locks instead of row-level locks, does not support `FOR UPDATE`, has a different set of built-in functions, and handles data types with different strictness. Tests that pass on SQLite may still fail on the target database.

## End-to-End Testing: Target Backend

End-to-end tests exercise the full stack against the actual database you deploy in production. This is where you discover real-world issues: connection timeout behavior, deadlock detection, charset handling, and database-specific SQL dialect differences.

```python
import os
from rhosocial.activerecord.backend.impl.mysql import MySQLBackend, MySQLConnectionConfig

config = MySQLConnectionConfig(
    host=os.environ.get('MYSQL_HOST', 'localhost'),
    port=int(os.environ.get('MYSQL_PORT', 3306)),
    database=os.environ.get('MYSQL_DATABASE', 'test'),
    username=os.environ.get('MYSQL_USER', 'root'),
    password=os.environ.get('MYSQL_PASSWORD', ''),
)
User.configure(config, MySQLBackend)
```

End-to-end tests are slower and require a running database, so they are typically run less frequently — before releases, in nightly builds, or on demand when investigating production issues. The `python-activerecord-testsuite` provides a standard set of feature tests that every backend must pass, ensuring behavioral consistency across databases.

## Choosing What to Test at Each Level

There is no hard rule, but a practical guideline is:

- **DummyBackend** (no configuration): Anything that builds SQL but does not execute it — field expressions, query construction, validation hooks, serialization logic.
- **SQLite** (explicit configuration): Anything that executes queries but does not depend on database-specific behavior — basic CRUD, relation loading, transaction boundaries, model lifecycle events.
- **Target backend** (explicit configuration): Anything that depends on the database's specific behavior — deadlock handling, charset sorting, type coercion differences, concurrency characteristics, backend-specific SQL extensions.

In practice, most test suites concentrate effort on the SQLite level for speed, use DummyBackend for quick feedback during development, and run target-backend tests in CI or pre-release.

## See Also

- [Core Testing Strategies](strategies.md) — deeper discussion of what to test at each layer
- [Dummy Backend](dummy.md) — detailed DummyBackend behavior and limitations
- [Testsuite Provider Guide](provider_guide.md) — how to implement a provider for the standard test suite

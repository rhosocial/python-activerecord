# Testsuite Provider Guide

The `python-activerecord-testsuite` defines a standard set of behavioral tests that every backend must pass. To run these tests against your database, you implement a **Provider** — a small module that knows how to create tables, manage connections, and clean up after each test.

The concept is straightforward: the test suite itself is database-agnostic. It calls generic operations like "create a table named `users`" and "insert a row into `posts`". The Provider translates these into the right SQL for your database and handles the lifecycle of the test environment.

## What a Provider Does

A Provider has two phases: setup and teardown.

During setup, the Provider creates the database schema (tables, indexes, and any custom types your database requires), opens a connection, and configures the test models to use your backend. The test suite then runs its standard test cases against this environment.

During teardown, the Provider must reverse everything it created — but in the right order. This is where most provider bugs appear.

### The Cleanup Order Problem

The cleanup must follow a specific sequence because each step depends on the database connection being alive:

1. **Drop tables first.** Tables contain data and may reference custom types. Dropping them removes dependencies.
2. **Drop custom types.** Some databases (notably PostgreSQL) allow user-defined types like ENUM or ARRAY. These must be dropped before the connection closes, because the type system is part of the connection state.
3. **Close cursors.** Unclosed cursors can cause resource leaks or, in some drivers, `RuntimeError` during iteration.
4. **Disconnect last.** Once the connection is closed, nothing else can run against it.

The common mistake is disconnecting before cleaning up. The connection is already gone, so the DROP TABLE statements fail silently or raise errors that get swallowed by the test framework. Tests appear to pass, but the database accumulates stale tables until the next test run hits "table already exists" errors.

```python
def teardown(self):
    try:
        # Correct order: clean up while connected
        for table in self.tables:
            self.connection.execute(f"DROP TABLE IF EXISTS {table}")
        # Drop custom types if your database uses them
        # Close cursors
    finally:
        # Disconnect last
        self.connection.disconnect()
```

### Common Provider Issues

Beyond the cleanup order, providers for different databases face distinct challenges:

**MySQL's async cursor problem.** When using the async MySQL backend, failing to close cursors before disconnecting can trigger `RuntimeError: Set changed size during iteration` because the driver's internal weak set of active cursors is modified during cleanup.

**PostgreSQL's custom types.** PostgreSQL allows you to define ENUM types, ARRAY types, and other custom types at the database level. If a test creates a custom type, the provider must drop it during teardown — and it must be dropped before the tables that reference it.

**Data contamination.** If a test inserts data and the provider does not clean it up, subsequent tests that depend on specific data states will fail unpredictably. This is especially insidious because the failures appear non-deterministic — they depend on test execution order.

## Writing a Provider

A typical provider module looks like this:

```python
class MyBackendProvider:
    def setup(self):
        """Create schema and configure models for testing."""
        self.connection = self._create_connection()
        self.connection.connect()
        self._create_tables()
        self._configure_models()

    def teardown(self):
        """Clean up in the correct order."""
        try:
            for table in self.tables:
                self.connection.execute(f"DROP TABLE IF EXISTS {table}")
        finally:
            self.connection.disconnect()

    def _create_connection(self):
        """Create a connection to the test database."""
        from rhosocial.activerecord.backend.impl.mysql import MySQLBackend, MySQLConnectionConfig
        config = MySQLConnectionConfig(
            host=os.environ.get('MYSQL_HOST', 'localhost'),
            database=os.environ.get('MYSQL_DATABASE', 'test'),
            username=os.environ.get('MYSQL_USER', 'root'),
            password=os.environ.get('MYSQL_PASSWORD', ''),
        )
        return MySQLBackend(config)

    def _create_tables(self):
        """Create the test schema."""
        self.connection.execute("CREATE TABLE IF NOT EXISTS users (...)")
        self.connection.execute("CREATE TABLE IF NOT EXISTS posts (...)")

    def _configure_models(self):
        """Point test models at this backend."""
        from tests.providers.basic import User, Post
        User.configure(self.connection.config, MySQLBackend)
        Post.__backend__ = User.backend()
```

The exact table schemas and model configurations depend on the test cases you are running. The `python-activerecord-testsuite` documentation describes what tables and models each feature test expects.

## See Also

- [Backend Testing Guide](backend_testing.md) — three-tier testing strategy
- [python-activerecord-testsuite](../../../python-activerecord-testsuite/docs/en_US/README.md) — test suite structure and feature tests

# Testing

## Testing Principles

The SQLite backend follows the project-wide testing conventions. These principles ensure consistent, maintainable test coverage across all backends.

### Sync/Async Parity

All tests involving IO operations must prepare **paired sync and async tests** for equivalent scenarios:

```python
# Sync test
def test_create_user():
    user = User(name="Alice").create()
    assert user.id is not None

# Async test — same logic, async API
async def test_async_create_user():
    user = await AsyncUser(name="Alice").create()
    assert user.id is not None
```

If a backend only supports sync or only async, prepare the corresponding tests only. For SQLite, both sync and async are supported, so both should be tested.

### Expression Tests — No IO

Expression tests involve no database IO — they only build SQL and validate the generated SQL:

```python
def test_expression_sql():
    expr = Eq(User.name, "Alice")
    assert expr.to_sql() == '"name" = ?'
    assert expr.params == ["Alice"]
```

No async counterpart is needed for expression tests since they perform no I/O.

### ActiveRecord Tests — Use Testsuite

ActiveRecord feature tests (model CRUD, relationships, queries) use the **testsuite**:

```bash
cd python-activerecord
PYTHONPATH=tests .venv3.14-ubuntu26.04/bin/pytest \
    ../python-activerecord-testsuite/src/rhosocial/activerecord/testsuite/feature/relation/
```

Each backend provides **provider implementations** that wire the tests to its specific database. The test logic is shared; only the provider layer changes per backend.

### Test Categories Summary

| What to Test | Approach | IO? | Async? |
|-------------|----------|-----|--------|
| Expression classes (dialect SQL generation) | Unit tests, no DB | No | No |
| Type adapters (type conversion) | Unit tests, no DB | No | No |
| Named features (expression, procedure, migration) | CLI scripts | Yes | If supported |
| ActiveRecord features (CRUD, relations, queries) | Testsuite + provider | Yes | Yes |
| SQLite-specific features (pragma, extensions) | Project-specific tests | Yes | Yes |

## Running SQLite Tests

### Provider Tests

```bash
cd python-activerecord
PYTHONPATH=tests .venv3.14-ubuntu26.04/bin/pytest tests/rhosocial/activerecord_test/feature/basic/
```

### Testsuite Tests

```bash
cd python-activerecord
PYTHONPATH=tests .venv3.14-ubuntu26.04/bin/pytest \
    ../python-activerecord-testsuite/src/rhosocial/activerecord/testsuite/feature/
```

### Expression Tests (No DB Required)

```bash
.venv3.14-ubuntu26.04/bin/pytest tests/ -k "expression"
```

## Provider Responsibilities

The SQLite backend uses an in-memory database by default for tests. The provider is responsible for:

- Creating the test database (usually `:memory:`)
- Configuring the backend and dialect
- Setting up and tearing down test data
- Providing model classes for the testsuite

See the [Core Testsuite Provider Guide](provider_guide.md) for implementation details.

## See Also

- [Core Backend Testing Guide](backend_testing.md)
- [Core Testsuite Provider Guide](provider_guide.md)
- [Troubleshooting](../troubleshooting/README.md)

💡 *AI Prompt:* "How do I write provider tests for a new backend?"

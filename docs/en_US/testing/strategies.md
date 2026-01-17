# Testing Strategies

## Zero-IO Testing

Using `DummyBackend`, you can test your model logic and query construction without a database.

```python
from rhosocial.activerecord.backend.impl.dummy import DummyBackend

def test_user_query():
    # Switch to Dummy backend
    User.configure(None, DummyBackend)

    # Execute query (actually just records the SQL, won't raise error)
    User.find_one({'name': 'alice'})

    # Verify if the generated SQL meets expectations
    last_op = User.backend().get_last_operation()
    assert "SELECT" in last_op.sql
    assert "alice" in last_op.params
```

## Integration Testing

Use the SQLite in-memory database (`:memory:`) for fast end-to-end testing.

```python
@pytest.fixture
def db():
    config = SQLiteConnectionConfig(database=':memory:')
    User.configure(config, SQLiteBackend)
    # ... create tables ...
    yield
    # ... cleanup ...
```

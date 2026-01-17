# Testing with DummyBackend

rhosocial-activerecord provides a special `DummyBackend` that allows you to test models and business logic without connecting to a real database. This is known as "Zero-IO" testing, which is extremely fast and requires no environment cleanup.

## What is DummyBackend?

`DummyBackend` is a storage backend that executes no SQL. It records all SQL operations and allows you to preset query return values.

## Enabling DummyBackend

Configure your models to use `DummyBackend` at the start of your tests.

```python
from rhosocial.activerecord.backend.impl.dummy import DummyBackend, DummyConnectionConfig

# Configure all models to use DummyBackend
User.configure(DummyConnectionConfig(), DummyBackend)
```

## Mocking Responses

You can intercept specific SQL patterns and return preset data.

```python
backend = User.backend()

# When querying the users table, return specific user data
backend.add_response(
    pattern="SELECT .* FROM users",
    data=[
        {"id": 1, "username": "test_user", "email": "test@example.com"}
    ]
)

# Now execute the query; it won't access the database but will return the preset data directly
user = User.find(1)
assert user.username == "test_user"
```

## Verifying Executed SQL

You can check which SQL statements the backend executed to verify if your query logic is correct.

```python
# Perform some operations
User.find(1)

# Get the last executed SQL
last_sql = backend.last_sql
print(last_sql)
# SELECT "users"."id", "users"."username", ... FROM "users" WHERE "users"."id" = ? LIMIT ?

# Get execution history
history = backend.execution_history
assert len(history) == 1
```

## Advantages

1.  **Extremely Fast**: No network or disk IO.
2.  **No Fixtures**: No need to prepare a database environment.
3.  **Deterministic**: Results are consistent every run.
4.  **SQL Verification**: You can precisely verify if the generated SQL meets expectations.

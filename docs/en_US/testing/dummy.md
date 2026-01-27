# Inspecting SQL with DummyBackend

`DummyBackend` is the default backend for rhosocial-activerecord and serves as a special "Zero-IO" backend. Its primary purpose is to verify SQL generation logic using standard SQL Dialect without connecting to a real database.

## Key Features

1.  **Default Backend**: When you haven't configured any specific database backend (like SQLite), the system defaults to using `DummyBackend` (or its async version `AsyncDummyBackend`).
2.  **Dialect Only**: It only provides a SQL Dialect implementation (`DummyDialect`) to support standard SQL construction.
3.  **No Execution Support**: It **does not** have any database execution capabilities. Attempting to execute queries (like `find`, `save`, `all`, etc.) will raise an error immediately.
4.  **Test-Friendly**: Unlike systems that require database connections to test SQL generation, our dummy backend allows complete testing of SQL generation logic without any external dependencies.
5.  **Immediate Verification**: Any expression can call `to_sql()` immediately to verify output, without needing to execute through complex query compilation pipelines.
6.  **No Mocking Support**: Unlike some testing frameworks, it **does not** support mocking responses (preset return values).

## Primary Use Case: SQL Generation Verification

`DummyBackend` is best suited for unit tests to verify that your query construction logic generates the expected SQL statements and parameter tuples.

### Example

```python
from rhosocial.activerecord.model import ActiveRecord

class User(ActiveRecord):
    __table_name__ = "users"
    id: int
    username: str
    email: str

# No backend configuration needed, defaults to DummyBackend

def test_user_query_generation():
    # 1. Build query
    query = User.query().where(User.c.username == "alice")
    
    # 2. Get generated SQL and parameters (no database connection triggered)
    sql, params = query.to_sql()
    
    # 3. Verify
    print(f"SQL: {sql}")
    print(f"Params: {params}")
    
    assert 'SELECT "users".* FROM "users"' in sql
    assert 'WHERE "users"."username" = ?' in sql
    assert params == ("alice",)
```

## Important Note

If you attempt to execute a query, you will receive an error:

```python
# This will raise an error because DummyBackend does not support actual operations
try:
    User.query().where(User.c.id == 1).one()
except Exception as e:
    print(e) 
    # Output: DummyBackend does not support real database operations. Did you forget to configure a concrete backend?
```

## Summary

`DummyBackend` is a lightweight tool for ensuring your code generates correct SQL structures. If you need integration testing or actual data interaction, please use `SQLiteBackend` (supports in-memory mode `:memory:`) or other real database backends.

# Transaction Support

## Overview

The SQLite backend provides complete transaction management through a transaction manager that wraps SQLite's transaction semantics. SQLite supports transactions with SERIALIZABLE isolation by default.

## Transaction Manager

### Synchronous

```python
# Using the transaction manager
with User.transaction():
    user = User(username='alice')
    user.save()
    # Transaction commits on successful exit
    # Transaction rolls back on exception
```

### Asynchronous

```python
# Using the async transaction manager
async with User.transaction():
    user = User(username='alice')
    await user.save()
    # Transaction commits on successful exit
    # Transaction rolls back on exception
```

The transaction manager has both sync and async variants:
- `SQLiteTransactionManager` — synchronous
- `AsyncSQLiteTransactionManager` — asynchronous

The API is identical — the only difference is `async with` vs `with`.

### Manual Transaction Control

```python
# Manual transaction via backend
backend = SQLiteBackend(database=":memory:")
backend.connect()

with backend.transaction():
    backend.execute("INSERT INTO users (name) VALUES (?)", ("Alice",))
    backend.execute("INSERT INTO users (name) VALUES (?)", ("Bob",))
    # Commits on successful exit

# Transaction with explicit rollback
try:
    with backend.transaction():
        backend.execute("INSERT INTO users (name) VALUES (?)", ("Alice",))
        raise ValueError("Something went wrong")  # Rolls back
except ValueError:
    pass  # Alice was not inserted
```

## Savepoints

SQLite supports savepoints for nested transactions. Each nested `transaction()` call creates a savepoint, allowing partial rollback within a larger transaction.

```python
with backend.transaction():          # Outer transaction
    backend.execute("INSERT INTO users (name) VALUES (?)", ("Alice",))
    
    with backend.transaction():      # Creates savepoint
        backend.execute("INSERT INTO users (name) VALUES (?)", ("Bob",))
        # Rolls back to savepoint on exception, outer transaction continues
    
    # Alice is still committed (if outer transaction succeeds)
```

### Savepoint Behavior

| Scenario | Result |
|----------|--------|
| Inner transaction succeeds | Savepoint released, outer transaction continues |
| Inner transaction raises exception | Rolled back to savepoint, outer transaction continues |
| Outer transaction succeeds | All changes committed |
| Outer transaction raises exception | Everything rolled back |

## Isolation Level

SQLite uses SERIALIZABLE isolation by default, which is the strictest isolation level. This prevents dirty reads, non-repeatable reads, and phantom reads.

### SQLite Isolation Characteristics

| Isolation Level | Behavior |
|----------------|----------|
| SERIALIZABLE (default) | Full isolation; transactions appear to execute serially |
| DEFERRED | Acquires lock on first read (default for `BEGIN`) |
| IMMEDIATE | Acquires RESERVED lock on start |
| EXCLUSIVE | Acquires EXCLUSIVE lock on start |

### BEGIN Statement Variants

SQLite supports three BEGIN modes:

```python
# DEFERRED (default) — no lock until first read/write
BEGIN DEFERRED TRANSACTION

# IMMEDIATE — RESERVED lock acquired immediately
BEGIN IMMEDIATE TRANSACTION

# EXCLUSIVE — EXCLUSIVE lock acquired immediately
BEGIN EXCLUSIVE TRANSACTION
```

In rhosocial-activerecord, the transaction manager uses `BEGIN DEFERRED` by default. The lock is acquired lazily on the first database operation.

### Concurrent Access

SQLite uses file-level locking for concurrency. When one connection holds a write lock, other connections block until the lock is released.

```python
# Connection A
with backend.transaction():
    backend.execute("INSERT INTO users (name) VALUES (?)", ("Alice",))
    # Holds write lock until commit

# Connection B — blocks until Connection A commits
with backend.transaction():
    backend.execute("INSERT INTO users (name) VALUES (?)", ("Bob",))
```

For better concurrency, consider using WAL mode (see [Pragma System](../pragma.md)).

## See Also

- [Pragma System](../pragma.md) — Configure journal mode and locking behavior
- [Troubleshooting](../troubleshooting/README.md) — Database locked errors
- [Core: Parallel Worker Patterns](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/scenarios/parallel_workers)

💡 *AI Prompt:* "How do I handle database locked errors in SQLite with concurrent writes?"

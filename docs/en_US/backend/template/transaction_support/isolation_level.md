# Transaction Isolation Levels

## Overview

{database} supports several transaction isolation levels that control how transaction integrity is visible to other transactions.

## Available Isolation Levels

| Isolation Level | Dirty Read | Non-Repeatable Read | Phantom Read |
|----------------|------------|---------------------|--------------|
| READ UNCOMMITTED | Possible | Possible | Possible |
| READ COMMITTED | Prevented | Possible | Possible |
| REPEATABLE READ | Prevented | Prevented | Possible |
| SERIALIZABLE | Prevented | Prevented | Prevented |

<!-- Document backend-specific defaults and behavior -->

## Setting Isolation Level

### Synchronous

```python
# Set isolation level for a transaction
with User.transaction(isolation_level='READ COMMITTED'):
    user = User.query().where(User.c.id == 1).one()
    user.name = 'updated'
    user.save()
```

### Asynchronous

```python
# Set isolation level for a transaction (async)
async with User.transaction(isolation_level='READ COMMITTED'):
    user = await User.query().where(User.c.id == 1).one()
    user.name = 'updated'
    await user.save()
```

## Isolation Level Details

### READ COMMITTED

<!-- Document backend-specific behavior -->

### REPEATABLE READ

<!-- Document backend-specific behavior, default level, MVCC details -->

### SERIALIZABLE

<!-- Document backend-specific behavior, when to use -->

## See Also

- [Deadlock Handling](deadlock.md) — deadlock detection and retry

# Savepoint

## Overview

Savepoints allow you to create checkpoints within a transaction and roll back to a specific point without aborting the entire transaction. This is useful for conditional operations where part of a transaction may fail.

## Using Savepoints

```python
with User.transaction() as tm:
    user = User(username='alice')
    user.save()

    # Create a savepoint
    sp = tm.savepoint()

    try:
        # This might fail
        post = Post(title='Hello', author_id=user.id)
        post.save()
    except Exception:
        # Roll back to savepoint, keep the user
        tm.rollback_savepoint(sp)
```

## Async Savepoints

```python
async with AsyncUser.transaction() as tm:
    user = AsyncUser(username='alice')
    await user.save()

    sp = await tm.savepoint()

    try:
        post = AsyncPost(title='Hello', author_id=user.id)
        await post.save()
    except Exception:
        await tm.rollback_savepoint(sp)
```

## Use Cases

### Conditional Operations

```python
with Order.transaction() as tm:
    order = Order(user_id=user.id, total=100)
    order.save()

    sp = tm.savepoint()
    try:
        # Try to apply discount
        discount = Discount.find_one(coupon_code)
        order.total -= discount.amount
        order.save()
    except Exception:
        # Discount failed, continue without it
        tm.rollback_savepoint(sp)
```

### Error Recovery

```python
with User.transaction() as tm:
    sp = tm.savepoint()

    try:
        # Risky operation
        process_import(data)
    except ImportError:
        tm.rollback_savepoint(sp)
        # Continue with other work
```

## See Also

- [Isolation Levels](isolation_level.md) — transaction isolation
- [Deadlock Handling](deadlock.md) — deadlock detection

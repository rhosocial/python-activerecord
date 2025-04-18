# Isolation Level Configuration

Transaction isolation levels determine how transactions interact with each other, particularly when multiple transactions are running concurrently. rhosocial ActiveRecord supports standard SQL isolation levels and provides a flexible way to configure them.

## Understanding Isolation Levels

Isolation levels control the degree to which one transaction must be isolated from resource or data modifications made by other transactions. Higher isolation levels increase data consistency but may reduce concurrency and performance.

rhosocial ActiveRecord supports the following standard isolation levels through the `IsolationLevel` enum:

| Isolation Level | Description | Prevents |
|----------------|-------------|----------|
| `READ_UNCOMMITTED` | Lowest isolation level | None |
| `READ_COMMITTED` | Prevents dirty reads | Dirty reads |
| `REPEATABLE_READ` | Prevents non-repeatable reads | Dirty reads, non-repeatable reads |
| `SERIALIZABLE` | Highest isolation level | Dirty reads, non-repeatable reads, phantom reads |

### Concurrency Phenomena

- **Dirty Read**: A transaction reads data written by a concurrent uncommitted transaction.
- **Non-repeatable Read**: A transaction re-reads data it has previously read and finds that data has been modified by another transaction.
- **Phantom Read**: A transaction re-executes a query returning a set of rows that satisfy a search condition and finds that the set of rows has changed due to another transaction.

## Setting Isolation Levels

You can set the isolation level for transactions in several ways:

### Setting Default Isolation Level for a Backend

```python
from rhosocial.activerecord.backend import IsolationLevel

# Get the backend instance
backend = User.backend()

# Set the isolation level for future transactions
backend.transaction_manager.isolation_level = IsolationLevel.SERIALIZABLE
```

### Setting Isolation Level for a Specific Transaction

Some database backends allow setting the isolation level at the beginning of a transaction:

```python
# For PostgreSQL
from rhosocial.activerecord.backend.impl.pgsql import PostgreSQLTransactionManager

# Get the transaction manager
tx_manager = User.backend().transaction_manager

# Set isolation level before beginning transaction
tx_manager.isolation_level = IsolationLevel.REPEATABLE_READ

# Begin transaction with this isolation level
with User.transaction():
    # Operations run with REPEATABLE_READ isolation
    user = User.find(1)
    user.name = "New Name"
    user.save()
```

## Database-Specific Isolation Level Support

Different database systems have different default isolation levels and may implement isolation levels differently:

### MySQL/MariaDB

- Default: `REPEATABLE_READ`
- Supports all standard isolation levels
- Implementation uses a combination of locking and multi-version concurrency control (MVCC)

```python
from rhosocial.activerecord.backend.impl.mysql import MySQLTransactionManager
from rhosocial.activerecord.backend import IsolationLevel

# MySQL-specific transaction manager
tx_manager = User.backend().transaction_manager
assert isinstance(tx_manager, MySQLTransactionManager)

# Set isolation level
tx_manager.isolation_level = IsolationLevel.READ_COMMITTED
```

### PostgreSQL

- Default: `READ_COMMITTED`
- Supports all standard isolation levels
- Implementation uses MVCC
- Unique feature: `SERIALIZABLE` transactions can be `DEFERRABLE`

```python
from rhosocial.activerecord.backend.impl.pgsql import PostgreSQLTransactionManager
from rhosocial.activerecord.backend import IsolationLevel

# PostgreSQL-specific transaction manager
tx_manager = User.backend().transaction_manager
assert isinstance(tx_manager, PostgreSQLTransactionManager)

# Set isolation level
tx_manager.isolation_level = IsolationLevel.SERIALIZABLE
```

### SQLite

- Default behavior is similar to `SERIALIZABLE`
- Limited support for configuring different isolation levels

## Changing Isolation Levels

Important note: You cannot change the isolation level of an active transaction. Attempting to do so will raise an `IsolationLevelError`:

```python
from rhosocial.activerecord.backend import IsolationLevel
from rhosocial.activerecord.backend.errors import IsolationLevelError

tx_manager = User.backend().transaction_manager

# Begin transaction
User.backend().begin_transaction()

try:
    # This will raise IsolationLevelError
    tx_manager.isolation_level = IsolationLevel.SERIALIZABLE
except IsolationLevelError as e:
    print("Cannot change isolation level during active transaction")
finally:
    User.backend().rollback_transaction()
```

## Checking Current Isolation Level

You can check the current isolation level using the `isolation_level` property:

```python
from rhosocial.activerecord.backend import IsolationLevel

tx_manager = User.backend().transaction_manager
current_level = tx_manager.isolation_level

if current_level == IsolationLevel.SERIALIZABLE:
    print("Using highest isolation level")
```

Some database backends also provide a method to get the actual isolation level from the database server:

```python
# For PostgreSQL
from rhosocial.activerecord.backend.impl.pgsql import PostgreSQLTransactionManager

tx_manager = User.backend().transaction_manager
assert isinstance(tx_manager, PostgreSQLTransactionManager)

# Get current isolation level from server
current_level = tx_manager.get_current_isolation_level()
```

## Best Practices

1. **Choose the right isolation level**: Higher isolation levels provide stronger guarantees but may reduce performance
2. **Set isolation level before beginning transaction**: Cannot be changed once transaction has started
3. **Be aware of database-specific behavior**: Different databases implement isolation levels differently
4. **Consider application requirements**: Balance between data consistency and performance
5. **Test with realistic workloads**: Isolation level choice can significantly impact application performance

## Next Steps

- Learn about [Nested Transactions](nested_transactions.md)
- Explore [Savepoints](savepoints.md)
- Understand [Error Handling in Transactions](error_handling_in_transactions.md)
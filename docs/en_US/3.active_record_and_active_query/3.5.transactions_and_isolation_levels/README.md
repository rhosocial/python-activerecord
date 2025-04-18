# Transactions & Isolation Levels

Transactions are a fundamental concept in database management systems that ensure data integrity by grouping a set of operations into a single logical unit. rhosocial ActiveRecord provides comprehensive transaction support with various isolation levels to meet different application requirements.

## Contents

- [Transaction Management](transaction_management.md) - Learn how to manage database transactions
- [Isolation Level Configuration](isolation_level_configuration.md) - Configure transaction isolation levels
- [Nested Transactions](nested_transactions.md) - Work with transactions inside transactions
- [Savepoints](savepoints.md) - Create and manage savepoints within transactions
- [Error Handling in Transactions](error_handling_in_transactions.md) - Handle errors and exceptions in transactions

## Overview

Transactions in rhosocial ActiveRecord follow the ACID properties:

- **Atomicity**: All operations within a transaction succeed or fail together
- **Consistency**: A transaction brings the database from one valid state to another
- **Isolation**: Concurrent transactions do not interfere with each other
- **Durability**: Once a transaction is committed, it remains so

The framework provides both explicit transaction management through method calls and a convenient context manager interface for transaction blocks.

```python
# Using context manager (recommended)
with User.transaction():
    user1.save()
    user2.save()
    # Both users are saved or neither is saved

# Using explicit transaction management
User.backend().begin_transaction()
try:
    user1.save()
    user2.save()
    User.backend().commit_transaction()
except Exception:
    User.backend().rollback_transaction()
    raise
```

The transaction system in rhosocial ActiveRecord is designed to be database-agnostic while still allowing access to database-specific features when needed.
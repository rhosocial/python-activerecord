# Version Control and Optimistic Locking

Optimistic locking is a concurrency control method that allows multiple users to access the same record for editing, while preventing inadvertent overwrites of changes. rhosocial ActiveRecord provides the `OptimisticLockMixin` to implement this pattern in your models.

## Overview

The `OptimisticLockMixin` adds a `version` field to your model. Each time a record is updated, this version number is incremented. Before saving changes, the system verifies that the version number in the database matches the version number when the record was loaded. If they don't match, it means someone else has modified the record in the meantime, and an error is raised.

This approach is called "optimistic" because it assumes conflicts are rare and only checks for them at save time, rather than locking records preemptively.

## Basic Usage

To add optimistic locking to your model, include the `OptimisticLockMixin` in your class definition:

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import OptimisticLockMixin

class Account(OptimisticLockMixin, ActiveRecord):
    __tablename__ = 'accounts'
    
    name: str
    balance: float
```

With this setup, the `version` field will be automatically managed:

```python
# Create a new account
account = Account(name="John Doe", balance=1000.0)
account.save()

# The version is set to 1 for new records
print(account.version)  # 1

# Update the account
account.balance = 1500.0
account.save()

# The version is automatically incremented
print(account.version)  # 2

# If another process updates the same record
# before you save your changes, an error will be raised
```

## Handling Concurrent Updates

When a concurrent update is detected, a `DatabaseError` is raised. You can catch this exception and handle it appropriately:

```python
from rhosocial.activerecord.backend import DatabaseError

try:
    account.balance += 100.0
    account.save()
except DatabaseError as e:
    if "Record was updated by another process" in str(e):
        # Handle the conflict
        # For example, reload the record and reapply the changes
        fresh_account = Account.find(account.id)
        fresh_account.balance += 100.0
        fresh_account.save()
    else:
        # Handle other database errors
        raise
```

## How It Works

The `OptimisticLockMixin` works by:

1. Adding a `version` field to your model (stored as a private attribute `_version`)
2. Registering a handler for the `AFTER_SAVE` event to update the version
3. Adding a version check condition to update queries
4. Incrementing the version number after successful updates

Here's a simplified view of the implementation:

```python
class OptimisticLockMixin(IUpdateBehavior, IActiveRecord):
    _version: Version = Version(value=1, increment_by=1)

    def __init__(self, **data):
        super().__init__(**data)
        version_value = data.get('version', 1)
        self._version = Version(value=version_value, increment_by=1)
        self.on(ModelEvent.AFTER_SAVE, self._handle_version_after_save)

    @property
    def version(self) -> int:
        return self._version.value

    def get_update_conditions(self):
        # Add version check to update conditions
        condition, params = self._version.get_update_condition()
        return [(condition, params)]

    def get_update_expressions(self):
        # Add version increment to update expressions
        return {
            self._version.db_column: self._version.get_update_expression(self.backend())
        }

    def _handle_version_after_save(self, instance, is_new=False, result=None, **kwargs):
        if not is_new:
            if result.affected_rows == 0:
                raise DatabaseError("Record was updated by another process")
            self._version.increment()
```

## Database Considerations

To use optimistic locking, your database table must include a column for the version number. By default, this column is named `version` and should be an integer type. You can customize the column name by modifying the `_version` attribute's `db_column` property.

Example SQL for creating a table with version support:

```sql
CREATE TABLE accounts (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    balance DECIMAL(10, 2) NOT NULL,
    version INTEGER NOT NULL DEFAULT 1
);
```

## Combining with Other Mixins

The `OptimisticLockMixin` works well with other mixins like `TimestampMixin` and `SoftDeleteMixin`:

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import TimestampMixin, OptimisticLockMixin, SoftDeleteMixin

class Account(TimestampMixin, OptimisticLockMixin, SoftDeleteMixin, ActiveRecord):
    __tablename__ = 'accounts'
    
    name: str
    balance: float
```

With this setup, you'll have:
- `created_at`: When the record was created
- `updated_at`: When the record was last updated
- `version`: The current version number for optimistic locking
- `deleted_at`: When the record was soft-deleted (or `None` if not deleted)

## Best Practices

1. **Use with Timestamp Fields**: Combining optimistic locking with timestamp fields provides both version control and timing information.

2. **Handle Conflicts Gracefully**: Provide user-friendly ways to resolve conflicts when they occur.

3. **Consider Performance**: Optimistic locking adds an extra condition to every update query, which may impact performance in high-volume systems.

4. **Custom Increment Values**: For frequently updated records, consider using a larger increment value to avoid hitting integer limits.

## Next Steps

Now that you understand optimistic locking, you might want to explore:

- [Pessimistic Locking Strategies](pessimistic_locking_strategies.md) - For stronger concurrency control
- [Soft Delete Mechanism](soft_delete_mechanism.md) - For logical deletion of records
- [Custom Fields](custom_fields.md) - For extending model capabilities
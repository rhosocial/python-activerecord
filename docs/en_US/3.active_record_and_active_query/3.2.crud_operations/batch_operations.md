# Batch Operations

> **⚠️ PARTIALLY IMPLEMENTED/PLANNED**: Batch operations functionality is either not implemented or only partially implemented. The API described in this document may not reflect actual implemented functionality. Current users should rely on individual record operations only. This feature may be developed in future releases with no guaranteed timeline.

> **⚠️ ASPIRATIONAL DOCUMENTATION**: This document describes planned batch operations in rhosocial ActiveRecord, which would allow you to efficiently perform operations on multiple records at once. **This functionality is not currently available.**

## Batch Creation

When you need to insert multiple records at once, batch creation can significantly improve performance by reducing the number of database queries.

### Creating Multiple Records

```python
# Prepare multiple user records
users = [
    User(username="user1", email="user1@example.com"),
    User(username="user2", email="user2@example.com"),
    User(username="user3", email="user3@example.com")
]

# Insert all records in a single batch operation
User.batch_insert(users)

# After batch insertion, each model instance will have its primary key set
for user in users:
    print(f"User {user.username} has ID: {user.id}")
```

### Batch Creation with Dictionaries

You can also use dictionaries for batch creation:

```python
user_data = [
    {"username": "user4", "email": "user4@example.com"},
    {"username": "user5", "email": "user5@example.com"},
    {"username": "user6", "email": "user6@example.com"}
]

# Insert all records from dictionaries
User.batch_insert_from_dicts(user_data)
```

### Validation in Batch Creation

By default, validation is performed for each record during batch creation. You can skip validation if needed:

```python
# Skip validation during batch insert
User.batch_insert(users, validate=False)
```

### Performance Considerations

- Batch operations are significantly faster than individual inserts for large datasets
- Consider memory usage when working with very large collections
- For extremely large datasets, consider chunking your data into smaller batches

```python
# Process a large dataset in chunks of 1000 records
chunk_size = 1000
for i in range(0, len(large_dataset), chunk_size):
    chunk = large_dataset[i:i+chunk_size]
    User.batch_insert(chunk)
```

## Batch Updates

Batch updates allow you to update multiple records with a single query.

### Updating Multiple Records with the Same Values

```python
# Update all users with status 'inactive' to 'archived'
affected_rows = User.query()\
    .where({"status": "inactive"})\
    .update({"status": "archived"})

print(f"Updated {affected_rows} records")
```

### Conditional Batch Updates

You can use more complex conditions for batch updates:

```python
# Update all users who haven't logged in for 30 days
from datetime import datetime, timedelta
inactive_date = datetime.now() - timedelta(days=30)

affected_rows = User.query()\
    .where("last_login < ?", inactive_date)\
    .update({"status": "inactive"})
```

### Updating with Expressions

You can use expressions to update values based on existing values:

```python
# Increment the login_count for all active users
from rhosocial.activerecord.query.expression import Expression

User.query()\
    .where({"status": "active"})\
    .update({"login_count": Expression("login_count + 1")})
```

## Batch Deletes

Batch deletes allow you to remove multiple records with a single query.

### Deleting Multiple Records

```python
# Delete all users with status 'temporary'
affected_rows = User.query()\
    .where({"status": "temporary"})\
    .delete()

print(f"Deleted {affected_rows} records")
```

### Conditional Batch Deletes

You can use complex conditions for batch deletes:

```python
# Delete all inactive users created more than a year ago
old_date = datetime.now() - timedelta(days=365)

affected_rows = User.query()\
    .where({"status": "inactive"})\
    .where("created_at < ?", old_date)\
    .delete()
```

### Soft Deletes in Batch Operations

If your model uses `SoftDeleteMixin`, batch deletes will mark records as deleted rather than removing them:

```python
# Mark all inactive users as deleted
User.query()\
    .where({"status": "inactive"})\
    .delete()  # Records are soft-deleted

# Force actual deletion even with SoftDeleteMixin
User.query()\
    .where({"status": "inactive"})\
    .hard_delete()  # Records are permanently removed
```

## Optimizing Batch Operations

### Using Transactions for Batch Operations

Wrapping batch operations in transactions can improve performance and ensure atomicity:

```python
from rhosocial.activerecord.backend.transaction import Transaction

# Perform multiple batch operations in a single transaction
with Transaction():
    # Delete old records
    User.query().where("created_at < ?", old_date).delete()
    
    # Update existing records
    User.query().where({"status": "trial"}).update({"status": "active"})
    
    # Insert new records
    User.batch_insert(new_users)
```

### Disabling Triggers and Constraints

For very large batch operations, you might consider temporarily disabling triggers or constraints:

```python
# Example of disabling triggers for a large batch operation
# (Implementation depends on the specific database backend)
from rhosocial.activerecord.backend import get_connection

conn = get_connection()
with conn.cursor() as cursor:
    # Disable triggers (PostgreSQL example)
    cursor.execute("ALTER TABLE users DISABLE TRIGGER ALL")
    
    try:
        # Perform batch operation
        User.batch_insert(huge_dataset)
    finally:
        # Re-enable triggers
        cursor.execute("ALTER TABLE users ENABLE TRIGGER ALL")
```

## Summary

Batch operations in rhosocial ActiveRecord provide efficient ways to perform operations on multiple records. By using these features, you can significantly improve the performance of your application when working with large datasets.
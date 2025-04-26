# Soft Delete Mechanism

Soft deletion is a pattern where records are marked as deleted instead of being physically removed from the database. rhosocial ActiveRecord provides the `SoftDeleteMixin` to implement this pattern in your models.

## Overview

The `SoftDeleteMixin` adds a `deleted_at` timestamp field to your model. When a record is "deleted", this field is set to the current timestamp instead of removing the record from the database. This allows you to:

- Maintain a history of all records, including deleted ones
- Implement "trash" or "recycle bin" functionality
- Recover accidentally deleted records
- Maintain referential integrity in related records

## Basic Usage

To add soft delete functionality to your model, include the `SoftDeleteMixin` in your class definition:

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import SoftDeleteMixin

class Article(SoftDeleteMixin, ActiveRecord):
    __tablename__ = 'articles'
    
    title: str
    content: str
```

With this setup, calling `delete()` on an article will mark it as deleted instead of removing it:

```python
# Create a new article
article = Article(title="Hello World", content="This is my first article")
article.save()

# Soft delete the article
article.delete()

# The article is now marked as deleted
print(article.deleted_at)  # Current datetime when deleted

# The record still exists in the database but won't be returned by default queries
```

## Querying Soft-Deleted Records

The `SoftDeleteMixin` modifies the default query behavior to exclude soft-deleted records. It provides additional methods for working with deleted records:

```python
# Default query - returns only non-deleted records
articles = Article.query().all()

# Include deleted records in the query
all_articles = Article.query_with_deleted().all()

# Query only deleted records
deleted_articles = Article.query_only_deleted().all()
```

## Restoring Soft-Deleted Records

You can restore a soft-deleted record using the `restore()` method:

```python
# Find a deleted article
deleted_article = Article.query_only_deleted().first()

# Restore the article
deleted_article.restore()

# The article is now restored (deleted_at is set to None)
print(deleted_article.deleted_at)  # None
```

## How It Works

The `SoftDeleteMixin` works by:

1. Adding a nullable `deleted_at` timestamp field to your model
2. Registering a handler for the `BEFORE_DELETE` event to set the timestamp
3. Overriding the default query method to filter out deleted records
4. Providing additional query methods for working with deleted records
5. Implementing a `restore()` method to undelete records

Here's a simplified view of the implementation:

```python
class SoftDeleteMixin(IActiveRecord):
    deleted_at: Optional[datetime] = Field(default=None)

    def __init__(self, **data):
        super().__init__(**data)
        self.on(ModelEvent.BEFORE_DELETE, self._mark_as_deleted)

    def _mark_as_deleted(self, instance, **kwargs):
        instance.deleted_at = datetime.now(tzlocal.get_localzone())

    def prepare_delete(self):
        return {'deleted_at': self.deleted_at}

    @classmethod
    def query(cls):
        return super().query().where("deleted_at IS NULL")

    @classmethod
    def query_with_deleted(cls):
        return super().query()

    @classmethod
    def query_only_deleted(cls):
        return super().query().where("deleted_at IS NOT NULL")

    def restore(self):
        # Implementation to set deleted_at to None and save
```

## Combining with Other Mixins

The `SoftDeleteMixin` works well with other mixins like `TimestampMixin`:

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import TimestampMixin, SoftDeleteMixin

class Article(TimestampMixin, SoftDeleteMixin, ActiveRecord):
    __tablename__ = 'articles'
    
    title: str
    content: str
```

With this setup, you'll have:
- `created_at`: When the record was created
- `updated_at`: When the record was last updated
- `deleted_at`: When the record was soft-deleted (or `None` if not deleted)

## Batch Operations

Soft delete also works with batch operations:

```python
# Soft delete multiple articles
Article.delete_all({"author_id": 123})

# All matching articles are now marked as deleted, not physically removed
```

## Database Considerations

Soft delete adds an additional column to your database table and modifies query behavior. Consider the following:

- **Indexes**: You may want to add an index on the `deleted_at` column for performance
- **Unique Constraints**: If you have unique constraints, they may need to include `deleted_at` to allow "deleted" duplicates
- **Cascading Deletes**: You'll need to handle cascading soft deletes in your application code

## Best Practices

1. **Be Consistent**: Use soft delete consistently across related models
2. **Consider Hard Delete Options**: For some data (like personal information), you might need a true hard delete option for compliance reasons
3. **Periodic Cleanup**: Consider implementing a process to permanently remove very old soft-deleted records
4. **UI Clarity**: Make it clear to users when they're viewing data that includes or excludes deleted records

## Next Steps

Now that you understand soft delete, you might want to explore:

- [Version Control and Optimistic Locking](version_control_and_optimistic_locking.md) - For managing concurrent updates
- [Pessimistic Locking Strategies](pessimistic_locking_strategies.md) - For stronger concurrency control
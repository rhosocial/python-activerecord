# Timestamp Fields

Timestamp fields are essential for tracking when records are created and updated. rhosocial ActiveRecord provides the `TimestampMixin` to automatically manage these fields for you.

## Overview

The `TimestampMixin` adds two datetime fields to your model:

- `created_at`: Records when the record was first created
- `updated_at`: Records when the record was last updated

These fields are automatically maintained by the mixin, which hooks into the model's lifecycle events to update the timestamps appropriately.

## Basic Usage

To add timestamp functionality to your model, simply include the `TimestampMixin` in your class definition:

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import TimestampMixin

class Article(TimestampMixin, ActiveRecord):
    __tablename__ = 'articles'
    
    title: str
    content: str
```

With this setup, the `created_at` and `updated_at` fields will be automatically managed:

```python
# Create a new article
article = Article(title="Hello World", content="This is my first article")
article.save()

# The timestamps are automatically set
print(article.created_at)  # Current datetime when created
print(article.updated_at)  # Same as created_at initially

# Update the article
article.content = "Updated content"
article.save()

# updated_at is automatically updated, created_at remains unchanged
print(article.updated_at)  # Current datetime when updated
```

## How It Works

The `TimestampMixin` works by:

1. Defining `created_at` and `updated_at` fields with default values set to the current time
2. Registering a handler for the `BEFORE_SAVE` event
3. In the event handler, updating the timestamps based on whether the record is new or existing

Here's a simplified view of the implementation:

```python
class TimestampMixin(IActiveRecord):
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone))

    def __init__(self, **data):
        super().__init__(**data)
        self.on(ModelEvent.BEFORE_SAVE, self._update_timestamps)

    def _update_timestamps(self, instance, is_new: bool, **kwargs):
        now = datetime.now(timezone)
        if is_new:
            instance.created_at = now
        instance.updated_at = now
```

## Timezone Handling

By default, the `TimestampMixin` uses the local timezone for timestamp values. You can customize this behavior by setting the `__timezone__` class attribute:

```python
import pytz
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import TimestampMixin

class Article(TimestampMixin, ActiveRecord):
    __tablename__ = 'articles'
    __timezone__ = pytz.timezone('UTC')  # Use UTC for timestamps
    
    title: str
    content: str
```

## Customizing Timestamp Behavior

You can customize the timestamp behavior by extending the `TimestampMixin` and overriding the `_update_timestamps` method:

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import TimestampMixin

class CustomTimestampMixin(TimestampMixin):
    last_viewed_at: datetime = None
    
    def _update_timestamps(self, instance, is_new: bool, **kwargs):
        # Call the parent implementation first
        super()._update_timestamps(instance, is_new, **kwargs)
        
        # Add custom behavior
        if not is_new and kwargs.get('is_view', False):
            instance.last_viewed_at = datetime.now(self.__timezone__)

class Article(CustomTimestampMixin, ActiveRecord):
    __tablename__ = 'articles'
    
    title: str
    content: str
    
    def view(self):
        # Custom method that updates last_viewed_at
        self.save(is_view=True)
```

## Database Considerations

Different databases handle datetime fields differently:

- **SQLite**: Stores timestamps as ISO8601 strings
- **MySQL/MariaDB**: Uses `DATETIME` or `TIMESTAMP` types
- **PostgreSQL**: Uses `TIMESTAMP` or `TIMESTAMP WITH TIME ZONE` types

rhosocial ActiveRecord handles these differences for you, ensuring consistent behavior across database backends.

## Best Practices

1. **Always Include Timestamps**: It's a good practice to include timestamp fields in all your models for auditing and debugging purposes
2. **Use UTC**: For applications that span multiple timezones, consider using UTC for all timestamps
3. **Consider Additional Audit Fields**: For more comprehensive auditing, consider adding fields like `created_by` and `updated_by`

## Next Steps

Now that you understand timestamp fields, you might want to explore:

- [Soft Delete Mechanism](soft_delete_mechanism.md) - For implementing logical deletion
- [Version Control and Optimistic Locking](version_control_and_optimistic_locking.md) - For managing concurrent updates
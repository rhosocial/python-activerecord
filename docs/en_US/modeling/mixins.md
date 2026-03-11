# Mixins

Composition over inheritance. `rhosocial-activerecord` encourages using Mixins to reuse common fields and logic.

## Built-in Mixins

The framework provides several common Mixins:

### UUIDMixin

Uses UUID as the primary key.

```python
from rhosocial.activerecord.field import UUIDMixin

class User(UUIDMixin, ActiveRecord):
    # Automatically gets: id: uuid.UUID (Primary Key)
    pass
```

### TimestampMixin

Automatically records creation and update times.

```python
from rhosocial.activerecord.field import TimestampMixin

class Post(TimestampMixin, ActiveRecord):
    # Automatically gets:
    # created_at: datetime (UTC timezone)
    # updated_at: datetime (UTC timezone)
    pass
```

#### Timestamp Generation Strategy

`TimestampMixin` uses **Python-side timestamp generation** instead of relying on database `CURRENT_TIMESTAMP` functions.

**Design Rationale**:

1. **Format Consistency**: Insert and update operations use the same UTC datetime format (ISO 8601), avoiding data format inconsistencies.
   
   If using database `CURRENT_TIMESTAMP`:
   - On insert: Python generates UTC datetime (e.g., `2024-01-15T10:30:00+00:00`)
   - On update: Database generates timestamp (format may vary by database)
   - Result: Same field has two different formats

2. **Cross-Database Compatibility**: Different databases handle `CURRENT_TIMESTAMP` differently:
   - SQLite: Returns local time string
   - PostgreSQL: Returns timestamp with timezone
   - MySQL: Returns server timezone time
   
   Using Python generation ensures consistent behavior across all database backends.

3. **Predictability**: Timestamp values are available before saving, facilitating business logic handling.

**Implementation Details**:

- All timestamps use UTC timezone `datetime` objects
- `_update_timestamps` method is called during `BEFORE_SAVE` event
- New records: Sets both `created_at` and `updated_at`
- Update records: Only updates `updated_at`, `created_at` remains unchanged

### SoftDeleteMixin

Marks records as deleted instead of physically removing them.

```python
from rhosocial.activerecord.field import SoftDeleteMixin

class Comment(SoftDeleteMixin, ActiveRecord):
    # Automatically gets: deleted_at: Optional[int]
    pass

# Queries automatically filter out deleted records
active_comments = Comment.all()

# Physical deletion
comment.delete(hard=True)
```

## Custom Mixins

You can easily create your own Mixins. A Mixin is just a class inheriting from `ActiveRecord` (or its base).

### Example: ContentMixin

Suppose multiple models (Post, Comment, Note) have `content` and `summary` fields.

```python
from pydantic import Field
from rhosocial.activerecord.model import ActiveRecord

class ContentMixin(ActiveRecord):
    content: str
    
    # You can define methods and properties in Mixins
    @property
    def word_count(self) -> int:
        return len(self.content.split())
        
    def summary(self, length=100) -> str:
        return self.content[:length] + "..." if len(self.content) > length else self.content

class Post(ContentMixin, ActiveRecord):
    title: str

class Comment(ContentMixin, ActiveRecord):
    user_id: str
```

This keeps your code DRY (Don't Repeat Yourself).

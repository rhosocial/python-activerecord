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
    # created_at: int (default milliseconds timestamp, configurable)
    # updated_at: int
    pass
```

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

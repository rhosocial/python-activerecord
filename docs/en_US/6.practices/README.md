# Model Design Best Practices

This guide covers best practices for designing ActiveRecord models, focusing on maintainability, performance, and code organization.

## Basic Principles

### Single Responsibility

Models should have a single, well-defined responsibility:

```python
# Good: Focused model
class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: int
    username: str
    email: str
    created_at: datetime
    
    def authenticate(self, password: str) -> bool:
        return self._verify_password(password)
    
    def update_last_login(self) -> None:
        self.last_login = datetime.now()
        self.save()

# Bad: Too many responsibilities
class UserWithTooMuch(ActiveRecord):
    __table_name__ = 'users'
    
    id: int
    username: str
    email: str
    
    def authenticate(self, password: str) -> bool:
        # Authentication logic
        pass
    
    def send_email(self, subject: str, body: str) -> None:
        # Email sending logic
        pass
    
    def generate_report(self) -> str:
        # Report generation logic
        pass
```

### Clear Field Definitions

Use explicit type hints and field definitions:

```python
from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import EmailStr, Field

class Order(ActiveRecord):
    __table_name__ = 'orders'
    
    id: int
    user_id: int
    total: Decimal = Field(ge=0)
    status: str = Field(default='pending')
    created_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        validate_all = True
```

## Model Organization

### Use Mixins for Shared Behavior

```python
from rhosocial.activerecord.fields import TimestampMixin, SoftDeleteMixin

class ContentMixin(ActiveRecord):
    title: str = Field(min_length=1, max_length=200)
    content: str
    published: bool = False
    
    def publish(self) -> None:
        self.published = True
        self.save()

class Post(ContentMixin, TimestampMixin, ActiveRecord):
    __table_name__ = 'posts'
    
    id: int
    user_id: int
    
class Page(ContentMixin, TimestampMixin, ActiveRecord):
    __table_name__ = 'pages'
    
    id: int
    slug: str
```

### Relationship Organization

```python
class User(ActiveRecord):
    __table_name__ = 'users'
    
    # Core fields
    id: int
    username: str
    email: EmailStr
    
    # Direct relationships
    profile: 'Profile' = HasOne('Profile', foreign_key='user_id')
    posts: List['Post'] = HasMany('Post', foreign_key='user_id')
    
    # Indirect relationships
    liked_posts: List['Post'] = HasMany(
        'Post',
        through='user_likes',
        foreign_key='user_id',
        target_key='post_id'
    )
```

## Validation and Business Logic

### Model-Level Validation

```python
class Order(ActiveRecord):
    __table_name__ = 'orders'
    
    id: int
    user_id: int
    total: Decimal
    status: str
    
    @validator('total')
    def validate_total(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Total cannot be negative")
        return v
    
    @validator('status')
    def validate_status(cls, v: str) -> str:
        valid_statuses = {'pending', 'processing', 'completed', 'cancelled'}
        if v not in valid_statuses:
            raise ValueError(f"Invalid status: {v}")
        return v
```

### Business Logic Methods

```python
class Order(ActiveRecord):
    def process(self) -> None:
        """Process the order."""
        if self.status != 'pending':
            raise ValueError("Can only process pending orders")
        
        with self.transaction():
            # Update inventory
            for item in self.items:
                product = item.product
                product.stock -= item.quantity
                product.save()
            
            # Update order
            self.status = 'processing'
            self.save()
    
    def complete(self) -> None:
        """Complete the order."""
        if self.status != 'processing':
            raise ValueError("Can only complete processing orders")
        
        self.status = 'completed'
        self.completed_at = datetime.now()
        self.save()
```

## Performance Considerations

### Eager Loading

```python
# Define common eager loading patterns
class Post(ActiveRecord):
    @classmethod
    def with_details(cls):
        return cls.query()\
            .with_('author', 'comments.author')\
            .where('deleted_at IS NULL')
    
    @classmethod
    def with_stats(cls):
        return cls.query()\
            .select(
                'posts.*',
                'COUNT(comments.id) as comment_count',
                'COUNT(DISTINCT likes.user_id) as like_count'
            )\
            .join('LEFT JOIN comments ON comments.post_id = posts.id')\
            .join('LEFT JOIN likes ON likes.post_id = posts.id')\
            .group_by('posts.id')
```

### Batch Operations

```python
class User(ActiveRecord):
    @classmethod
    def deactivate_inactive(cls, days: int) -> int:
        cutoff = datetime.now() - timedelta(days=days)
        return cls.query()\
            .where('last_login < ?', (cutoff,))\
            .where('status = ?', ('active',))\
            .update({'status': 'inactive'})
    
    @classmethod
    def process_in_batches(cls, batch_size: int = 1000):
        offset = 0
        while True:
            batch = cls.query()\
                .limit(batch_size)\
                .offset(offset)\
                .all()
            
            if not batch:
                break
            
            yield batch
            offset += batch_size
```

## Error Handling

### Graceful Error Recovery

```python
class Order(ActiveRecord):
    def process_safely(self) -> bool:
        try:
            with self.transaction():
                self.process()
                return True
        except ValidationError as e:
            self.log_error('Validation failed', e)
            return False
        except DatabaseError as e:
            self.log_error('Database error', e)
            return False
        except Exception as e:
            self.log_error('Unexpected error', e)
            return False
    
    def log_error(self, message: str, error: Exception) -> None:
        logger.error(f"Order #{self.id} - {message}: {str(error)}")
```

## Testing Considerations

### Testable Design

```python
class User(ActiveRecord):
    def __init__(self, **data):
        super().__init__(**data)
        self.password_hasher = data.get('password_hasher', DefaultHasher())
    
    def set_password(self, password: str) -> None:
        self.password_hash = self.password_hasher.hash(password)
        self.save()

# Easy to test with mock hasher
class TestUser(TestCase):
    def test_set_password(self):
        mock_hasher = Mock()
        mock_hasher.hash.return_value = 'hashed'
        
        user = User(password_hasher=mock_hasher)
        user.set_password('secret')
        
        mock_hasher.hash.assert_called_with('secret')
        self.assertEqual(user.password_hash, 'hashed')
```

## Best Practices

1. **Model Design**
   - Follow single responsibility principle
   - Use explicit type hints
   - Implement proper validation
   - Keep models focused

2. **Code Organization**
   - Use mixins for shared behavior
   - Organize relationships clearly
   - Separate business logic
   - Maintain consistent structure

3. **Performance**
   - Implement eager loading
   - Use batch operations
   - Optimize queries
   - Cache when appropriate

4. **Error Handling**
   - Implement proper validation
   - Handle errors gracefully
   - Log errors appropriately
   - Maintain data consistency

5. **Testing**
   - Design for testability
   - Mock external dependencies
   - Test edge cases
   - Maintain test coverage

## Next Steps

1. Review [Query Writing](query_writing.md) practices
2. Study [Transaction Usage](transaction_usage.md)
3. Learn about [Error Handling](error_handling.md)
4. Explore [Testing Strategy](testing_strategy.md)
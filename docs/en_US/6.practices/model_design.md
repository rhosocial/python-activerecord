# Model Design Best Practices

This guide covers best practices for designing ActiveRecord models in RhoSocial ActiveRecord applications, focusing on maintainability, performance, and code organization.

## Core Principles

### Single Responsibility

Each model should have a clear, single responsibility:

```python
# Good: User model focused on user data
class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: int
    username: str
    email: str
    created_at: datetime
    
    def authenticate(self, password: str) -> bool:
        """Authenticate user with password."""
        return self._verify_password(password)
    
    def update_profile(self, data: dict) -> None:
        """Update user profile data."""
        self.username = data.get('username', self.username)
        self.email = data.get('email', self.email)
        self.save()

# Bad: User model with mixed responsibilities
class UserWithTooMuch(ActiveRecord):
    __table_name__ = 'users'
    
    id: int
    username: str
    email: str
    
    def authenticate(self, password: str) -> bool:
        pass
    
    def send_email(self, subject: str, body: str) -> None:
        # Email sending doesn't belong in the model
        pass
    
    def generate_report(self) -> str:
        # Report generation doesn't belong in the model
        pass
```

### Domain Logic

Focus on business logic and domain rules:

```python
# E-commerce example
class Order(ActiveRecord):
    __table_name__ = 'orders'
    
    id: int
    user_id: int
    total: Decimal
    status: str
    created_at: datetime
    
    def calculate_total(self) -> Decimal:
        """Calculate order total from items."""
        return sum(item.quantity * item.price for item in self.items)
    
    def can_cancel(self) -> bool:
        """Check if order can be cancelled."""
        return self.status in ('pending', 'processing')
    
    def process(self) -> None:
        """Process the order."""
        if not self.items:
            raise ValueError("Cannot process empty order")
        
        with self.transaction():
            # Update inventory
            for item in self.items:
                product = item.product
                if product.stock < item.quantity:
                    raise ValueError(f"Insufficient stock for {product.name}")
                product.stock -= item.quantity
                product.save()
            
            # Update order
            self.status = 'processing'
            self.save()
```

## Model Relationships

### Clear Relationship Definitions

```python
# Social media example
class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: int
    username: str
    
    # Direct relationships
    posts: List['Post'] = HasMany('Post', foreign_key='user_id')
    profile: 'Profile' = HasOne('Profile', foreign_key='user_id')
    
    # Indirect relationships
    liked_posts: List['Post'] = HasMany(
        'Post',
        through='user_likes',
        foreign_key='user_id',
        target_key='post_id'
    )

class Post(ActiveRecord):
    __table_name__ = 'posts'
    
    id: int
    user_id: int
    content: str
    
    # Relationships
    author: User = BelongsTo('User', foreign_key='user_id')
    comments: List['Comment'] = HasMany('Comment', foreign_key='post_id')
```

### Relationship Validation

```python
# E-commerce relationships
class Order(ActiveRecord):
    __table_name__ = 'orders'
    
    # Relationships
    user: 'User' = BelongsTo('User', foreign_key='user_id')
    items: List['OrderItem'] = HasMany('OrderItem', foreign_key='order_id')
    
    def validate_items(self) -> None:
        """Validate order items."""
        if not self.items:
            raise ValidationError("Order must have items")
        
        total_amount = self.calculate_total()
        if total_amount <= 0:
            raise ValidationError("Order total must be positive")

class OrderItem(ActiveRecord):
    __table_name__ = 'order_items'
    
    order_id: int
    product_id: int
    quantity: int
    price: Decimal
    
    # Relationships
    order: Order = BelongsTo('Order', foreign_key='order_id')
    product: 'Product' = BelongsTo('Product', foreign_key='product_id')
    
    def validate_quantity(self) -> None:
        """Validate item quantity."""
        if self.quantity <= 0:
            raise ValidationError("Quantity must be positive")
        
        if self.product and self.quantity > self.product.stock:
            raise ValidationError("Insufficient stock")
```

## Field Types and Validation

### Strong Type Definitions

```python
from datetime import datetime
from decimal import Decimal
from pydantic import EmailStr, Field
from typing import Optional

class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: int
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    created_at: datetime = Field(default_factory=datetime.now)
    last_login: Optional[datetime] = None

class Product(ActiveRecord):
    __table_name__ = 'products'
    
    id: int
    name: str = Field(min_length=1, max_length=200)
    price: Decimal = Field(ge=0)
    stock: int = Field(ge=0)
    description: Optional[str] = Field(max_length=1000)
```

### Custom Validation Rules

```python
class User(ActiveRecord):
    username: str
    email: str
    age: int
    
    @validator('username')
    def validate_username(cls, v: str) -> str:
        if not v.isalnum():
            raise ValueError("Username must be alphanumeric")
        return v.lower()
    
    @validator('email')
    def validate_email(cls, v: str) -> str:
        if not '@' in v:
            raise ValueError("Invalid email format")
        return v.lower()
    
    @validator('age')
    def validate_age(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Age cannot be negative")
        if v > 150:
            raise ValueError("Age seems invalid")
        return v
```

## Model Organization

### Use Mixins for Shared Behavior

```python
class TimestampMixin(ActiveRecord):
    """Add timestamp fields to model."""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    def save(self) -> None:
        self.updated_at = datetime.now()
        super().save()

class SoftDeleteMixin(ActiveRecord):
    """Add soft delete capability."""
    deleted_at: Optional[datetime] = None
    
    def delete(self) -> None:
        self.deleted_at = datetime.now()
        self.save()
    
    def restore(self) -> None:
        self.deleted_at = None
        self.save()

# Usage
class Post(TimestampMixin, SoftDeleteMixin, ActiveRecord):
    __table_name__ = 'posts'
    
    id: int
    user_id: int
    content: str
```

### Event Handlers

```python
from rhosocial.activerecord.interface import ModelEvent

class Order(ActiveRecord):
    def __init__(self, **data):
        super().__init__(**data)
        self.on(ModelEvent.BEFORE_SAVE, self._before_save)
        self.on(ModelEvent.AFTER_SAVE, self._after_save)
    
    def _before_save(self, instance: 'Order', is_new: bool):
        """Handle before save event."""
        if is_new:
            self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def _after_save(self, instance: 'Order', is_new: bool):
        """Handle after save event."""
        if is_new:
            # Send notification
            notify_new_order(self)
```

## Best Practices

1. **Model Design**
   - Follow single responsibility principle
   - Use clear field definitions
   - Implement proper validation
   - Design clear relationships

2. **Code Organization**
   - Use mixins for shared behavior
   - Implement event handlers
   - Separate business logic
   - Maintain clean interfaces

3. **Validation**
   - Use strong type definitions
   - Implement custom validators
   - Validate relationships
   - Handle edge cases

4. **Relationships**
   - Define clear relationships
   - Use appropriate relationship types
   - Validate related data
   - Consider performance

5. **Performance**
   - Use appropriate field types
   - Implement efficient queries
   - Consider batch operations
   - Monitor performance

## Next Steps

1. Study [Query Writing](query_writing.md)
2. Review [Transaction Usage](transaction_usage.md)
3. Learn about [Error Handling](error_handling.md)
4. Explore [Testing Strategy](testing_strategy.md)
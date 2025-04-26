# Composition Patterns and Mixins

This document explains how to use composition patterns and mixins in your ActiveRecord models. These techniques allow you to reuse functionality across models without relying on inheritance hierarchies.

## Overview

Composition is a design pattern where complex objects are built from smaller, reusable components. In rhosocial ActiveRecord, composition is often implemented using mixins - classes that provide specific functionality that can be "mixed in" to other classes.

Mixins offer several advantages over traditional inheritance:

- They allow for more flexible code reuse
- They avoid the limitations of single inheritance
- They make it easier to compose functionality from multiple sources
- They keep your model hierarchy flat and maintainable

## Using Predefined Mixins

rhosocial ActiveRecord comes with several predefined mixins that provide common functionality:

### TimestampMixin

Adds automatic timestamp management for created_at and updated_at fields:

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import TimestampMixin

class Article(TimestampMixin, ActiveRecord):
    id: int
    title: str
    content: str
    # created_at and updated_at are automatically added and managed
```

### SoftDeleteMixin

Implements soft delete functionality, allowing records to be marked as deleted without actually removing them from the database:

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import SoftDeleteMixin

class Document(SoftDeleteMixin, ActiveRecord):
    id: int
    title: str
    content: str
    # deleted_at is automatically added and managed
    
# Usage:
doc = Document.find(1)
doc.delete()  # Marks as deleted but keeps in database

# Query methods:
Document.query()  # Returns only non-deleted records
Document.query_with_deleted()  # Returns all records
Document.query_only_deleted()  # Returns only deleted records
```

### OptimisticLockMixin

Implements optimistic locking using version numbers to prevent concurrent updates:

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import OptimisticLockMixin

class Account(OptimisticLockMixin, ActiveRecord):
    id: int
    balance: float
    # version field is automatically added and managed
```

### UUIDMixin

Adds UUID primary key support with automatic UUID generation for new records:

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import UUIDMixin

class Order(UUIDMixin, ActiveRecord):
    # id will be automatically set as UUID
    customer_name: str
    total_amount: float
```

### IntegerPKMixin

Provides integer primary key support with automatic handling of null values for new records:

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin

class Product(IntegerPKMixin, ActiveRecord):
    # id will be automatically managed
    name: str
    price: float
```

## Creating Custom Mixins

You can create your own mixins to encapsulate reusable functionality:

### Basic Mixin Structure

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.interface import ModelEvent
from typing import ClassVar, Optional

class AuditableMixin(ActiveRecord):
    """Mixin that adds auditing capabilities to models."""
    
    created_by: Optional[int] = None
    updated_by: Optional[int] = None
    
    # Class variable to store the current user ID
    __current_user_id__: ClassVar[Optional[int]] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        
        # Register event handlers
        self.on(ModelEvent.BEFORE_CREATE, self._set_created_by)
        self.on(ModelEvent.BEFORE_UPDATE, self._set_updated_by)
    
    def _set_created_by(self, event):
        """Set created_by field to current user ID."""
        if self.__class__.__current_user_id__ is not None:
            self.created_by = self.__class__.__current_user_id__
    
    def _set_updated_by(self, event):
        """Set updated_by field to current user ID."""
        if self.__class__.__current_user_id__ is not None:
            self.updated_by = self.__class__.__current_user_id__
    
    @classmethod
    def set_current_user(cls, user_id: Optional[int]):
        """Set the current user ID for auditing."""
        cls.__current_user_id__ = user_id
```

### Using the Custom Mixin

```python
class Invoice(AuditableMixin, TimestampMixin, ActiveRecord):
    id: int
    amount: float
    description: str
    # Inherits created_at, updated_at, created_by, updated_by

# Set the current user for auditing
Invoice.set_current_user(user_id=123)

# Create a new invoice (will have created_by=123)
invoice = Invoice(amount=100.0, description="Monthly service")
invoice.save()
```

## Composition Patterns

### Trait-like Mixins

Traits are small, focused mixins that provide a single piece of functionality:

```python
class TaggableMixin(ActiveRecord):
    """Mixin that adds tagging capabilities to models."""
    
    _tags: str = ""  # Comma-separated tags stored in database
    
    def add_tag(self, tag: str):
        """Add a tag to this record."""
        tags = self.tags
        if tag not in tags:
            tags.append(tag)
            self._tags = ",".join(tags)
    
    def remove_tag(self, tag: str):
        """Remove a tag from this record."""
        tags = self.tags
        if tag in tags:
            tags.remove(tag)
            self._tags = ",".join(tags)
    
    @property
    def tags(self) -> list:
        """Get the list of tags."""
        return self._tags.split(",") if self._tags else []
```

### Behavior Mixins

Behavior mixins add specific behaviors to models:

```python
from datetime import datetime, timedelta

class ExpirableMixin(ActiveRecord):
    """Mixin that adds expiration behavior to models."""
    
    expires_at: Optional[datetime] = None
    
    def set_expiration(self, days: int):
        """Set the expiration date to a number of days from now."""
        self.expires_at = datetime.now() + timedelta(days=days)
    
    def is_expired(self) -> bool:
        """Check if the record has expired."""
        return self.expires_at is not None and datetime.now() > self.expires_at
    
    @classmethod
    def query_active(cls):
        """Query only non-expired records."""
        return cls.query().where(
            (cls.expires_at == None) | (cls.expires_at > datetime.now())
        )
```

### Validator Mixins

Validator mixins add custom validation logic:

```python
from pydantic import validator

class EmailValidationMixin(ActiveRecord):
    """Mixin that adds email validation."""
    
    email: str
    
    @validator('email')
    def validate_email(cls, v):
        """Validate email format."""
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', v):
            raise ValueError('Invalid email format')
        return v.lower()  # Normalize to lowercase
```

### Query Scope Mixins

Query scope mixins add reusable query methods:

```python
from datetime import datetime

class TimeScopeMixin(ActiveRecord):
    """Mixin that adds time-based query scopes."""
    
    created_at: datetime
    
    @classmethod
    def created_today(cls):
        """Query records created today."""
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        return cls.query().where(
            (cls.created_at >= today.isoformat()) & 
            (cls.created_at < tomorrow.isoformat())
        )
    
    @classmethod
    def created_this_week(cls):
        """Query records created this week."""
        today = datetime.now().date()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=7)
        return cls.query().where(
            (cls.created_at >= start_of_week.isoformat()) & 
            (cls.created_at < end_of_week.isoformat())
        )
```

## Combining Multiple Mixins

You can combine multiple mixins to build complex functionality:

```python
class Article(
    TaggableMixin,        # Adds tagging capabilities
    ExpirableMixin,        # Adds expiration behavior
    TimeScopeMixin,        # Adds time-based query scopes
    SoftDeleteMixin,       # Adds soft delete functionality
    TimestampMixin,        # Adds timestamp management
    IntegerPKMixin,        # Adds integer primary key support
    ActiveRecord
):
    title: str
    content: str
    author_id: int
    
    # Now this model has all the functionality from the mixins
```

## Mixin Order Considerations

The order of mixins matters in Python due to method resolution order (MRO). When a method is called, Python searches for it in the class and its parent classes in a specific order.

```python
# This order:
class User(AuditableMixin, TimestampMixin, ActiveRecord):
    pass

# Is different from this order:
class User(TimestampMixin, AuditableMixin, ActiveRecord):
    pass
```

If both mixins define the same method or hook into the same event, the one listed first will take precedence.

### Best Practices for Mixin Order

1. Put more specific mixins before more general ones
2. Put mixins that override methods from other mixins earlier in the list
3. Always put ActiveRecord last in the inheritance list

## Delegation Pattern

Another composition pattern is delegation, where a model delegates certain operations to associated objects:

```python
class ShoppingCart(ActiveRecord):
    id: int
    user_id: int
    
    def items(self):
        """Get cart items."""
        from .cart_item import CartItem
        return CartItem.query().where(cart_id=self.id).all()
    
    @property
    def total(self) -> float:
        """Calculate total by delegating to cart items."""
        return sum(item.subtotal for item in self.items())
    
    def add_product(self, product_id: int, quantity: int = 1):
        """Add a product to the cart."""
        from .cart_item import CartItem
        from .product import Product
        
        # Check if product already in cart
        existing_item = CartItem.query().where(
            cart_id=self.id, product_id=product_id
        ).first()
        
        if existing_item:
            # Update quantity
            existing_item.quantity += quantity
            existing_item.save()
            return existing_item
        else:
            # Create new cart item
            product = Product.find(product_id)
            item = CartItem(
                cart_id=self.id,
                product_id=product_id,
                price=product.price,
                quantity=quantity
            )
            item.save()
            return item
```

## Best Practices

1. **Keep Mixins Focused**: Each mixin should have a single responsibility.

2. **Document Mixin Requirements**: Clearly document any fields or methods that a mixin expects to be present in the classes that use it.

3. **Avoid Mixin Conflicts**: Be careful when combining mixins that might override the same methods or hook into the same events.

4. **Use Composition Over Inheritance**: When possible, prefer composition (has-a relationship) over inheritance (is-a relationship).

5. **Test Mixins Independently**: Write unit tests for your mixins to ensure they work correctly in isolation.

6. **Consider Namespace Pollution**: Be careful about adding too many methods or properties to your models through mixins.

7. **Use Descriptive Names**: Name your mixins to clearly indicate their purpose (e.g., `TaggableMixin`, `AuditableMixin`).

## Conclusion

Composition patterns and mixins provide powerful ways to reuse functionality across your ActiveRecord models. By breaking down common behaviors into small, focused mixins, you can create more maintainable and flexible code. This approach allows you to compose complex models from simple building blocks, following the principle of composition over inheritance.
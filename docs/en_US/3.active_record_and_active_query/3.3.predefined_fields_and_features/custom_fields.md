# Custom Fields

rhosocial ActiveRecord allows you to extend your models with custom fields and field behaviors. This document explains how to create and use custom fields in your ActiveRecord models.

## Overview

Custom fields enable you to:

- Define specialized field types with custom validation and behavior
- Create reusable field patterns across multiple models
- Implement domain-specific field types for your application
- Extend the base functionality of ActiveRecord models

## Basic Custom Fields

The simplest way to create custom fields is to use Pydantic's `Field` function with custom validators:

```python
from pydantic import Field, validator
from rhosocial.activerecord import ActiveRecord
from typing import Optional

class Product(ActiveRecord):
    __tablename__ = 'products'
    
    name: str
    price: float = Field(..., gt=0)  # Custom constraint: price must be positive
    sku: str = Field(..., regex=r'^[A-Z]{3}\d{6}$')  # Custom format validation
    
    @validator('sku')
    def validate_sku(cls, v):
        # Additional custom validation logic
        if not v.startswith('SKU'):
            raise ValueError('SKU must start with "SKU"')
        return v
```

In this example, we've created custom fields with:
- A price field that must be greater than zero
- An SKU field with a specific format enforced by regex
- Additional validation logic for the SKU field

## Creating Custom Field Types

For more complex or reusable field types, you can create custom field classes:

```python
from pydantic import Field
from pydantic.fields import FieldInfo
from typing import Any, Callable, Optional, Type

def EmailField(default: Any = ..., *, title: Optional[str] = None, description: Optional[str] = None, **kwargs) -> Any:
    """Custom email field with built-in validation."""
    return Field(
        default,
        title=title or "Email Address",
        description=description or "A valid email address",
        regex=r'^[\w\.-]+@[\w\.-]+\.\w+$',
        **kwargs
    )

# Using the custom field
class User(ActiveRecord):
    __tablename__ = 'users'
    
    name: str
    email: str = EmailField()  # Using our custom field type
```

## Field Mixins

For more complex field behavior, you can create mixins that add fields and related methods to your models:

```python
from datetime import datetime
from pydantic import Field
from rhosocial.activerecord import ActiveRecord

class AuditableMixin:
    """Adds auditing fields to track who created and updated records."""
    
    created_by: Optional[int] = Field(None)
    updated_by: Optional[int] = Field(None)
    
    def set_created_by(self, user_id: int):
        """Set the created_by field to the current user ID."""
        self.created_by = user_id
    
    def set_updated_by(self, user_id: int):
        """Set the updated_by field to the current user ID."""
        self.updated_by = user_id

class Article(AuditableMixin, ActiveRecord):
    __tablename__ = 'articles'
    
    title: str
    content: str
    
    def before_save(self):
        """Hook into the save lifecycle to set audit fields."""
        super().before_save()
        
        # Assuming you have a way to get the current user ID
        current_user_id = get_current_user_id()  # This would be your implementation
        
        if self.is_new_record():
            self.set_created_by(current_user_id)
        
        self.set_updated_by(current_user_id)
```

## Computed Fields

You can also create computed fields that derive their values from other fields:

```python
from pydantic import computed_field
from rhosocial.activerecord import ActiveRecord

class Rectangle(ActiveRecord):
    __tablename__ = 'rectangles'
    
    width: float
    height: float
    
    @computed_field
    def area(self) -> float:
        """Calculate the area of the rectangle."""
        return self.width * self.height
    
    @computed_field
    def perimeter(self) -> float:
        """Calculate the perimeter of the rectangle."""
        return 2 * (self.width + self.height)
```

## JSON Fields

Many databases support JSON data types. You can use them in your models:

```python
from typing import Dict, Any, List
from pydantic import Field
from rhosocial.activerecord import ActiveRecord

class UserProfile(ActiveRecord):
    __tablename__ = 'user_profiles'
    
    user_id: int
    preferences: Dict[str, Any] = Field(default_factory=dict)  # JSON field
    tags: List[str] = Field(default_factory=list)  # JSON array field
    
    def add_tag(self, tag: str):
        """Add a tag to the user's profile."""
        if tag not in self.tags:
            self.tags.append(tag)
    
    def set_preference(self, key: str, value: Any):
        """Set a user preference."""
        self.preferences[key] = value
```

## Excluding Fields from Change Tracking

ActiveRecord tracks changes to fields to optimize updates. Sometimes you may want to exclude certain fields from this tracking:

```python
from rhosocial.activerecord import ActiveRecord

class CachedContent(ActiveRecord):
    __tablename__ = 'cached_contents'
    
    key: str
    content: str
    access_count: int = 0  # Counter that doesn't need change tracking
    
    # Exclude access_count from change tracking
    __no_track_fields__ = {'access_count'}
    
    def increment_access(self):
        """Increment the access counter without marking the record as dirty."""
        self.access_count += 1
        # This won't mark the record as needing to be saved
```

## Database-Specific Field Types

You can specify database-specific column types for your fields:

```python
from pydantic import Field
from rhosocial.activerecord import ActiveRecord

class Document(ActiveRecord):
    __tablename__ = 'documents'
    
    title: str
    # Use TEXT type instead of VARCHAR for content
    content: str = Field(..., sa_column_type="TEXT")
    # Use JSONB for PostgreSQL
    metadata: dict = Field(default_factory=dict, sa_column_type="JSONB")
```

## Best Practices

1. **Reuse Field Definitions**: Create custom field types for commonly used patterns to ensure consistency.

2. **Document Field Behavior**: Clearly document any special behavior or constraints of custom fields.

3. **Validation Logic**: Keep validation logic close to the field definition for clarity.

4. **Separate Concerns**: Use mixins to group related fields and behaviors together.

5. **Consider Performance**: Be mindful of the performance impact of complex computed fields or validators.

6. **Test Edge Cases**: Thoroughly test custom fields with edge cases to ensure robust behavior.

## Next Steps

Now that you understand custom fields, you might want to explore:

- [Defining Models](../3.1.defining_models/README.md) - For more details on model definition
- [Field Validation Rules](../3.1.defining_models/field_validation_rules.md) - For advanced validation techniques
- [Composition Patterns and Mixins](../3.1.defining_models/composition_patterns_and_mixins.md) - For more on using mixins
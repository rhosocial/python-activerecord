# Inheritance and Polymorphism

This document explains how to use inheritance and polymorphism in your ActiveRecord models. These object-oriented concepts allow you to create model hierarchies, share behavior, and implement specialized versions of base models.

## Overview

rhosocial ActiveRecord supports model inheritance, allowing you to create hierarchies of related models. This enables you to:

- Share common fields and behavior across related models
- Implement specialized versions of base models
- Create polymorphic relationships between models
- Organize your models in a logical, object-oriented structure

## Single Table Inheritance

Single Table Inheritance (STI) is a pattern where multiple model classes share a single database table. The table includes all fields needed by any of the subclasses, and a type column indicates which specific model a row represents.

### Basic Implementation

```python
from rhosocial.activerecord import ActiveRecord
from typing import Optional

class Vehicle(ActiveRecord):
    __table_name__ = 'vehicles'
    __type_field__ = 'vehicle_type'  # Column that stores the model type
    
    id: int
    make: str
    model: str
    year: int
    color: str
    vehicle_type: str  # Stores the class name or type identifier
    
    def __init__(self, **data):
        if self.__class__ == Vehicle:
            data['vehicle_type'] = 'Vehicle'
        super().__init__(**data)

class Car(Vehicle):
    doors: int
    trunk_capacity: Optional[float] = None
    
    def __init__(self, **data):
        data['vehicle_type'] = 'Car'
        super().__init__(**data)

class Motorcycle(Vehicle):
    engine_displacement: Optional[int] = None
    has_sidecar: bool = False
    
    def __init__(self, **data):
        data['vehicle_type'] = 'Motorcycle'
        super().__init__(**data)
```

### Querying with STI

When querying with Single Table Inheritance, you can:

1. Query the base class to get all types:

```python
# Get all vehicles regardless of type
vehicles = Vehicle.query().all()
```

2. Query a specific subclass to get only that type:

```python
# Get only cars
cars = Car.query().all()

# Get only motorcycles
motorcycles = Motorcycle.query().all()
```

The ActiveRecord framework automatically adds the appropriate type condition when querying from a subclass.

## Class Table Inheritance

Class Table Inheritance (CTI) uses separate tables for each class in the inheritance hierarchy, with foreign key relationships between them. This approach is more normalized but requires joins for complete object retrieval.

### Basic Implementation

```python
from rhosocial.activerecord import ActiveRecord
from typing import Optional

class Person(ActiveRecord):
    __table_name__ = 'people'
    
    id: int
    name: str
    email: str
    birth_date: Optional[date] = None

class Employee(Person):
    __table_name__ = 'employees'
    __primary_key__ = 'person_id'  # Foreign key to people table
    
    person_id: int  # References Person.id
    hire_date: date
    department: str
    salary: float
    
    def __init__(self, **data):
        # Handle person data separately
        person_data = {}
        for field in Person.model_fields():
            if field in data:
                person_data[field] = data.pop(field)
        
        # Create or update the person record
        if 'id' in person_data:
            person = Person.find_one(person_data['id'])
            for key, value in person_data.items():
                setattr(person, key, value)
            person.save()
        else:
            person = Person(**person_data)
            person.save()
        
        # Set the person_id for the employee
        data['person_id'] = person.id
        
        super().__init__(**data)
```

### Querying with CTI

Querying with Class Table Inheritance requires explicit joins:

```python
# Get employees with their person data
employees = Employee.query()\
    .inner_join('people', 'person_id', 'people.id')\
    .select('employees.*', 'people.name', 'people.email')\
    .all()
```

## Polymorphic Associations

Polymorphic associations allow a model to belong to multiple types of models through a single association. This is implemented using a combination of a foreign key and a type identifier.

### Basic Implementation

```python
from rhosocial.activerecord import ActiveRecord

class Comment(ActiveRecord):
    __table_name__ = 'comments'
    
    id: int
    content: str
    commentable_id: int      # Foreign key to the associated object
    commentable_type: str    # Type of the associated object (e.g., 'Post', 'Photo')
    created_at: datetime
    
    def commentable(self):
        """Get the associated object (post, photo, etc.)"""
        if self.commentable_type == 'Post':
            from .post import Post
            return Post.find_one(self.commentable_id)
        elif self.commentable_type == 'Photo':
            from .photo import Photo
            return Photo.find_one(self.commentable_id)
        return None

class Post(ActiveRecord):
    __table_name__ = 'posts'
    
    id: int
    title: str
    content: str
    
    def comments(self):
        """Get comments associated with this post"""
        return Comment.query()\
            .where(commentable_id=self.id, commentable_type='Post')\
            .all()
    
    def add_comment(self, content: str):
        """Add a comment to this post"""
        comment = Comment(
            content=content,
            commentable_id=self.id,
            commentable_type='Post',
            created_at=datetime.now()
        )
        comment.save()
        return comment

class Photo(ActiveRecord):
    __table_name__ = 'photos'
    
    id: int
    title: str
    url: str
    
    def comments(self):
        """Get comments associated with this photo"""
        return Comment.query()\
            .where(commentable_id=self.id, commentable_type='Photo')\
            .all()
    
    def add_comment(self, content: str):
        """Add a comment to this photo"""
        comment = Comment(
            content=content,
            commentable_id=self.id,
            commentable_type='Photo',
            created_at=datetime.now()
        )
        comment.save()
        return comment
```

### Using Polymorphic Associations

```python
# Create a post and add a comment
post = Post(title="My First Post", content="Hello, world!")
post.save()
post.add_comment("Great post!")

# Create a photo and add a comment
photo = Photo(title="Sunset", url="/images/sunset.jpg")
photo.save()
photo.add_comment("Beautiful colors!")

# Get all comments for a post
post_comments = post.comments()

# Get the commentable object from a comment
comment = Comment.find_one(1)
commentable = comment.commentable()  # Returns either a Post or Photo instance
```

## Abstract Base Classes

Abstract base classes provide common functionality without being directly instantiable. They're useful for sharing code across models without creating database tables for the base classes.

### Basic Implementation

```python
from abc import ABC
from rhosocial.activerecord import ActiveRecord

class Auditable(ActiveRecord, ABC):
    """Abstract base class for auditable models."""
    __abstract__ = True  # Marks this as an abstract class (no table)
    
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None
    updated_by: Optional[int] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        self.on(ModelEvent.BEFORE_CREATE, self._set_audit_timestamps)
        self.on(ModelEvent.BEFORE_UPDATE, self._update_audit_timestamps)
    
    def _set_audit_timestamps(self, event):
        now = datetime.now()
        self.created_at = now
        self.updated_at = now
        # Could set created_by/updated_by from current user if available
    
    def _update_audit_timestamps(self, event):
        self.updated_at = datetime.now()
        # Could set updated_by from current user if available

class User(Auditable):
    __table_name__ = 'users'
    
    id: int
    username: str
    email: str
    # Inherits created_at, updated_at, created_by, updated_by

class Product(Auditable):
    __table_name__ = 'products'
    
    id: int
    name: str
    price: float
    # Inherits created_at, updated_at, created_by, updated_by
```

## Method Overriding

You can override methods from parent classes to customize behavior in subclasses:

```python
class Animal(ActiveRecord):
    id: int
    name: str
    species: str
    
    def make_sound(self):
        return "Some generic animal sound"

class Dog(Animal):
    breed: str
    
    def __init__(self, **data):
        data['species'] = 'Canine'
        super().__init__(**data)
    
    def make_sound(self):
        # Override the parent method
        return "Woof!"

class Cat(Animal):
    fur_color: str
    
    def __init__(self, **data):
        data['species'] = 'Feline'
        super().__init__(**data)
    
    def make_sound(self):
        # Override the parent method
        return "Meow!"
```

## Best Practices

1. **Choose the Right Inheritance Type**: Select Single Table Inheritance for closely related models with few differences, and Class Table Inheritance for models with significant differences.

2. **Use Abstract Base Classes**: For shared behavior without database tables, use abstract base classes.

3. **Be Careful with Deep Hierarchies**: Deep inheritance hierarchies can become complex and difficult to maintain. Keep them shallow when possible.

4. **Document Type Fields**: Clearly document the meaning of type fields in Single Table Inheritance and polymorphic associations.

5. **Consider Composition**: Sometimes composition (using mixins or has-a relationships) is more appropriate than inheritance.

6. **Test Inheritance Thoroughly**: Write tests that verify the behavior of both base classes and subclasses.

## Conclusion

Inheritance and polymorphism are powerful object-oriented concepts that can help you organize and structure your ActiveRecord models. By using these techniques appropriately, you can create more maintainable, DRY (Don't Repeat Yourself) code while accurately modeling the relationships in your domain.
# Migrating from Other ORMs to ActiveRecord

## Introduction

Migrating from one ORM framework to another can be a significant undertaking. This guide provides strategies and best practices for transitioning from popular Python ORMs like SQLAlchemy, Django ORM, and Peewee to rhosocial ActiveRecord. We'll cover approaches for code conversion, data migration, and testing to ensure a smooth transition.

## General Migration Strategy

### 1. Assessment and Planning

Before beginning the migration, conduct a thorough assessment:

- **Inventory existing models**: Document all models, relationships, and custom behaviors
- **Identify ORM-specific features**: Note any features unique to your current ORM that may need special handling
- **Analyze query patterns**: Review how your application interacts with the database
- **Establish test coverage**: Ensure you have tests that verify current database functionality

### 2. Incremental vs. Complete Migration

Choose the migration approach that best fits your project:

- **Incremental Migration**: Convert models and functionality one at a time
  - Lower risk, allows for gradual transition
  - Requires temporary compatibility layer between ORMs
  - Better for large, complex applications

- **Complete Migration**: Convert all models and functionality at once
  - Simpler conceptually, no need to maintain two systems
  - Higher risk, requires more thorough testing
  - Better for smaller applications

## Migrating from SQLAlchemy

### Conceptual Differences

| SQLAlchemy | rhosocial ActiveRecord |
|------------|---------------------|
| Explicit session management | Implicit connection management |
| Declarative model definition | Active Record pattern |
| Query construction via Session API | Query methods on model classes |
| Relationship definition in model class | Relationship methods in model class |

### Model Conversion Examples

**SQLAlchemy Model:**

```python
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    posts = relationship('Post', back_populates='author')
    
    def __repr__(self):
        return f'<User {self.username}>'

class Post(Base):
    __tablename__ = 'posts'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False)
    content = Column(String(10000), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    author = relationship('User', back_populates='posts')
    
    def __repr__(self):
        return f'<Post {self.title}>'
```

**Equivalent rhosocial ActiveRecord Model:**

```python
from rhosocial.activerecord import ActiveRecord
from typing import Optional
from datetime import datetime

class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: int  # Primary key, auto-incrementing
    username: str  # Username, unique, not null
    email: str  # Email, unique, not null
    created_at: datetime  # Creation timestamp, auto-set to current time
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def posts(self):
        return self.has_many(Post, foreign_key='user_id')

class Post(ActiveRecord):
    __table_name__ = 'posts'
    
    id: int  # Primary key, auto-incrementing
    title: str  # Title, not null
    content: str  # Content, not null
    user_id: int  # Foreign key to users.id
    created_at: datetime  # Creation timestamp, auto-set to current time
    
    def __repr__(self):
        return f'<Post {self.title}>'
    
    def author(self):
        return self.belongs_to(User, foreign_key='user_id')
```

### Query Conversion Examples

**SQLAlchemy Queries:**

```python
# Create a new user
user = User(username='johndoe', email='john@example.com')
session.add(user)
session.commit()

# Find a user by primary key
user = session.query(User).get(1)

# Find a user by criteria
user = session.query(User).filter(User.username == 'johndoe').first()

# Find all posts by a user
posts = session.query(Post).filter(Post.user_id == user.id).all()

# Eager loading relationships
user_with_posts = session.query(User).options(joinedload(User.posts)).filter(User.id == 1).first()

# Update a user
user.email = 'newemail@example.com'
session.commit()

# Delete a user
session.delete(user)
session.commit()
```

**Equivalent rhosocial ActiveRecord Queries:**

```python
# Create a new user
user = User(username='johndoe', email='john@example.com')
user.save()

# Find a user by primary key
user = User.find_one(1)

# Find a user by criteria
user = User.find().where(User.username == 'johndoe').one()

# Find all posts by a user
posts = Post.find().where(Post.user_id == user.id).all()

# Eager loading relationships
user_with_posts = User.find().with_('posts').where(User.id == 1).one()

# Update a user
user.email = 'newemail@example.com'
user.save()

# Delete a user
user.delete()
```

## Migrating from Django ORM

### Conceptual Differences

| Django ORM | rhosocial ActiveRecord |
|------------|---------------------|
| Tightly integrated with Django | Standalone ORM |
| Models defined in app-specific models.py | Models can be defined anywhere |
| Migration system tied to Django | Standalone migration system |
| QuerySet API | ActiveQuery API |

### Model Conversion Examples

**Django Model:**

```python
from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = 'Categories'
    
    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
```

**Equivalent rhosocial ActiveRecord Model:**

```python
from rhosocial.activerecord import ActiveRecord
from typing import Optional
from datetime import datetime
from decimal import Decimal

class Category(ActiveRecord):
    name: str  # Name
    description: Optional[str] = ''  # Description, can be null, default empty string
    
    def __str__(self):
        return self.name
    
    def products(self):
        return self.has_many(Product, foreign_key='category_id')

class Product(ActiveRecord):
    name: str  # Name
    description: str  # Description
    price: Decimal  # Price with precision of 10 and scale of 2
    category_id: int  # Foreign key to category.id
    created_at: datetime  # Creation timestamp, auto-set to current time
    updated_at: datetime  # Update timestamp, auto-updated to current time
    is_active: bool = True  # Whether active, default True
    
    def __str__(self):
        return self.name
    
    def category(self):
        return self.belongs_to(Category, foreign_key='category_id')
```

### Query Conversion Examples

**Django Queries:**

```python
# Create a new category
category = Category.objects.create(name='Electronics', description='Electronic devices')

# Create a product
product = Product.objects.create(
    name='Smartphone',
    description='Latest model',
    price=599.99,
    category=category
)

# Get all products
all_products = Product.objects.all()

# Filter products
active_products = Product.objects.filter(is_active=True)

# Complex filtering
expensive_electronics = Product.objects.filter(
    category__name='Electronics',
    price__gt=500,
    is_active=True
)

# Ordering
products_by_price = Product.objects.order_by('price')

# Limiting results
top_5_products = Product.objects.order_by('-created_at')[:5]

# Updating a product
product.price = 499.99
product.save()

# Deleting a product
product.delete()
```

**Equivalent rhosocial ActiveRecord Queries:**

```python
# Create a new category
category = Category(name='Electronics', description='Electronic devices')
category.save()

# Create a product
product = Product(
    name='Smartphone',
    description='Latest model',
    price=599.99,
    category_id=category.id
)
product.save()

# Get all products
all_products = Product.find().all()

# Filter products
active_products = Product.find().where(Product.is_active == True).all()

# Complex filtering
expensive_electronics = Product.find()\
    .join(Category, Product.category_id == Category.id)\
    .where(Category.name == 'Electronics')\
    .where(Product.price > 500)\
    .where(Product.is_active == True)\
    .all()

# Ordering
products_by_price = Product.find().order_by(Product.price.asc()).all()

# Limiting results
top_5_products = Product.find().order_by(Product.created_at.desc()).limit(5).all()

# Updating a product
product.price = 499.99
product.save()

# Deleting a product
product.delete()
```

## Migrating from Peewee

### Conceptual Differences

| Peewee | rhosocial ActiveRecord |
|--------|---------------------|
| Lightweight, simple API | Full-featured ORM with Active Record pattern |
| Model-centric design | Model-centric design |
| Connection management via model Meta | Connection management via configuration |
| Field-based query construction | Method chaining for queries |

### Model Conversion Examples

**Peewee Model:**

```python
from peewee import *

db = SqliteDatabase('my_app.db')

class BaseModel(Model):
    class Meta:
        database = db

class Person(BaseModel):
    name = CharField()
    birthday = DateField()
    is_relative = BooleanField(default=False)
    
    def __str__(self):
        return self.name

class Pet(BaseModel):
    owner = ForeignKeyField(Person, backref='pets')
    name = CharField()
    animal_type = CharField()
    
    def __str__(self):
        return f'{self.name} ({self.animal_type})'
```

**Equivalent rhosocial ActiveRecord Model:**

```python
from rhosocial.activerecord import ActiveRecord
from typing import Optional
from datetime import date

class Person(ActiveRecord):
    name: str  # Name
    birthday: date  # Birthday
    is_relative: bool = False  # Whether relative, default False
    
    def __str__(self):
        return self.name
    
    def pets(self):
        return self.has_many(Pet, foreign_key='owner_id')

class Pet(ActiveRecord):
    owner_id: int  # Foreign key to person.id
    name: str  # Name
    animal_type: str  # Animal type
    
    def __str__(self):
        return f'{self.name} ({self.animal_type})'
    
    def owner(self):
        return self.belongs_to(Person, foreign_key='owner_id')
```

### Query Conversion Examples

**Peewee Queries:**

```python
# Create a person
person = Person.create(name='John', birthday=date(1990, 1, 1), is_relative=True)

# Create a pet with a relationship
pet = Pet.create(owner=person, name='Fido', animal_type='dog')

# Get all pets belonging to a person
pets = Pet.select().where(Pet.owner == person)

# Join query
query = (Pet
         .select(Pet, Person)
         .join(Person)
         .where(Person.name == 'John'))

# Ordering
pets_by_name = Pet.select().order_by(Pet.name)

# Limiting
first_3_pets = Pet.select().limit(3)

# Update a record
person.name = 'John Smith'
person.save()

# Delete a record
pet.delete_instance()
```

**Equivalent rhosocial ActiveRecord Queries:**

```python
# Create a person
person = Person(name='John', birthday=date(1990, 1, 1), is_relative=True)
person.save()

# Create a pet with a relationship
pet = Pet(owner_id=person.id, name='Fido', animal_type='dog')
pet.save()

# Get all pets belonging to a person
pets = Pet.find().where(Pet.owner_id == person.id).all()

# Join query
pets = Pet.find()\
    .join(Person, Pet.owner_id == Person.id)\
    .where(Person.name == 'John')\
    .all()

# Ordering
pets_by_name = Pet.find().order_by(Pet.name.asc()).all()

# Limiting
first_3_pets = Pet.find().limit(3).all()

# Update a record
person.name = 'John Smith'
person.save()

# Delete a record
pet.delete()
```

## Data Migration Strategies

### 1. Using Database-Level Migration

For simple migrations where the schema remains largely the same:

```python
from rhosocial.activerecord.migration import Migration

class MigrateFromDjangoORM(Migration):
    def up(self):
        # Rename tables if needed
        self.execute("ALTER TABLE django_app_product RENAME TO product")
        
        # Rename columns if needed
        self.execute("ALTER TABLE product RENAME COLUMN product_name TO name")
        
        # Update foreign key constraints if needed
        self.execute("ALTER TABLE product DROP CONSTRAINT django_app_product_category_id_fkey")
        self.execute("ALTER TABLE product ADD CONSTRAINT product_category_id_fkey "
                    "FOREIGN KEY (category_id) REFERENCES category(id)")
```

### 2. Using ETL Process

For complex migrations with significant schema changes:

```python
# Extract data from old ORM
from old_app.models import OldUser
from new_app.models import User

def migrate_users():
    # Get all users from old system
    old_users = OldUser.objects.all()
    
    # Transform and load into new system
    for old_user in old_users:
        user = User(
            username=old_user.username,
            email=old_user.email,
            # Transform data as needed
            status='active' if old_user.is_active else 'inactive'
        )
        user.save()
        
        print(f"Migrated user: {user.username}")
```

### 3. Dual-Write Strategy for Incremental Migration

For gradual migration with minimal downtime:

```python
# In your service layer, write to both ORMs during transition
class UserService:
    def create_user(self, username, email, **kwargs):
        # Create in old ORM
        old_user = OldUser.objects.create(
            username=username,
            email=email,
            is_active=kwargs.get('is_active', True)
        )
        
        # Create in new ORM
        new_user = User(
            username=username,
            email=email,
            status='active' if kwargs.get('is_active', True) else 'inactive'
        )
        new_user.save()
        
        return new_user
```

## Testing the Migration

### 1. Functional Equivalence Testing

Verify that the new implementation produces the same results as the old one:

```python
import unittest

class MigrationTest(unittest.TestCase):
    def test_user_retrieval(self):
        # Test with old ORM
        old_user = OldUser.objects.get(username='testuser')
        
        # Test with new ORM
        new_user = User.find().where(User.username == 'testuser').one()
        
        # Verify results match
        self.assertEqual(old_user.email, new_user.email)
        self.assertEqual(old_user.is_active, new_user.status == 'active')
```

### 2. Performance Testing

Compare performance between old and new implementations:

```python
import time

def benchmark_query():
    # Benchmark old ORM
    start = time.time()
    old_result = OldUser.objects.filter(is_active=True).count()
    old_time = time.time() - start
    
    # Benchmark new ORM
    start = time.time()
    new_result = User.find().where(User.status == 'active').count()
    new_time = time.time() - start
    
    print(f"Old ORM: {old_time:.4f}s, New ORM: {new_time:.4f}s")
    print(f"Results: Old={old_result}, New={new_result}")
```

## Common Challenges and Solutions

### 1. Custom SQL and Database-Specific Features

**Challenge**: Migrating custom SQL or database-specific features.

**Solution**: Use rhosocial ActiveRecord's raw SQL capabilities:

```python
# Old SQLAlchemy raw query
result = session.execute("SELECT * FROM users WHERE last_login > NOW() - INTERVAL '7 days'")

# New ActiveRecord raw query
result = User.find_by_sql("SELECT * FROM users WHERE last_login > NOW() - INTERVAL '7 days'")
```

### 2. Complex Relationships

**Challenge**: Migrating complex relationship patterns.

**Solution**: Break down complex relationships and implement them step by step:

```python
# Define relationships explicitly
class User(ActiveRecord):
    # Basic fields...
    
    def posts(self):
        return self.has_many(Post, foreign_key='user_id')
    
    def comments(self):
        return self.has_many(Comment, foreign_key='user_id')
    
    def commented_posts(self):
        # Implement many-to-many through relationship
        return self.has_many_through(Post, Comment, 'user_id', 'post_id')
```

### 3. Custom Model Methods

**Challenge**: Migrating custom model methods and behaviors.

**Solution**: Implement equivalent methods in the new models:

```python
# Old Django model method
class Order(models.Model):
    # Fields...
    
    def calculate_total(self):
        return sum(item.price * item.quantity for item in self.items.all())

# New ActiveRecord model method
class Order(ActiveRecord):
    # Fields...
    
    def calculate_total(self):
        items = self.items().all()
        return sum(item.price * item.quantity for item in items)
```

## Conclusion

Migrating from one ORM to another requires careful planning, systematic conversion, and thorough testing. By following the patterns and examples in this guide, you can successfully transition your application from SQLAlchemy, Django ORM, or Peewee to rhosocial ActiveRecord while minimizing disruption and maintaining functionality.

Remember that migration is an opportunity to improve your data model and query patterns. Take advantage of rhosocial ActiveRecord's features to enhance your application's database interactions as you migrate.
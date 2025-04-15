# Query Scopes

This document explains how to use query scopes to create reusable query conditions and methods in your ActiveRecord models.

## Introduction

Query scopes are a way to define commonly used query conditions as methods on your model classes. They help you encapsulate query logic, make your code more readable, and eliminate repetition across your application.

## Defining Query Scopes

There are two main approaches to defining query scopes in ActiveRecord:

1. **Instance methods on your model class**
2. **Mixins that add query methods to multiple models**

### Method 1: Model Instance Methods

The simplest way to define query scopes is to add methods to your model class that return query objects:

```python
from rhosocial.activerecord import ActiveRecord

class Article(ActiveRecord):
    __table_name__ = 'articles'
    
    @classmethod
    def published(cls):
        """Scope for published articles."""
        return cls.query().where('status = ?', 'published')
    
    @classmethod
    def recent(cls, days=7):
        """Scope for recently published articles."""
        return cls.query().where(
            'published_at > NOW() - INTERVAL ? DAY', 
            days
        ).order_by('published_at DESC')
    
    @classmethod
    def by_author(cls, author_id):
        """Scope for articles by a specific author."""
        return cls.query().where('author_id = ?', author_id)
```

### Method 2: Query Scope Mixins

For query scopes that apply to multiple models, you can create mixins:

```python
class TimeScopeMixin:
    """Mixin that adds time-based query scopes."""
    
    @classmethod
    def created_after(cls, date):
        """Find records created after the specified date."""
        return cls.query().where('created_at > ?', date)
    
    @classmethod
    def created_before(cls, date):
        """Find records created before the specified date."""
        return cls.query().where('created_at < ?', date)
    
    @classmethod
    def created_between(cls, start_date, end_date):
        """Find records created between the specified dates."""
        return cls.query().where(
            'created_at BETWEEN ? AND ?', 
            start_date, end_date
        )


class SoftDeleteScopeMixin:
    """Mixin that adds soft delete query scopes."""
    
    @classmethod
    def active(cls):
        """Find only active (non-deleted) records."""
        return cls.query().where('deleted_at IS NULL')
    
    @classmethod
    def deleted(cls):
        """Find only soft-deleted records."""
        return cls.query().where('deleted_at IS NOT NULL')
```

Then apply these mixins to your models:

```python
class User(ActiveRecord, TimeScopeMixin, SoftDeleteScopeMixin):
    __table_name__ = 'users'
    # ...

class Post(ActiveRecord, TimeScopeMixin, SoftDeleteScopeMixin):
    __table_name__ = 'posts'
    # ...
```

## Using Query Scopes

Once defined, query scopes can be used like any other query method:

```python
# Using model-specific scopes
recent_articles = Article.published().recent().all()
user_articles = Article.by_author(current_user.id).all()

# Using mixin scopes
recent_users = User.created_after(last_week).active().all()
deleted_posts = Post.deleted().order_by('deleted_at DESC').all()
```

### Combining Multiple Scopes

One of the key benefits of query scopes is that they can be combined with each other and with standard query methods:

```python
# Combining multiple scopes
results = Article.published()\
    .recent(30)\
    .by_author(author_id)\
    .order_by('title')\
    .limit(10)\
    .all()
```

## Dynamic Scopes with Parameters

Scopes can accept parameters to make them more flexible:

```python
class Product(ActiveRecord):
    __table_name__ = 'products'
    
    @classmethod
    def price_range(cls, min_price, max_price):
        """Find products within a price range."""
        return cls.query().where(
            'price BETWEEN ? AND ?', 
            min_price, max_price
        )
    
    @classmethod
    def in_category(cls, category_id):
        """Find products in a specific category."""
        return cls.query().where('category_id = ?', category_id)
    
    @classmethod
    def with_tag(cls, tag):
        """Find products with a specific tag."""
        return cls.query()\
            .join('JOIN product_tags ON products.id = product_tags.product_id')\
            .join('JOIN tags ON product_tags.tag_id = tags.id')\
            .where('tags.name = ?', tag)
```

Usage:

```python
# Find affordable electronics
results = Product.price_range(0, 100)\
    .in_category('electronics')\
    .with_tag('bestseller')\
    .all()
```

## Default Scopes

You can implement default scopes that are automatically applied to all queries for a model by overriding the `query` method:

```python
class Post(ActiveRecord):
    __table_name__ = 'posts'
    
    @classmethod
    def query(cls):
        """Create a new query with default scope applied."""
        # Start with the standard query and apply default conditions
        return super().query().where('is_published = ?', True)
```

With this implementation, all queries on the `Post` model will automatically include the `is_published = True` condition unless explicitly overridden.

## Unscoping

To remove a default scope or reset specific query conditions, you can create a fresh query instance:

```python
# Create a completely fresh query without any default scopes
from rhosocial.activerecord.query import ActiveQuery
all_posts = ActiveQuery(Post).all()  # Creates a new query instance directly

# Or use the query class constructor
all_posts = Post.query().__class__(Post).all()  # Creates a new query instance
```

## Best Practices

1. **Name Scopes Clearly**: Use descriptive names that indicate what the scope does.

2. **Keep Scopes Focused**: Each scope should have a single responsibility.

3. **Document Scope Behavior**: Add docstrings to explain what each scope does and what parameters it accepts.

4. **Consider Composition**: Design scopes that can be effectively combined with other scopes.

5. **Use Parameters Wisely**: Make scopes flexible with parameters, but don't overload them with too many options.

6. **Avoid Side Effects**: Scopes should only modify the query, not perform other actions.

## Custom Query Classes

In addition to query scopes, you can extend query functionality through custom query classes. By setting the `__query_class__` attribute on your model, you can replace the default query instance:

```python
from rhosocial.activerecord import ActiveRecord
from .queries import CustomArticleQuery

class Article(ActiveRecord):
    __table_name__ = 'articles'
    __query_class__ = CustomArticleQuery  # Specify the custom query class
    
    # Model definition continues...
```

### Creating Additional Query Methods

You can also create additional query methods that coexist with the original query method:

```python
class Article(ActiveRecord):
    __table_name__ = 'articles'
    
    @classmethod
    def query_special(cls):
        """Returns a special query instance."""
        from .queries import SpecialArticleQuery
        return SpecialArticleQuery(cls)
```

This way, you can use both default and special queries:

```python
# Using default query
regular_results = Article.query().all()

# Using special query
special_results = Article.query_special().all()
```

## Conclusion

Query scopes are a powerful feature that helps you organize your query logic, reduce code duplication, and create more readable and maintainable code. By defining common query patterns as scopes and utilizing custom query classes, you can simplify complex queries and ensure consistent behavior across your application while maintaining flexibility.
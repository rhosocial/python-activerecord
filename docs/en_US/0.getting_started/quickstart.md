# Configuration Guide

This guide covers how to configure RhoSocial ActiveRecord for different database backends and scenarios.

## Basic Configuration

### SQLite Configuration

SQLite is the built-in backend, perfect for development and small applications:

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.typing import ConnectionConfig

# Basic configuration
class User(ActiveRecord):
    __table_name__ = 'users'
    id: int
    name: str

# File-based database
User.configure(
    ConnectionConfig(database='app.db'),
    backend_class=SQLiteBackend
)

# In-memory database (for testing)
User.configure(
    ConnectionConfig(database=':memory:'),
    backend_class=SQLiteBackend
)
```

### Configuration Options

The `ConnectionConfig` class supports various options:

```python
config = ConnectionConfig(
    # Basic settings
    database='app.db',      # Database name/path
    host='localhost',       # Database host
    port=3306,             # Port number
    username='user',       # Username
    password='pass',       # Password
    charset='utf8mb4',     # Character set
    
    # Connection pool settings
    pool_size=5,           # Connection pool size
    pool_timeout=30,       # Pool timeout in seconds
    
    # SSL configuration
    ssl_ca='ca.pem',       # SSL CA certificate
    ssl_cert='cert.pem',   # SSL certificate
    ssl_key='key.pem',     # SSL private key
    
    # Additional options
    options={              # Backend-specific options
        'timeout': 30,
        'journal_mode': 'WAL'
    }
)
```

## Example Application Configuration

Here's a complete configuration example using our social media application models:

```python
from datetime import datetime
from typing import Optional, List
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.relations import HasMany, BelongsTo

# User model
class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: int
    username: str
    email: str
    created_at: datetime
    
    # Define relationships
    posts: List['Post'] = HasMany('Post', foreign_key='user_id')
    comments: List['Comment'] = HasMany('Comment', foreign_key='user_id')

# Post model
class Post(ActiveRecord):
    __table_name__ = 'posts'
    
    id: int
    user_id: int
    content: str
    created_at: datetime
    
    # Define relationships
    author: User = BelongsTo('User', foreign_key='user_id')
    comments: List['Comment'] = HasMany('Comment', foreign_key='post_id')

# Comment model
class Comment(ActiveRecord):
    __table_name__ = 'comments'
    
    id: int
    post_id: int
    user_id: int
    content: str
    created_at: datetime
    
    # Define relationships
    author: User = BelongsTo('User', foreign_key='user_id')
    post: Post = BelongsTo('Post', foreign_key='post_id')

# Configure all models
def configure_database():
    config = ConnectionConfig(database='social_media.db')
    backend = SQLiteBackend
    
    for model in [User, Post, Comment]:
        model.configure(config, backend_class=backend)
```

## E-Commerce Example Configuration

Here's another configuration example for an e-commerce system:

```python
from decimal import Decimal

class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: int
    email: str
    name: str
    
    orders: List['Order'] = HasMany('Order', foreign_key='user_id')

class Order(ActiveRecord):
    __table_name__ = 'orders'
    
    id: int
    user_id: int
    total: Decimal
    status: str
    created_at: datetime
    
    user: User = BelongsTo('User', foreign_key='user_id')
    items: List['OrderItem'] = HasMany('OrderItem', foreign_key='order_id')

class Product(ActiveRecord):
    __table_name__ = 'products'
    
    id: int
    name: str
    price: Decimal
    stock: int
    
    order_items: List['OrderItem'] = HasMany('OrderItem', foreign_key='product_id')

class OrderItem(ActiveRecord):
    __table_name__ = 'order_items'
    
    id: int
    order_id: int
    product_id: int
    quantity: int
    price: Decimal
    
    order: Order = BelongsTo('Order', foreign_key='order_id')
    product: Product = BelongsTo('Product', foreign_key='product_id')

# Configure all models
def configure_ecommerce_database():
    config = ConnectionConfig(database='ecommerce.db')
    backend = SQLiteBackend
    
    for model in [User, Order, Product, OrderItem]:
        model.configure(config, backend_class=backend)
```

## Environment-Based Configuration

For production applications, use environment variables:

```python
import os
from rhosocial.activerecord.backend.typing import ConnectionConfig

def get_database_config():
    return ConnectionConfig(
        database=os.getenv('DB_NAME', 'app.db'),
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', '3306')),
        username=os.getenv('DB_USER'),
        password=os.getenv('DB_PASS'),
        pool_size=int(os.getenv('DB_POOL_SIZE', '5'))
    )
```

## Next Steps

After configuration:
1. Check [Quickstart](quickstart.md) for basic usage examples
2. Learn about [Models](../1.core/models.md) in detail
3. Explore [Relationships](../1.core/relationships.md) configuration
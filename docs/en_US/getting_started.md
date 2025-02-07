# Getting Started with RhoSocial ActiveRecord

## Installation

RhoSocial ActiveRecord comes with built-in SQLite support, making it easy to get started without additional dependencies.

```bash
pip install rhosocial-activerecord
```

For other databases, install the corresponding backend package:
```bash
# Choose the backend you need
pip install rhosocial-activerecord-mysql    # MySQL support
pip install rhosocial-activerecord-pgsql    # PostgreSQL support
pip install rhosocial-activerecord-oracle   # Oracle support
pip install rhosocial-activerecord-mssql    # SQL Server support
```

## First Steps

### 1. Creating Your First Model

```python
from rhosocial.activerecord import ActiveRecord
from datetime import datetime
from typing import Optional

class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: int
    name: str
    email: str
    created_at: datetime = Field(default_factory=datetime.now)
    deleted_at: Optional[datetime] = None
```

### 2. Configure Database Connection

```python
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.typing import ConnectionConfig

# Configure SQLite database
User.configure(
    ConnectionConfig(database='mydatabase.sqlite3'),
    backend_class=SQLiteBackend
)
```

### 3. Basic Operations

```python
# Create a new user
user = User(name='John Doe', email='john@example.com')
user.save()

# Find a user
user = User.find_one(1)  # By primary key
user = User.find_one({'email': 'john@example.com'})  # By condition

# Update user
user.name = 'Jane Doe'
user.save()

# Delete user
user.delete()
```

### 4. Simple Queries

```python
# Find all users
all_users = User.find_all()

# Query with conditions
active_users = User.query()
    .where('deleted_at IS NULL')
    .order_by('created_at DESC')
    .all()

# Count users
user_count = User.query().count()
```

## Database Schema

RhoSocial ActiveRecord expects your database schema to match your model definitions. For the User model above, you would need a table like this:

### SQLite Example
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    created_at DATETIME NOT NULL,
    deleted_at DATETIME
);
```

## Next Steps

After getting familiar with the basics, you can explore:

1. [Model Definition in Detail](model_definition.md)
2. [Complex Queries](querying.md)
3. [Relationships](relationships.md)
4. [Transactions](transactions.md)

## Configuration Options

The `ConnectionConfig` class supports various options depending on your database backend:

```python
ConnectionConfig(
    # Common options
    database: str,           # Database name or path
    host: str = 'localhost', # Database host
    port: Optional[int] = None,  # Database port
    username: Optional[str] = None,  # Username
    password: Optional[str] = None,  # Password
    
    # Connection pool settings
    pool_size: int = 5,
    pool_timeout: int = 30,
    
    # Character set and timezone
    charset: str = 'utf8mb4',
    timezone: Optional[str] = None,
    
    # SSL configuration
    ssl_ca: Optional[str] = None,
    ssl_cert: Optional[str] = None,
    ssl_key: Optional[str] = None,
    
    # Additional backend-specific options
    options: Dict[str, Any] = {}
)
```

## Common Issues

### Database Connection
- Ensure database file is writable (SQLite)
- Check database credentials
- Verify host and port settings
- Confirm database exists

### Model Definition
- All fields must have type annotations
- Table must exist in database
- Field types must match database schema

### Need Help?
- Check our [Troubleshooting Guide](troubleshooting.md)
- Search [GitHub Issues](https://github.com/rhosocial/python-activerecord/issues)
- Join our [Discord Community](https://discord.gg/rhosocial)
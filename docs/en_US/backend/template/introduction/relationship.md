# Relationship with Core Library

## Architecture Overview

rhosocial-activerecord uses a modular design where the core library (`rhosocial-activerecord`) provides database-agnostic ActiveRecord implementations, and database backends exist as separate extension packages.

The {backend} backend's namespace is located under `rhosocial.activerecord.backend.impl.{backend}`, at the same level as other backends (such as `sqlite`, `dummy`). This means:

- Backends do not participate in ActiveRecord layer changes
- Backends strictly follow backend interface protocols
- Backend updates are decoupled from the core library's ActiveRecord functionality

```
rhosocial.activerecord
├── backend.impl.sqlite      # SQLite backend
├── backend.impl.dummy       # Dummy backend for testing
└── backend.impl.{backend}   # {Backend} backend (this package)
    ├── {Backend}Backend
    ├── Async{Backend}Backend
    └── ...
```

## Backend Responsibilities

The {backend} backend is responsible for the following:

### 1. SQL Dialect Generation

Converts generic query builders into {database}-specific SQL statements:

```python
# Core library: generic query building
query = User.query().where(User.c.age >= 18).order_by(User.c.created_at)

# {backend} backend: converted to {database} SQL
# SELECT * FROM users WHERE age >= 18 ORDER BY created_at
```

### 2. Data Type Mapping

Handles {database}-specific data types. See [Type Adapters](../type_adapters/mapping.md) for the complete mapping table.

### 3. Connection Management

Provides {database} connection establishment, disconnection, and other low-level operations. See [Connection Management](../installation_and_configuration/pool.md) for lifecycle details.

### 4. Transaction Control

Implements {database} transaction BEGIN, COMMIT, ROLLBACK logic. See [Transaction Support](../transaction_support/README.md) for isolation levels and deadlock handling.

## Quick Start

### 1. Installation

```bash
pip install rhosocial-activerecord
pip install rhosocial-activerecord-{backend}
```

### 2. Define Models

```python
import uuid
from typing import ClassVar
from pydantic import Field
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.field import UUIDMixin, DefaultTimestampMixin


class User(UUIDMixin, DefaultTimestampMixin, ActiveRecord):
    username: str = Field(..., max_length=50)
    email: str

    c: ClassVar[FieldProxy] = FieldProxy()

    @classmethod
    def table_name(cls) -> str:
        return 'users'
```

### 3. Configure Backend

```python
from rhosocial.activerecord.backend.impl.{backend} import (
    {Backend}Backend,
    {Backend}ConnectionConfig,
)

config = {Backend}ConnectionConfig(
    host='localhost',
    port={port},
    database='myapp',
    username='user',
    password='password',
)

User.configure(config, {Backend}Backend)
```

### 4. CRUD Operations

```python
# Create
user = User(username='tom', email='tom@example.com')
user.save()

# Read
user = User.query().where(User.c.username == 'tom').one()

# Update
user.email = 'tom.new@example.com'
user.save()

# Delete
user.delete()
```

💡 *AI Prompt:* "What is the ActiveRecord pattern? What are its advantages and disadvantages?"

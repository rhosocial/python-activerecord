# Installation Guide

This guide covers different methods for installing RhoSocial ActiveRecord and its optional components.

## Installing via pip

### Basic Installation

The core package includes SQLite support:

```bash
pip install rhosocial-activerecord
```

### Installing Optional Database Backends

Choose the backends you need:

```bash
# MySQL support
pip install rhosocial-activerecord[mysql]

# PostgreSQL support
pip install rhosocial-activerecord[pgsql]

# Oracle support
pip install rhosocial-activerecord[oracle]

# SQL Server support
pip install rhosocial-activerecord[mssql]

# All database backends
pip install rhosocial-activerecord[databases]
```

### Additional Features

```bash
# Database migrations support
pip install rhosocial-activerecord[migration]

# Install everything (all backends and features)
pip install rhosocial-activerecord[all]
```

## Installing from Source

For development or latest features:

```bash
# Clone the repository
git clone https://github.com/rhosocial/python-activerecord.git
cd python-activerecord

# Install in development mode
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"
```

## Verifying Installation

Test your installation:

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.typing import ConnectionConfig

# Create a test model
class User(ActiveRecord):
    __table_name__ = 'users'
    id: int
    name: str

# Configure with SQLite
User.configure(
    ConnectionConfig(database=':memory:'),
    backend_class=SQLiteBackend
)

print("Installation successful!")
```

## Virtual Environment (Recommended)

It's recommended to use a virtual environment:

```bash
# Create virtual environment
python -m venv venv

# Activate on Unix/macOS
source venv/bin/activate

# Activate on Windows
venv\Scripts\activate

# Install in virtual environment
pip install rhosocial-activerecord
```

## Installation in Production

For production environments:

1. Create a requirements.txt:
```text
rhosocial-activerecord>=1.0.0
rhosocial-activerecord[mysql]  # if using MySQL
```

2. Install with version pinning:
```bash
pip install -r requirements.txt
```

## Troubleshooting

Common installation issues and solutions:

### SQLite Version Issues
If you see SQLite version errors:
```python
import sqlite3
print(sqlite3.sqlite_version)  # Should be 3.35.0 or higher
```

### Database Backend Dependencies
If database backends fail to install:
1. Check system requirements
2. Install required system libraries
3. Install database client libraries

## Next Steps

After installation:
1. Check [Configuration](configuration.md) for database setup
2. Follow [Quickstart](quickstart.md) for basic usage
3. Review core concepts in the [Core Documentation](../1.core/index.md)

## Version Management

To upgrade to the latest version:
```bash
pip install --upgrade rhosocial-activerecord
```

To install a specific version:
```bash
pip install rhosocial-activerecord==1.0.0
```
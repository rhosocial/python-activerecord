# rhosocial ActiveRecord

> **⚠️ 开发阶段声明：** 当前项目尚处于开发阶段，特性随时可能增减，且可能存在缺陷，甚至与实际实现不对应。因此文档内容存在随时调整的可能性，目前仅供参考。

[![PyPI version](https://badge.fury.io/py/rhosocial-activerecord.svg)](https://badge.fury.io/py/rhosocial-activerecord)
[![Python](https://img.shields.io/pypi/pyversions/rhosocial-activerecord.svg)](https://pypi.org/project/rhosocial-activerecord/)
[![Tests](https://github.com/rhosocial/python-activerecord/actions/workflows/test.yml/badge.svg)](https://github.com/rhosocial/python-activerecord/actions)
[![Coverage Status](https://codecov.io/gh/rhosocial/python-activerecord/branch/main/graph/badge.svg)](https://app.codecov.io/gh/rhosocial/python-activerecord/tree/main)
[![License](https://img.shields.io/github/license/rhosocial/python-activerecord.svg)](https://github.com/rhosocial/python-activerecord/blob/main/LICENSE)
[![Powered by vistart](https://img.shields.io/badge/Powered_by-vistart-blue.svg)](https://github.com/vistart)

<div align="center">
    <img src="docs/images/logo.svg" alt="rhosocial ActiveRecord Logo" width="200"/>
    <p>A modern, Pythonic implementation of the ActiveRecord pattern, providing an elegant and intuitive interface for database operations with type safety and rich features.</p>
</div>

## Key Features

- 🎯 Pure Python implementation with no external ORM dependencies
- 🚀 Modern Python features with comprehensive type hints
- 🔒 Type-safe field definitions using Pydantic
- 💾 Built-in SQLite support for immediate use
- 🔄 Rich relationship support (BelongsTo, HasOne, HasMany)
- 🔍 Fluent query builder interface
- 📦 Advanced transaction support with savepoints
- 🎯 Event system for model lifecycle hooks
- 🛡️ Enterprise features: optimistic locking, soft delete, UUID support
- 🔌 Expandable to other databases through optional backend packages

## Requirements

- Python 3.8+
- Pydantic 2.10+
- SQLite 3.25+ (if using SQLite backend)

All dependencies are handled through the package manager with no external ORM requirements.

Note that the sqlite3 version must be greater than 3.25, otherwise it will not work.
You can run the following command to check the sqlite3 version:

```shell
python3 -c "import sqlite3; print(sqlite3.sqlite_version);"
```

As of the release of this software, the latest version of pydantic is 2.11.x. This version supports Python3.13 free-threaded mode (PEP 703).

Note that pydantic 2.11 has dropped support for Python3.8. If you need to use Python3.8, please stick with pydantic 2.10.

Also note that according to Python's official development plan (https://peps.python.org/pep-0703/),
the free-threaded mode will remain experimental for several years and is not recommended for production environments,
even though both pydantic and this project support it.

## Installation

```bash
# Core package with SQLite support
pip install rhosocial-activerecord

# Optional database backends
pip install rhosocial-activerecord[mysql]     # MySQL support
pip install rhosocial-activerecord[mariadb]   # MariaDB support
pip install rhosocial-activerecord[pgsql]     # PostgreSQL support
pip install rhosocial-activerecord[oracle]    # Oracle support
pip install rhosocial-activerecord[mssql]     # SQL Server support

# All database backends
pip install rhosocial-activerecord[databases]

# Additional features
pip install rhosocial-activerecord[migration]  # Database migrations

# Everything
pip install rhosocial-activerecord[all]
```

## Quick Start

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.typing import ConnectionConfig
from datetime import datetime
from typing import Optional

class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: int
    name: str
    email: str
    created_at: datetime
    deleted_at: Optional[datetime] = None

# Configure with built-in SQLite backend
User.configure(
    ConnectionConfig(database='database.sqlite3'),
    backend_class=SQLiteBackend
)

# Create a new user
user = User(name='John Doe', email='john@example.com')
user.save()

# Query users
active_users = User.query()
    .where('deleted_at IS NULL')
    .order_by('created_at DESC')
    .all()

# Update user
user.name = 'Jane Doe'
user.save()

# Delete user
user.delete()
```

## Documentation

Complete documentation is available at [python-activerecord](https://docs.python-activerecord.dev.rho.social/)

- [Getting Started Guide](https://rhosocial-activerecord.readthedocs.io/en/latest/getting_started.html)
- [API Reference](https://rhosocial-activerecord.readthedocs.io/en/latest/api/)
- [Backend Implementation Guide](https://rhosocial-activerecord.readthedocs.io/en/latest/storage_backends/implementing.html)
- [Available Backends](https://rhosocial-activerecord.readthedocs.io/en/latest/storage_backends/available.html)

## Features in Detail
For detailed information about features, including built-in SQLite support, modular backend system, and type safety, please see our [Features Documentation](https://rhosocial-activerecord.readthedocs.io/en/latest/features/).

## Contributing
We welcome and value all forms of contributions! For details on how to contribute, please see our [Contributing Guide](CONTRIBUTING.md).

### Sponsor the Project

Support development through:
- GitHub Sponsors
- Open Collective
- One-time donations
- Commercial support

Your logo will appear here with a link to your website:

[![Donate](https://liberapay.com/assets/widgets/donate.svg)](https://liberapay.com/vistart/donate)

## License

[![license](https://img.shields.io/github/license/rhosocial/python-activerecord.svg)](https://github.com/rhosocial/python-activerecord/blob/main/LICENSE)

Copyright © 2025 [vistart](https://github.com/vistart)

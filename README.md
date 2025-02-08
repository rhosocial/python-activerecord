# RhoSocial ActiveRecord

[![PyPI version](https://badge.fury.io/py/rhosocial-activerecord.svg)](https://badge.fury.io/py/rhosocial-activerecord)
[![Python](https://img.shields.io/pypi/pyversions/rhosocial-activerecord.svg)](https://pypi.org/project/rhosocial-activerecord/)
[![Tests](https://github.com/rhosocial/activerecord/workflows/Tests/badge.svg)](https://github.com/rhosocial/activerecord/actions)
[![Coverage Status](https://coveralls.io/repos/github/rhosocial/activerecord/badge.svg?branch=main)](https://coveralls.io/github/rhosocial/activerecord?branch=main)
[![License](https://img.shields.io/github/license/rhosocial/python-activerecord.svg)](https://github.com/rhosocial/python-activerecord/blob/main/LICENSE)
[![Powered by vistart](https://img.shields.io/badge/Powered_by-vistart-blue.svg)](https://github.com/vistart)

<div align="center">
    <img src="docs/images/logo.png" alt="rhosocial ActiveRecord Logo" width="200"/>
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

- Python 3.10+
- Pydantic 2.10+
- SQLite 3.35+

All dependencies are handled through the package manager with no external ORM requirements.

Note that the sqlite3 version must be greater than 3.35, otherwise it will not work.
You can run the following command to check the sqlite3 version:

```shell
python3 -c "import sqlite3; print(sqlite3.sqlite_version);"
```

Python 3.9 and earlier versions are not currently supported because there is a problem with the `rowcount` parameter
in the result returned by the sqlite3 execution statement.

As of the release of this software, the latest version of pydantic is 2.10.x. As of this version,
Python no-GIL is not supported. Therefore, this software can only run on python3.13, not python3.13t.

## Installation

```bash
# Core package with SQLite support
pip install rhosocial-activerecord

# Optional database backends
pip install rhosocial-activerecord[mysql]     # MySQL support
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
We welcome and value all forms of contributions! For details on how to contribute, please see our [Contributing Guide](https://rhosocial-activerecord.readthedocs.io/en/latest/contributing/).

### Sponsor the Project
Support development through:
- GitHub Sponsors
- Open Collective
- One-time donations
- Commercial support

Your logo will appear here with a link to your website:

[![Sponsor][sponsors-image]][sponsors-url]

[sponsors-image]: https://opencollective.com/rhosocial/sponsors.svg
[sponsors-url]: https://opencollective.com/rhosocial#sponsors

## License

[![license](https://img.shields.io/github/license/rhosocial/python-activerecord.svg)](https://github.com/rhosocial/python-activerecord/blob/main/LICENSE)

Copyright © 2025 [vistart](https://github.com/vistart)

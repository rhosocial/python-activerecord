# Installation

This guide covers how to install rhosocial ActiveRecord and its dependencies.

## Requirements

Before installing rhosocial ActiveRecord, ensure your system meets these requirements:

- **Python**: 3.8 or higher
- **Pydantic**: 2.10+ (for Python 3.8), 2.11+ (for Python 3.9+)
- **SQLite**: 3.25+ (if using the built-in SQLite backend)

> **Note**: You can check your SQLite version with:
> ```shell
> python3 -c "import sqlite3; print(sqlite3.sqlite_version);"
> ```

## Installation Methods

### Basic Installation

To install the core package with SQLite support:

```bash
pip install rhosocial-activerecord
```

This provides everything you need to get started with SQLite as your database backend.

### Optional Database Backends

rhosocial ActiveRecord supports multiple database backends through optional packages:

> **Note**: These optional database backends are currently under development and may not be fully stable for production use.

```bash
# MySQL support
pip install rhosocial-activerecord[mysql]

# MariaDB support
pip install rhosocial-activerecord[mariadb]

# PostgreSQL support
pip install rhosocial-activerecord[pgsql]

# Oracle support
pip install rhosocial-activerecord[oracle]

# SQL Server support
pip install rhosocial-activerecord[mssql]
```

### Complete Installation

To install all database backends:

```bash
pip install rhosocial-activerecord[databases]
```

For all features including database migrations:

```bash
pip install rhosocial-activerecord[all]
```

## Version Compatibility

### Pydantic Compatibility

- **Pydantic 2.10.x**: Compatible with Python 3.8 through 3.12
- **Pydantic 2.11.x**: Compatible with Python 3.9 through 3.13 (including free-threaded mode)

> **Note**: According to Python's official development plan ([PEP 703](https://peps.python.org/pep-0703/)), the free-threaded mode will remain experimental for several years and is not recommended for production environments, even though both Pydantic and rhosocial ActiveRecord support it.

## Verifying Installation

After installation, you can verify that rhosocial ActiveRecord is correctly installed by running:

```python
import rhosocial.activerecord
print(rhosocial.activerecord.__version__)
```

This should print the version number of the installed package.

## Next Steps

Now that you have installed rhosocial ActiveRecord, proceed to [Basic Configuration](basic_configuration.md) to learn how to set up your first database connection.
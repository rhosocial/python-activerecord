# Requirements

Before installing rhosocial ActiveRecord, ensure your environment meets the following requirements:

## Python Version

- Python 3.10 or higher is required
- Python 3.13t (no-GIL version) is not supported due to Pydantic compatibility

## Core Dependencies

- **Pydantic** (2.10.0 or higher)
  - Used for model definition and validation
  - Provides type safety and data validation

- **typing-extensions** (4.12.0 or higher)
  - Required for advanced type hints
  - Ensures compatibility across Python versions

- **pytz** (2025.1 or higher)
  - Handles timezone support
  - Required for datetime operations

- **python-dateutil** (2.9.0 or higher)
  - Additional datetime handling functionality
  - Used for parsing and manipulating dates

- **tzlocal** (5.2 or higher)
  - Local timezone detection
  - Required for automatic timezone handling

## Database Requirements

### SQLite (Built-in)
- SQLite 3.35.0 or higher
- Required for RETURNING clause support
- Check your SQLite version:
  ```python
  python3 -c "import sqlite3; print(sqlite3.sqlite_version);"
  ```

### Optional Database Backends
Each optional backend has its own requirements:

- **MySQL Backend**
  - MySQL 5.7+ or MariaDB 10.3+
  - mysql-connector-python package

- **PostgreSQL Backend**
  - PostgreSQL 10+
  - psycopg2 or psycopg package

- **Oracle Backend**
  - Oracle Database 12c+
  - cx_Oracle package

- **SQL Server Backend**
  - SQL Server 2017+
  - pyodbc package

## Operating System Support

- Linux (all major distributions)
- macOS (10.14 Mojave or newer)
- Windows 10/11
- BSD variants

## Memory and Disk Space

- Minimum 4GB RAM recommended
- ~100MB disk space for installation
- Additional space required for database files

## Development Tools (Optional)

For development and testing:
- pytest (7.0.0+) for testing
- coverage (7.0.0+) for code coverage
- black (23.0.0+) for code formatting
- mypy (1.0.0+) for type checking

## Next Steps

Once you've confirmed your environment meets these requirements:
1. Proceed to [Installation](installation.md)
2. Configure your database following [Configuration](configuration.md)
3. Try the examples in [Quickstart](quickstart.md)
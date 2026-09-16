# Supported Versions

## {database} Version Support

| {database} Version | Support Status | Notes |
|-------------------|----------------|-------|
| x.x | Supported | |
| x.x | Recommended | |

## Python Version Requirements

| Python Version | Support Status |
|---------------|----------------|
| 3.8 | Supported |
| 3.9 | Supported |
| 3.10 | Supported |
| 3.11 | Supported |
| 3.12 | Supported |
| 3.13 | Supported |
| 3.14 | Supported |

## Database Drivers

Each backend uses a specific database driver. The driver handles the low-level communication between Python and the database server.

| Backend | Sync Driver | Async Driver | Package |
|---------|-------------|--------------|---------|
| MySQL | `mysql.connector` | `mysql.connector.aio` | `mysql-connector-python` |
| PostgreSQL | `psycopg` | `psycopg` (AsyncConnection) | `psycopg` |
| SQLite | `sqlite3` (stdlib) | `aiosqlite` | `aiosqlite` (async only) |
| MariaDB | `mariadb` | `mariadb` (asyncConnect) | `mariadb` (v2.0.0+) |
| SQL Server | `pyodbc` | `aioodbc` | `pyodbc` + `aioodbc` (async) |
| Oracle | `oracledb` | `oracledb` (thin mode) | `oracledb` |

### Driver Notes

- **MySQL**: `mysql-connector-python` includes both sync and async support. No separate async package needed.
- **PostgreSQL**: `psycopg` (v3+) is a modern driver with native async support. The same library handles both sync and async.
- **SQLite**: The sync driver (`sqlite3`) is part of Python's standard library. For async, install `aiosqlite` separately.
- **MariaDB**: Requires `mariadb` v2.0.0+ for async support. Earlier versions only support sync.
- **SQL Server**: Requires two packages — `pyodbc` for sync and `aioodbc` for async.
- **Oracle**: `oracledb` supports both sync and async natively in thin mode (no Oracle Client required).

## Dependency Requirements

| Dependency | Version | Notes |
|-----------|---------|-------|
| rhosocial-activerecord | >=1.0.0 | Core library |
| {driver-package} | >=x.x.x | {database} driver |

⚠️ **Important**: This backend only supports {driver-package}. Other drivers are not supported.

## See Also

- [Installation Guide](../installation_and_configuration/installation.md) — setup instructions
- [Introduction](README.md) — sync/async architecture and driver requirements

💡 *AI Prompt:* "What are the differences between {database} versions relevant to this backend?"

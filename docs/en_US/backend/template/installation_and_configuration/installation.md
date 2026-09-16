# Installation Guide

## System Requirements

- Python 3.8+
- {database} x.x+
- pip or poetry

## Installation Steps

### 1. Create a Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate  # Windows
```

### 2. Install Core Library and {database} Backend

```bash
# Install core library
pip install rhosocial-activerecord

# Install {database} backend
pip install rhosocial-activerecord-{backend}
```

### 3. Install {database} Driver

This backend requires `{driver-package}`:

```bash
pip install {driver-package}
```

⚠️ **Note**: This backend does not support other {database} drivers. Please ensure you use `{driver-package}`.

## Async Driver Requirements

If you plan to use the async API (`Async{Backend}Backend`), check whether a separate async driver package is needed:

| Backend | Sync Driver | Async Driver | Separate Package? |
|---------|-------------|--------------|-------------------|
| MySQL | `mysql-connector-python` | `mysql.connector.aio` | No (same package) |
| PostgreSQL | `psycopg` | `psycopg` (AsyncConnection) | No (same library) |
| MariaDB | `mariadb` | `mariadb` (asyncConnect) | No (same library, v2.0.0+) |
| SQL Server | `pyodbc` | `aioodbc` | **Yes** |
| Oracle | `oracledb` | `oracledb` (thin mode) | No (same library) |

For SQL Server async support:

```bash
pip install aioodbc
```

**Note**: Some backends lazy-load their async components. If you import `Async{Backend}Backend` and the async driver is not installed, you will get an `ImportError` at import time.

## Verify Installation

### Synchronous

```python
from rhosocial.activerecord.backend.impl.{backend} import {Backend}Backend

backend = {Backend}Backend(
    host='localhost',
    port={port},
    database='test_db',
    username='root',
    password='password'
)
backend.connect()
print(f"{database} version: {backend.get_server_version()}")
backend.disconnect()
```

### Asynchronous

```python
import asyncio
from rhosocial.activerecord.backend.impl.{backend} import Async{Backend}Backend, {Backend}ConnectionConfig

async def main():
    config = {Backend}ConnectionConfig(
        host='localhost',
        port={port},
        database='test_db',
        username='root',
        password='password'
    )
    backend = Async{Backend}Backend(config)
    await backend.connect()
    print(f"{database} version: {backend.get_server_version()}")
    await backend.disconnect()

asyncio.run(main())
```

**Note**: `{Backend}ConnectionConfig` is shared between sync and async backends — they use the same configuration object.

💡 *AI Prompt:* "What are the advantages of {driver-package}?"

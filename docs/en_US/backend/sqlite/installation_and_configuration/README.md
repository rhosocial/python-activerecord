# Installation and Configuration

## Installation

The SQLite backend is included in the core `rhosocial-activerecord` package. No separate backend package is required.

```bash
pip install rhosocial-activerecord
```

For async support, install `aiosqlite`:

```bash
pip install aiosqlite
```

Or install everything at once:

```bash
pip install rhosocial-activerecord[all]
```

### Dependencies

| Component | Required | Package |
|-----------|----------|---------|
| SQLite driver | Yes | `sqlite3` (Python standard library) |
| Async SQLite driver | For async only | `aiosqlite` |
| Expression system | Yes | `pydantic` 2.x |

No SSL configuration is needed — SQLite is a local file-based database with no network transport.

## Connection Configuration

### SQLiteConnectionConfig

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteConnectionConfig

# In-memory database
config = SQLiteConnectionConfig(database=":memory:")

# File-based database
config = SQLiteConnectionConfig(database="/path/to/database.db")
```

### Database Path

The `database` parameter accepts:

| Value | Behavior |
|-------|----------|
| `":memory:"` | In-memory database (lost on disconnect) |
| `"path/to/file.db"` | Creates or opens a file-based database |
| `"file::memory:"` | Alternative in-memory syntax |

### Connecting

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend

backend = SQLiteBackend(database=":memory:")
backend.connect()

# Use the backend...

backend.disconnect()
```

### Connecting with Async

```python
from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend

backend = AsyncSQLiteBackend(database=":memory:")
await backend.connect()

# Use the backend...

await backend.disconnect()
```

### In-Memory vs File-Based

| Characteristic | In-Memory | File-Based |
|----------------|-----------|------------|
| Persistence | No (lost on disconnect) | Yes |
| Speed | Faster (no disk I/O) | Slightly slower |
| Concurrency | Single connection only | Multiple connections supported |
| Use case | Testing, prototyping | Production, development |

For in-memory databases, each connection gets its own isolated database. Two connections to `:memory:` cannot share data — use a file-based database if you need multiple connections to the same data.

## See Also

- **[Pragma System](../pragma.md)**: Configure SQLite runtime behavior
- **[Transaction Support](../transaction_support/README.md)**: Transaction management

💡 *AI Prompt:* "When should I use an in-memory database versus a file-based database?"

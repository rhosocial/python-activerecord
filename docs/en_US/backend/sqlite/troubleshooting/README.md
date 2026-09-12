# Troubleshooting

This section covers common issues and their solutions for the SQLite backend.

## Database Locked

### Symptom

```
sqlite3.OperationalError: database is locked
```

### Cause

SQLite uses file-level locking. When one connection holds a write lock, other connections block. If a connection holds the lock too long (e.g., within a long-running transaction), other connections may timeout.

### Solutions

1. **Enable WAL mode** — allows concurrent reads during writes:

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend

backend = SQLiteBackend(database="my.db")
backend.connect()
backend.execute("PRAGMA journal_mode = WAL")
```

2. **Set busy timeout** — wait longer before failing:

```python
backend.execute("PRAGMA busy_timeout = 5000")  # 5 seconds
```

3. **Shorten transactions** — commit as soon as possible

4. **Use in-memory database for testing** — no file locking involved:

```python
backend = SQLiteBackend(database=":memory:")
```

## WAL Mode Issues

### Symptom

WAL files (`.db-wal`) not being cleaned up, or database larger than expected.

### Solution

WAL mode requires periodic checkpointing. Force a checkpoint:

```python
backend.execute("PRAGMA wal_checkpoint(TRUNCATE)")
```

Or set auto-checkpoint interval:

```python
backend.execute("PRAGMA wal_autocheckpoint = 1000")  # Every 1000 pages
```

## VACUUM Limitations

### Symptom

```
sqlite3.OperationalError: cannot VACUUM from within a transaction
```

### Cause

VACUUM rebuilds the entire database file and cannot run inside a transaction.

### Solution

Ensure no transaction is active:

```python
# WRONG — inside a transaction
with backend.transaction():
    backend.execute("VACUUM")  # Error!

# CORRECT — outside a transaction
backend.execute("VACUUM")
```

## ALTER TABLE Limitations

### Symptom

```
sqlite3.OperationalError: near "ALTER": syntax error
```

### Cause

SQLite's ALTER TABLE is limited. You cannot ALTER COLUMN, and RENAME/DROP COLUMN require specific versions.

### Solutions

| Operation | Minimum Version | Workaround for Older Versions |
|-----------|-----------------|-------------------------------|
| RENAME COLUMN | 3.25.0+ | Recreate table with new column name |
| DROP COLUMN | 3.35.0+ | Recreate table without the column |
| ALTER COLUMN type | Not supported | Recreate table with new type |

For column type changes, use the standard approach:

```python
# 1. Create new table
# 2. Copy data with transformation
# 3. Drop old table
# 4. Rename new table
```

## AUTOINCREMENT Issues

### Symptom

IDs have gaps, or performance degrades with many deletes.

### Cause

AUTOINCREMENT prevents rowid reuse and maintains a separate `sqlite_sequence` table. Deleted IDs are never reused.

### Solution

For most cases, omit AUTOINCREMENT. The implicit rowid behavior assigns the next available value:

```python
# Without AUTOINCREMENT — faster, allows rowid reuse
class User(ActiveRecord):
    id: int | None = None  # INTEGER PRIMARY KEY (implicit rowid)
    name: str
```

## Network Storage

### Symptom

Frequent database locked errors or data corruption on NFS/network drives.

### Cause

SQLite uses file locking that does not work reliably over network filesystems.

### Solution

Do not use SQLite on NFS, SMB, or similar network storage. For network-accessible databases, use MySQL, PostgreSQL, or another client-server database.

## Memory Issues with In-Memory Databases

### Symptom

Application memory grows when using `:memory:` databases with many connections.

### Cause

Each connection to `:memory:` creates a separate, isolated database. They do not share data.

### Solution

- Use a single connection for in-memory databases
- For testing, use a shared in-memory database with URI:

```python
backend = SQLiteBackend(database="file::memory:?cache=shared", uri=True)
```

## See Also

- [Pragma System](../pragma.md) — Configure SQLite behavior
- [Transaction Support](../transaction_support/README.md) — Transaction management
- [Scenarios](../scenarios/README.md) — Concurrency and deployment patterns
- [Core: Troubleshooting](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/getting_started/troubleshooting)

💡 *AI Prompt:* "What causes database locked errors in SQLite and how do I fix them?"

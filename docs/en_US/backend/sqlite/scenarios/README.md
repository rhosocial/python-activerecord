# Scenarios

## Concurrency Characteristics

SQLite is an embedded database that uses file-level locking for concurrency. Understanding its concurrency model is essential for choosing the right deployment pattern.

### How SQLite Concurrency Works

SQLite uses three locking states:

| Lock State | Description |
|------------|-------------|
| UNLOCKED | No locks held; connection can read or write |
| SHARED | Read lock; multiple connections can read simultaneously |
| RESERVED | Intent to write; no other connection can begin writing |
| EXCLUSIVE | Write lock; only this connection can read or write |

When a connection acquires an EXCLUSIVE lock, all other connections block until the lock is released.

### WAL Mode for Better Concurrency

WAL (Write-Ahead Logging) mode significantly improves concurrency by allowing concurrent reads during writes:

```python
backend.execute("PRAGMA journal_mode = WAL")
```

| Mode | Read during write | Write during read | Concurrent writes |
|------|------------------|-------------------|-------------------|
| DELETE (default) | No | No | No |
| WAL | Yes | Yes | No |

Even in WAL mode, only one write can execute at a time. But reads are never blocked by writes.

## Deployment Patterns

### Single-Process Applications

SQLite works well for single-process applications with no network access:

```python
# Desktop application
backend = SQLiteBackend(database="~/.myapp/data.db")
```

### Multi-Process with WAL

Multiple processes can read simultaneously, but writes are serialized:

```
Process A ──read──→ [database]
Process B ──read──→ [database]
Process C ──write──→ [database]  (blocks until complete)
```

### Not Recommended for Network Storage

Do not use SQLite on NFS, SMB, or similar network filesystems. File locking does not work reliably over networks, leading to data corruption.

| Storage Type | Recommended | Reason |
|-------------|-------------|--------|
| Local SSD/HDD | Yes | Fast, reliable locking |
| USB drive | Caution | May lose data on removal |
| NFS/SMB | No | Unreliable locking |
| Docker volume | Yes (local) | Treats as local storage |
| Cloud disk (EBS, etc.) | Caution | Check locking semantics |

### Multi-User Web Applications

For web applications with multiple concurrent users, consider:

1. **SQLite with WAL** — suitable for read-heavy applications with infrequent writes
2. **MySQL/PostgreSQL** — better for write-heavy applications or many concurrent users

```
# SQLite: Good for
- Personal blogs, portfolios
- Small internal tools
- Read-heavy APIs (< 10 concurrent writers)

# Switch to MySQL/PostgreSQL for
- Social media platforms
- E-commerce with many concurrent orders
- Applications with > 10 concurrent writers
```

### Read Replicas

SQLite does not support built-in replication. For read-heavy workloads, you can implement application-level replication by copying the database file:

```python
import shutil

# Periodic snapshot for read replicas
shutil.copy2("main.db", "readonly_replica.db")
```

Note: This is not real-time replication. Use MySQL or PostgreSQL for true replication.

## Performance Tips

### Connection Pooling

SQLite is a file-based database — there is no connection pool in the traditional sense. Each connection opens the file directly. For in-memory databases, each connection gets its own isolated database.

### PRAGMA Tuning

```python
# Enable WAL for better concurrency
backend.execute("PRAGMA journal_mode = WAL")

# Increase cache size (default is 2000 pages ≈ 8MB)
backend.execute("PRAGMA cache_size = -64000")  # 64MB

# Memory-mapped I/O for large databases
backend.execute("PRAGMA mmap_size = 268435456")  # 256MB

# Optimize synchronous mode for WAL
backend.execute("PRAGMA synchronous = NORMAL")
```

## See Also

- [Troubleshooting](../troubleshooting/README.md) — Common issues and solutions
- [Transaction Support](../transaction_support/README.md) — Transaction management
- [Core Parallel Worker Patterns](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/scenarios/parallel_workers)

💡 *AI Prompt:* "When should I use SQLite versus MySQL or PostgreSQL?"

# {database} Partitioning

## Overview

Table partitioning splits large tables into smaller, more manageable pieces. Partitioning support varies significantly between backends — some backends have comprehensive partitioning capabilities, while others do not support it at all.

### Which Backends Support Partitioning?

| Backend | Partitioning | Strategies |
|---------|-------------|------------|
| PostgreSQL | Yes (PG 10+) | RANGE, LIST, HASH |
| MySQL | Yes (5.1+) | RANGE, LIST, HASH, KEY, COLUMNS, subpartitioning |
| SQLite | **No** | — |
| MariaDB | Yes | RANGE, LIST, HASH, KEY, COLUMNS |
| SQL Server | Yes | RANGE, LIST, HASH (since 2016) |
| Oracle | Yes | RANGE, LIST, HASH, composite, interval |

If your target database does not support partitioning, this section does not apply to you. You can check at runtime:

```python
dialect = backend.dialect

if dialect.supports_table_partitioning():
    # Create partitioned tables
    ...
else:
    # This backend does not support partitioning — use regular tables
    ...
```

> **Core provides a common interface, but partitioning is inherently backend-specific.** The SQL syntax for creating partitions, adding/removing partitions, and managing partition lifecycles differs completely between MySQL and PostgreSQL. rhosocial-activerecord provides backend-specific expression classes for each operation.

## Supported Strategies

### PostgreSQL Partitioning

PostgreSQL supports RANGE, LIST, and HASH partitioning (declarative, since PG 10+):

| Strategy | Description | Example |
|----------|-------------|---------|
| RANGE | Partition by value range | `PARTITION BY RANGE (created_at)` |
| LIST | Partition by discrete values | `PARTITION BY LIST (region)` |
| HASH | Partition by hash of column | `PARTITION BY HASH (user_id)` |

PostgreSQL uses `CREATE TABLE ... PARTITION OF parent FOR VALUES ...` syntax for creating partitions.

### MySQL Partitioning

MySQL supports RANGE, LIST, HASH, and KEY partitioning, plus subpartitioning:

| Strategy | Description | Example |
|----------|-------------|---------|
| RANGE | Partition by value range | `PARTITION BY RANGE (year)` |
| RANGE COLUMNS | Partition by column values | `PARTITION BY RANGE COLUMNS (date)` |
| LIST | Partition by discrete values | `PARTITION BY LIST (region_id)` |
| LIST COLUMNS | Partition by column values | `PARTITION BY LIST COLUMNS (status)` |
| HASH | Partition by hash of column | `PARTITION BY HASH (id)` |
| KEY | Partition by key | `PARTITION BY KEY (id)` |

MySQL supports subpartitioning (partitioning a partition), which PostgreSQL does not.

## Creating a Partitioned Table

> **Partition DDL is not part of the model declaration layer.** Unlike table creation, indexes, and constraints — which you declare on the model class — partitioning requires using backend-specific expression classes directly. `ModelSchemaGenerator` does not generate partition clauses. You must construct the DDL manually.

### PostgreSQL Example

```python
from rhosocial.activerecord.backend.impl.postgres.expression.ddl.partition import (
    PostgresCreatePartitionExpression,
)

# Create a partitioned table via backend-specific expression
# Backend-specific partition expression
```

### MySQL Example

```python
from rhosocial.activerecord.backend.impl.mysql.expression.partition import (
    MySQLPartitionClause,
)

# Create a partitioned table via backend-specific expression
# Backend-specific partition expression
```

## Partition Lifecycle Management

### PostgreSQL Lifecycle

| Operation | Description |
|-----------|-------------|
| `CREATE TABLE ... PARTITION OF parent FOR VALUES ...` | Create a new partition |
| `ALTER TABLE ... ATTACH PARTITION ...` | Attach an existing table as a partition |
| `ALTER TABLE ... DETACH PARTITION ...` | Detach a partition (PG 14+ supports `CONCURRENTLY`) |

### MySQL Lifecycle

| Operation | Description |
|-----------|-------------|
| `ALTER TABLE ... ADD PARTITION` | Add a new partition |
| `ALTER TABLE ... DROP PARTITION` | Drop a partition (data is lost) |
| `ALTER TABLE ... TRUNCATE PARTITION` | Truncate a partition (keep structure) |
| `ALTER TABLE ... REORGANIZE PARTITION` | Merge or split partitions |
| `ALTER TABLE ... EXCHANGE PARTITION` | Swap a partition with a regular table |
| `ALTER TABLE ... COALESCE PARTITION` | Reduce number of HASH/KEY partitions |

## Dialect Feature Detection

```python
# Check if the backend supports partitioning at all
if not dialect.supports_table_partitioning():
    raise UnsupportedError("This backend does not support table partitioning")

# Check specific partition strategies
if dialect.supports_range_table_partitioning():
    # RANGE partitioning is available
    ...

if dialect.supports_list_table_partitioning():
    # LIST partitioning is available
    ...

if dialect.supports_hash_table_partitioning():
    # HASH partitioning is available
    ...

# Check partition lifecycle operations
if dialect.supports_add_partition():
    # Can add partitions
    ...

if dialect.supports_detach_partition():
    # Can detach partitions (PG 14+)
    ...
```

## See Also

- [DDL Operations](../ddl/README.md) — schema management
- [Dialect Expressions](dialect.md) — feature detection and protocol system
- [Core: DDL](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/modeling/ddl)

💡 *AI Prompt:* "When should I use partitioning instead of just adding indexes?"

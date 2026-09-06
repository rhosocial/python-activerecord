# Indexing

## Why Indexes Matter

A database index is a data structure that speeds up data retrieval at the cost of additional storage and slower writes. Without an index, every query that filters or sorts data must scan the entire table — a full table scan. For a table with a million rows, that means reading a million rows even if you only need one.

Indexes are not free. Every index must be updated whenever a row is inserted, updated, or deleted. A table with ten indexes writes ten index entries for every row change. The art of indexing is finding the balance between read speed and write overhead.

## How rhosocial-activerecord Handles Indexes

rhosocial-activerecord lets you declare indexes on your model through the `indexes()` class method. When you run DDL operations, the framework generates the appropriate `CREATE INDEX` statements for your backend.

```python
class User(ActiveRecord):
    username: str
    email: str
    created_at: str

    @classmethod
    def table_name(cls) -> str:
        return 'users'

    @classmethod
    def indexes(cls) -> list:
        return [
            {'columns': ['email'], 'unique': True},
            {'columns': ['created_at']},
        ]
```

The primary key index is automatic — you do not need to declare it. When you define `id: int | None = None` on a model, a primary key index is created automatically.

## Composite Indexes and the Leftmost Prefix Rule

A composite index covers multiple columns. Its order matters: the database can use the index for queries that filter on a **prefix** of the indexed columns, but not for queries that skip a leading column.

Consider this composite index:

```python
{'columns': ['user_id', 'status', 'created_at']}
```

This index accelerates these queries:

- `WHERE user_id = 1` — uses the first column
- `WHERE user_id = 1 AND status = 'active'` — uses the first two columns
- `WHERE user_id = 1 AND status = 'active' AND created_at > '2024-01-01'` — uses all three columns

But it does **not** help with:

- `WHERE status = 'active'` — skips the leading column
- `WHERE created_at > '2024-01-01'` — skips the leading two columns

This is the leftmost prefix rule. When designing composite indexes, put the column most frequently used in `WHERE` clauses first, then the next most frequent, and so on.

## When to Create an Index

The general rule is: **create an index on any column that appears in a `WHERE` clause, a `JOIN` condition, or an `ORDER BY` clause**. But not every column deserves an index.

**Good candidates**:
- Columns with high selectivity (many distinct values, like `email` or `uuid`)
- Columns frequently used in `WHERE` clauses
- Columns used in `JOIN` conditions
- Columns used in `ORDER BY` that need to be sorted frequently

**Poor candidates**:
- Columns with low selectivity (few distinct values, like `boolean` or `status` with only 3-4 values)
- Small tables (full table scan is faster than index lookup)
- Columns that are rarely queried

## Unique Indexes

A unique index enforces that no two rows can have the same value in the indexed column(s). This is stronger than a regular index — it provides both performance and data integrity.

```python
class User(ActiveRecord):
    email: str

    @classmethod
    def indexes(cls) -> list:
        return [
            {'columns': ['email'], 'unique': True},
        ]
```

This prevents duplicate emails and accelerates `User.query().where(User.c.email == 'alice@example.com')`.

## {database}-Specific Index Types

### MySQL Index Types

MySQL InnoDB uses B-tree indexes by default. The storage engine determines which index types are available:

**B-tree indexes** are the default and work for most use cases. They support equality and range queries, and can be used for `ORDER BY` optimization.

**Hash indexes** are available only in MEMORY tables and have limited use cases — they support equality queries but not range queries or `ORDER BY`.

When choosing an index strategy for MySQL, consider the storage engine. InnoDB supports row-level locking and transactions; MyISAM supports table-level locking but was faster for read-heavy workloads in older versions. For most modern applications, InnoDB is the right choice.

```python
class User(ActiveRecord):
    @classmethod
    def engine(cls) -> str:
        return 'InnoDB'
```

### PostgreSQL Index Types

PostgreSQL offers several index types beyond the standard B-tree, each designed for different data patterns:

**B-tree** (default) is the right choice for most queries — equality checks, range queries, and `ORDER BY`. If you do not specify an index type, PostgreSQL uses B-tree.

**GIN** (Generalized Inverted Index) is designed for composite values: arrays, JSONB, and full-text search vectors. Use GIN when you need to search *inside* a column's contents rather than matching the column itself.

```python
class Article(ActiveRecord):
    tags: list  # PostgreSQL array type

    @classmethod
    def indexes(cls) -> list:
        return [
            {'columns': ['tags'], 'type': 'GIN'},
        ]
```

**GiST** (Generalized Search Tree) handles geometric data, range types, and full-text search. Use GiST for spatial queries with PostGIS or for range containment queries.

**BRIN** (Block Range Index) stores the minimum and maximum values for each block of the table. It is very small and works well for large tables where data is naturally ordered (like timestamps on a log table). BRIN is not useful for random data.

**Partial indexes** let you index only the rows that match a condition. This is useful when you frequently query a subset of rows:

```python
class Order(ActiveRecord):
    status: str

    @classmethod
    def indexes(cls) -> list:
        return [
            {
                'columns': ['status'],
                'where': "status = 'pending'",
            },
        ]
```

This index only covers pending orders, making it much smaller and faster to maintain than a full index on `status`.

### Which Backends Support Which Index Features?

| Feature | SQLite | MySQL | PostgreSQL |
|---------|--------|-------|------------|
| B-tree index | Yes | Yes | Yes |
| Hash index | No | Yes (MEMORY only) | Yes |
| GIN index | No | No | Yes |
| GiST index | No | No | Yes |
| BRIN index | No | No | Yes |
| Partial index | Yes | No | Yes |
| Functional index | Yes | No | Yes |
| Concurrent index creation | No | No | Yes (CREATE INDEX CONCURRENTLY) |
| Full-text index | Yes (FTS5) | Yes (FULLTEXT) | Yes (GIN + tsvector) |

## Verifying Index Usage with EXPLAIN

The best way to verify that your indexes are being used is to run EXPLAIN on your queries. EXPLAIN shows the execution plan — whether the database is doing a full table scan or using an index.

```python
result = User.query().where(User.c.email == 'alice@example.com').explain()
for line in result:
    print(line)
```

If you see a full table scan (type `ALL` in MySQL, `Seq Scan` in PostgreSQL), the index is not being used. Common reasons include:

- The column is not indexed
- The index exists but does not match the query pattern (leftmost prefix violation)
- The table is small enough that the optimizer prefers a full scan
- The query uses a function on the indexed column, preventing index use

See [EXPLAIN](explain.md) for detailed usage and output interpretation.

## The Write Overhead Trade-off

Every index slows down writes. When you insert a row, the database must update every index on that table. When you update an indexed column, the database must remove the old index entry and insert a new one.

For write-heavy workloads, be conservative with indexes. A table with twenty indexes will have significantly slower inserts than a table with three. Profile your actual query patterns before adding indexes — do not index every column "just in case."

## See Also

- [EXPLAIN](explain.md) — query plan analysis
- [Dialect Expressions](dialect.md) — feature detection and protocol system
- [Core: Performance](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/performance)

💡 *AI Prompt:* "When should I use a composite index versus multiple single-column indexes?"

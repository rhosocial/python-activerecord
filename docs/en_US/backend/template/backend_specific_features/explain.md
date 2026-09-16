# EXPLAIN

## Overview

EXPLAIN shows the execution plan that {database} uses to execute a query. Each backend has its own EXPLAIN syntax — this document covers the {database}-specific implementation.

### Which Backends Support EXPLAIN?

All backends support basic EXPLAIN. The differences are in options and output formats:

| Feature | SQLite | MySQL | PostgreSQL |
|---------|--------|-------|------------|
| Basic EXPLAIN | Yes | Yes | Yes |
| EXPLAIN ANALYZE | Yes | Yes (8.0.18+) | Yes |
| FORMAT=JSON | No | Yes | Yes (FORMAT JSON) |
| FORMAT=TREE | No | Yes (8.0.16+) | No |
| BUFFERS option | No | No | Yes |
| Cost detail | No | No | Yes |

## {database} EXPLAIN Syntax

### MySQL Syntax

MySQL uses `EXPLAIN` with options placed before the statement:

```sql
EXPLAIN [ANALYZE] [FORMAT=TEXT|JSON|TREE|TRADITIONAL] SELECT ...
```

- `FORMAT=TEXT` — default, human-readable
- `FORMAT=JSON` — structured output
- `FORMAT=TREE` — hierarchical (MySQL 8.0.16+)
- `ANALYZE` — actually executes the query (MySQL 8.0.18+)

### PostgreSQL Syntax

PostgreSQL uses `EXPLAIN` with parenthesized options:

```sql
EXPLAIN [(ANALYZE, BUFFERS, FORMAT JSON)] SELECT ...
```

- `(ANALYZE)` — actually executes the query
- `(BUFFERS)` — shows buffer usage
- `(FORMAT JSON|YAML|XML|TEXT)` — output format

### SQLite Syntax

SQLite uses a simpler syntax:

```sql
EXPLAIN [QUERY PLAN] SELECT ...
```

SQLite does not support `FORMAT=JSON` or `ANALYZE` in the same way as MySQL/PostgreSQL. The `QUERY PLAN` option shows a high-level plan.

## Accessing via Query Builder

```python
# Get EXPLAIN result for a query
result = User.query().where(User.c.age >= 18).explain()

# Iterate over plan lines
for line in result:
    print(line)
```

## Output Formats

### MySQL Result Structure

| Field | Description |
|-------|-------------|
| id | Query step identifier |
| select_type | Type of SELECT |
| table | Table being accessed |
| type | Access type (ALL, index, range, ref, eq_ref, const) |
| possible_keys | Possible indexes |
| key | Index actually used |
| rows | Estimated rows examined |
| Extra | Additional information |

### PostgreSQL Result Structure

PostgreSQL returns plan lines with a single `line` field containing the formatted text.

### SQLite Result Structure

SQLite returns a simplified plan with `id`, `parent`, and `detail` columns.

## EXPLAIN ANALYZE

```python
# Actually execute the query and show real execution stats
result = User.query().where(User.c.age >= 18).explain(analyze=True)
```

**MySQL**: `ANALYZE` actually executes the query and shows actual row counts and timing. Available since MySQL 8.0.18.

**PostgreSQL**: `ANALYZE` actually executes the query. Add `BUFFERS` for more detail: `EXPLAIN (ANALYZE, BUFFERS)`.

**SQLite**: `EXPLAIN QUERY PLAN` shows the plan without executing. SQLite does not have a true `ANALYZE` that executes and shows timing.

## Reading the Output

### What to Look For

| Warning Sign | MySQL | PostgreSQL | Meaning |
|--------------|-------|------------|---------|
| Full table scan | `type: ALL` | `Seq Scan` | No index used — check your WHERE columns |
| Wrong index | `key: NULL` | `Index Scan using other_index` | Optimizer chose differently than expected |
| High row estimate | `rows: 1000000` | `rows=1000000` | Query may be slow — consider adding an index |

### MySQL Access Types (type column)

From best to worst:

| Type | Meaning |
|------|---------|
| `const` | At most one row — primary key or unique index lookup |
| `eq_ref` | One row per join — primary key or unique index |
| `ref` | Index lookup, may return multiple rows |
| `range` | Index range scan |
| `index` | Full index scan (better than ALL) |
| `ALL` | Full table scan — consider adding an index |

### PostgreSQL Scan Types

| Type | Meaning |
|------|---------|
| `Index Scan` | Using an index efficiently |
| `Index Only Scan` | All data comes from the index (best case) |
| `Bitmap Index Scan` | Multiple index lookups combined |
| `Seq Scan` | Full table scan — consider adding an index |

## Version Compatibility

| Feature | Minimum {database} Version |
|---------|---------------------------|
| EXPLAIN | All versions |
| EXPLAIN ANALYZE | MySQL 8.0.18+ / PostgreSQL 9.1+ |
| FORMAT=JSON | MySQL 5.7+ / PostgreSQL 8.0+ |

## Best Practices

1. **Use EXPLAIN before optimizing** — always verify the execution plan before adding indexes
2. **Check for full table scans** — look for `type: ALL` (MySQL) or `Seq Scan` (PostgreSQL)
3. **Verify index usage** — confirm the expected index appears in the output
4. **Compare before/after** — run EXPLAIN before and after adding indexes

## See Also

- [Indexing](indexing.md) — index creation and optimization
- [Dialect Expressions](dialect.md) — feature detection and protocol system
- [Core: Query Explain](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/backend/explain)

💡 *AI Prompt:* "How do I read an EXPLAIN output to find slow queries?"

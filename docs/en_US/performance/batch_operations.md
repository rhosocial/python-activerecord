# Batch Operations

When dealing with large datasets, executing individual queries can be inefficient due to the overhead of repeated database round-trips. The batch execution interface provides a streamlined approach for bulk operations with automatic transaction management and memory-efficient iteration.

## Overview

The backend provides two batch execution methods:

- **`execute_batch_dml`**: Batch execution for DML operations (INSERT, UPDATE, DELETE)
- **`execute_batch_dql`**: Batch execution for DQL operations (SELECT) with pagination

Both methods support synchronous and asynchronous variants with identical APIs.

## Batch DML Operations

### Basic Usage

```python
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.expression import InsertStatement, ValuesSource, Literal
from rhosocial.activerecord.backend.expression.objects import Table

backend = SQLiteBackend(database=":memory:")
backend.connect()
backend.execute(
    "CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT)"
)

# Create a list of INSERT expressions
expressions = []
for i in range(100):
    source = ValuesSource(backend.dialect, values_list=[
        [Literal(backend.dialect, f"user{i}"),
         Literal(backend.dialect, f"user{i}@example.com")]
    ])
    expr = InsertStatement(
        backend.dialect,
        into=Table(backend.dialect, "users"),
        columns=["name", "email"],
        source=source
    )
    expressions.append(expr)

# Execute in batches of 20
for batch_result in backend.execute_batch_dml(expressions, batch_size=20):
    print(f"Batch {batch_result.batch_index}: {batch_result.total_affected_rows} rows affected")
```

### Commit Modes

Batch DML supports two commit modes:

#### WHOLE Mode (Default)

The entire batch operation is wrapped in a single transaction. If any error occurs, all changes are rolled back.

```python
from rhosocial.activerecord.backend.result import BatchCommitMode


def process_batch(batch):
    print(f"Batch {batch.batch_index}: {batch.total_affected_rows} rows affected")


# All-or-nothing: either all batches succeed or none do
for batch in backend.execute_batch_dml(
    expressions,
    batch_size=50,
    commit_mode=BatchCommitMode.WHOLE
):
    process_batch(batch)
```

**Behavior:**
- All batches execute within a single transaction
- If an error occurs mid-batch, all previous batches are rolled back
- Generator exit (break/exception) triggers rollback of the entire operation

#### PER_BATCH Mode

Each batch is committed immediately after execution. If an error occurs, previously committed batches retain their changes.

```python
# Each batch commits independently
for batch in backend.execute_batch_dml(
    expressions,
    batch_size=50,
    commit_mode=BatchCommitMode.PER_BATCH
):
    process_batch(batch)
```

**Behavior:**
- Each batch executes in its own transaction
- Committed batches survive even if later batches fail
- Generator exit does not roll back already-committed batches

### RETURNING Clause Support

For backends that support the RETURNING clause (PostgreSQL, SQLite 3.35+), you can retrieve data from affected rows:

```python
# Get inserted IDs and names
for batch in backend.execute_batch_dml(
    expressions,
    batch_size=10,
    returning_columns=["id", "name"]
):
    for result in batch.results:
        print(f"Inserted: id={result.data[0]['id']}, name={result.data[0]['name']}")
```

**Important:** Using `returning_columns` switches the execution path from efficient `executemany()` to individual `execute()` calls per row. Use this feature judiciously for large batches.

### Expression Requirements

Batch DML requires **homogeneous expressions**:

1. All expressions must be of the same type (all INSERT, all UPDATE, or all DELETE)
2. Expressions must produce the same SQL template (same table, same columns)

```python
# Valid: All INSERT expressions targeting the same table
from rhosocial.activerecord.backend.expression import IntegerColumn, Literal
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.statements import (
    InsertStatement,
    UpdateStatement,
    ValuesSource,
)


def make_insert(name, email):
    return InsertStatement(
        backend.dialect,
        into=Table(backend.dialect, "users"),
        columns=["name", "email"],
        source=ValuesSource(
            backend.dialect,
            values_list=[[Literal(backend.dialect, name), Literal(backend.dialect, email)]],
        ),
    )


def make_update(user_id, name):
    return UpdateStatement(
        backend.dialect,
        Table(backend.dialect, "users"),
        assignments={"name": Literal(backend.dialect, name)},
        where=(IntegerColumn(backend.dialect, "id") == user_id),
    )


expressions = [
    make_insert("user1", "user1@example.com"),
    make_insert("user2", "user2@example.com"),
    make_insert("user3", "user3@example.com"),
]

# Invalid: Mixed expression types
try:
    mixed = [
        make_insert("user1", "user1@example.com"),
        make_update(1, "new_name"),
    ]
    for _ in backend.execute_batch_dml(mixed):
        pass
except TypeError as exc:
    print(f"TypeError: {exc}")
```

## Batch DQL Operations

### Pagination with Lazy Loading

`execute_batch_dql` provides memory-efficient pagination for large result sets:

```python
from rhosocial.activerecord.backend.expression import (
    AllColumnsWildcard,
    NamedRelationRef,
)
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.statements import QueryStatement


def process_row(row):
    return row["id"]


query = QueryStatement(
    backend.dialect,
    select=[AllColumnsWildcard(backend.dialect)],
    from_=NamedRelationRef(backend.dialect, Table(backend.dialect, "users")),
)

# Process 1000-row pages one at a time
for page in backend.execute_batch_dql(query, page_size=1000):
    print(f"Page {page.page_index}: {page.page_size} rows")
    for row in page.data:
        process_row(row)
    # Memory from this page can be released before fetching next
```

### Page Metadata

Each batch result provides useful metadata:

```python
for page in backend.execute_batch_dql(query, page_size=100):
    print(f"Page index: {page.page_index}")
    print(f"Page size: {page.page_size}")
    print(f"Has more pages: {page.has_more}")
    print(f"Total rows this page: {len(page.data)}")
```

### Expression Types

`execute_batch_dql` supports all DQL expression types:

- `QueryStatement`: Basic SELECT queries
- `WithStatement`: Common Table Expressions (CTEs)
- `SetOperationStatement`: UNION, INTERSECT, EXCEPT operations

```python
# CTE example
from rhosocial.activerecord.backend.expression import (
    AllColumnsWildcard,
    NamedRelationRef,
    StringColumn,
)
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.query_parts import WhereClause
from rhosocial.activerecord.backend.expression.query_sources import CTEClause, WithStatement
from rhosocial.activerecord.backend.expression.statements import QueryStatement

backend.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER, status TEXT)")

cte_query = QueryStatement(
    backend.dialect,
    select=[AllColumnsWildcard(backend.dialect)],
    from_=NamedRelationRef(backend.dialect, Table(backend.dialect, "orders")),
    where=WhereClause(
        backend.dialect,
        condition=(StringColumn(backend.dialect, "status") == "open"),
    ),
)
cte = CTEClause(backend.dialect, name="recent_orders", query=cte_query)

main_query = QueryStatement(
    backend.dialect,
    select=[AllColumnsWildcard(backend.dialect)],
    from_=NamedRelationRef(backend.dialect, Table(backend.dialect, "recent_orders")),
)

with_query = WithStatement(backend.dialect, ctes=[cte], query=main_query)


def process_orders(rows):
    return len(rows)


for page in backend.execute_batch_dql(with_query, page_size=50):
    process_orders(page.data)
```

## Async Support

Both batch methods have async equivalents with identical semantics:

```python
# Async batch DML
import asyncio

from rhosocial.activerecord.backend.expression import (
    AllColumnsWildcard,
    InsertStatement,
    Literal,
    NamedRelationRef,
    ValuesSource,
)
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.statements import QueryStatement
from rhosocial.activerecord.backend.impl.sqlite.backend.async_backend import AsyncSQLiteBackend


async def run_async_batches():
    async_backend = AsyncSQLiteBackend(database=":memory:")
    await async_backend.connect()
    await async_backend.execute(
        "CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT)"
    )

    async_dialect = async_backend.dialect
    async_expressions = [
        InsertStatement(
            async_dialect,
            into=Table(async_dialect, "users"),
            columns=["name", "email"],
            source=ValuesSource(
                async_dialect,
                values_list=[[
                    Literal(async_dialect, f"async{i}"),
                    Literal(async_dialect, f"async{i}@example.com"),
                ]],
            ),
        )
        for i in range(10)
    ]

    # Async batch DML
    async for batch in async_backend.execute_batch_dml(async_expressions, batch_size=4):
        print(f"Batch {batch.batch_index}: {batch.total_affected_rows} rows affected")

    # Async batch DQL
    async_query = QueryStatement(
        async_dialect,
        select=[AllColumnsWildcard(async_dialect)],
        from_=NamedRelationRef(async_dialect, Table(async_dialect, "users")),
    )
    async for page in async_backend.execute_batch_dql(async_query, page_size=4):
        print(f"Page {page.page_index}: {page.page_size} rows")

    await async_backend.disconnect()


asyncio.run(run_async_batches())
```

## Transaction Interaction

### External Transaction

When already in a transaction, batch operations respect the existing transaction:

```python
with backend.transaction():
    # Batch operation uses the existing transaction
    for batch in backend.execute_batch_dml(expressions, batch_size=50):
        process_batch(batch)
    # Changes are not committed until the context manager exits
```

### Error Handling

```python
from rhosocial.activerecord.backend.errors import IntegrityError

try:
    for batch in backend.execute_batch_dml(
        expressions,
        batch_size=50,
        commit_mode=BatchCommitMode.WHOLE
    ):
        process_batch(batch)
except IntegrityError as exc:
    # In WHOLE mode: all changes rolled back
    # In PER_BATCH mode: previous batches may be committed
    print(f"Integrity error, batch rolled back: {exc}")
```

## Performance Considerations

1. **Batch Size Selection**:
   - Smaller batches: Lower memory usage, more granular progress
   - Larger batches: Fewer round-trips, better throughput
   - Recommended: 100-1000 rows for most use cases

2. **RETURNING Clause Trade-off**:
   - Without RETURNING: Uses efficient `executemany()`
   - With RETURNING: Uses individual `execute()` per row
   - Consider separate queries if you need RETURNING data

3. **Memory Efficiency**:
   - DQL pagination releases memory after each page
   - DML batches process incrementally
   - Avoid accumulating all results in memory

## Backend Support

| Backend | Batch DML | Batch DQL | RETURNING |
|---------|-----------|-----------|-----------|
| SQLite | Yes | Yes | 3.35+ |
| MySQL | Yes | Yes | No |
| PostgreSQL | Yes | Yes | Yes |

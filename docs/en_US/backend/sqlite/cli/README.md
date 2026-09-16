# Command-Line Interface

## Overview

The SQLite backend includes a command-line interface for database operations. The CLI provides commands for querying, introspecting, and managing SQLite databases without writing Python code.

The CLI commands fall into two categories:

1. **SQLite-specific commands** — SQLite-unique operations (query, introspect, info)
2. **Core inherited commands** — shared across all backends (named-expression, named-procedure, named-migration, named-connection)

## Invocation

The CLI is installed as `rhosocial-activerecord-sqlite` when you install the package:

```bash
pip install rhosocial-activerecord
```

Then invoke commands directly:

```bash
rhosocial-activerecord-sqlite <command> [options]
```

This command is registered in `pyproject.toml` and is equivalent to `python -m rhosocial.activerecord.backend.impl.sqlite`.

## Output Formats

The CLI supports multiple output formats via the `-o` / `--output` option:

| Format | Description | Rich Required |
|--------|-------------|---------------|
| `table` | Human-readable table with borders (default) | Yes |
| `json` | JSON array of objects | No |
| `csv` | Comma-separated values | No |
| `tsv` | Tab-separated values | No |

When Rich is installed, the `table` format provides beautified output with colored borders. When Rich is not available, the CLI automatically falls back to `json` format.

### Rich Integration

The CLI integrates with the [Rich](https://github.com/Textualize/rich) library for enhanced terminal output:

- **Colored borders**: Unicode box-drawing characters for table borders
- **ASCII fallback**: Use `--rich-ascii` to force ASCII borders (`+`, `-`, `|`)
- **Auto-detection**: If Rich is not installed, falls back to JSON output automatically

```bash
# Default table output (Unicode borders)
rhosocial-activerecord-sqlite query "SELECT * FROM users;"

# ASCII borders (for terminals without Unicode support)
rhosocial-activerecord-sqlite query --rich-ascii "SELECT * FROM users;"

# Force JSON output
rhosocial-activerecord-sqlite query -o json "SELECT * FROM users;"
```

### Output Examples

**Table format (default):**
```
┌─────┬─────────┬───────┐
│ id  │ name    │ email │
├─────┼─────────┼───────┤
│ 1   │ Alice   │ a@x   │
│ 2   │ Bob     │ b@x   │
└─────┴─────────┴───────┘
```

**JSON format:**
```json
[
  {"id": 1, "name": "Alice", "email": "a@x"},
  {"id": 2, "name": "Bob", "email": "b@x"}
]
```

**CSV format:**
```csv
id,name,email
1,Alice,a@x
2,Bob,b@x
```

**TSV format:**
```tsv
id	name	email
1	Alice	a@x
2	Bob	b@x
```

## SQLite-Specific Commands

### info

Display environment information without requiring a database connection:

```bash
rhosocial-activerecord-sqlite info
```

Output includes:
- SQLite version number
- Extension support (FTS5, JSON1, R-Tree, etc.)
- Pragma system category counts
- Protocol implementation status

### query

Execute SQL queries directly:

```bash
# Simple query
rhosocial-activerecord-sqlite query "SELECT sqlite_version();"

# Query from database file
rhosocial-activerecord-sqlite query --db-file my.db "SELECT * FROM users;"

# Execute SQL from file
rhosocial-activerecord-sqlite query --file script.sql

# Execute multi-statement script
rhosocial-activerecord-sqlite query --executescript --file dump.sql

# JSON output
rhosocial-activerecord-sqlite query -o json "SELECT * FROM users;"
```

### introspect

Inspect database metadata:

```bash
# List all tables
rhosocial-activerecord-sqlite introspect tables --db-file my.db

# List all views
rhosocial-activerecord-sqlite introspect views --db-file my.db

# Get database information
rhosocial-activerecord-sqlite introspect database --db-file my.db

# Include system tables
rhosocial-activerecord-sqlite introspect tables --db-file my.db --include-system

# Get complete table info (columns, indexes, foreign keys)
rhosocial-activerecord-sqlite introspect table users --db-file my.db

# Query specific details
rhosocial-activerecord-sqlite introspect columns users --db-file my.db
rhosocial-activerecord-sqlite introspect indexes users --db-file my.db
rhosocial-activerecord-sqlite introspect foreign-keys posts --db-file my.db
```

#### Introspection Types

| Type | Description | Table Name Required |
|------|-------------|---------------------|
| `tables` | List all tables | No |
| `views` | List all views | No |
| `database` | Database information | No |
| `table` | Complete table details (columns, indexes, foreign keys) | Yes |
| `columns` | Column information | Yes |
| `indexes` | Index information | Yes |
| `foreign-keys` | Foreign key information | Yes |
| `triggers` | Trigger information | Optional |

## Core Inherited Commands

These commands are **inherited from the core `python-activerecord` library** and work identically across all backends:

| Command | Source Module | Description |
|---------|--------------|-------------|
| `named-expression` | `backend.named_expression` | Execute type-safe parameterized SQL defined in Python |
| `named-procedure` | `backend.named_expression.procedure` | Execute multi-query orchestration with transaction support |
| `named-procedure-graph` | `backend.named_expression.procedure` | Execute procedure graphs (DAG workflows) |
| `named-migration` | `backend.migration` | Execute versioned schema changes with dependency tracking |
| `named-connection` | `backend.named_connection` | Manage and test named connection configurations |

### Why Named Features?

Named features let you **encode complex configurations as a single name**, avoiding verbose command-line arguments and enabling parameter combinations that cannot be expressed through CLI flags alone.

**Named Connection** — encapsulates all connection parameters:

```bash
# Without named connection: long argument list
rhosocial-activerecord-sqlite query \
    --db-file /path/to/production.db \
    --conn-param journal_mode=WAL \
    --conn-param synchronous=FULL \
    --conn-param foreign_keys=1 \
    "SELECT * FROM users"

# With named connection: one name holds everything
rhosocial-activerecord-sqlite query \
    --named-connection myapp.connections.prod_db \
    "SELECT * FROM users"
```

**Named Expression** — encapsulates complex query logic:

```bash
# Without named expression: complex SQL that's hard to shell-escape
rhosocial-activerecord-sqlite query \
    "SELECT u.name, COUNT(o.id) as order_count FROM users u LEFT JOIN orders o ON u.id = o.user_id WHERE o.created_at >= '2026-01-01' GROUP BY u.id HAVING COUNT(o.id) > 5 ORDER BY order_count DESC LIMIT 20"

# With named expression: one name, typed parameters
rhosocial-activerecord-sqlite named-expression \
    myapp.queries.high_value_customers \
    --param since=2026-01-01 --param min_orders=5
```

**Named Procedure** — encapsulates multi-step workflows:

```bash
# Without named procedure: multiple sequential commands
rhosocial-activerecord-sqlite query "BEGIN TRANSACTION; ..."
rhosocial-activerecord-sqlite query "UPDATE inventory ..."
rhosocial-activerecord-sqlite query "INSERT INTO orders ..."
rhosocial-activerecord-sqlite query "COMMIT;"

# With named procedure: one command, transaction managed
rhosocial-activerecord-sqlite named-procedure \
    myapp.workflows.place_order \
    --param user_id=42 --param product_id=100 --param quantity=3
```

| Feature | Benefit |
|---------|---------|
| Named Connection | Store connection config in versionable Python code; share across scripts |
| Named Expression | Encapsulate complex SQL; type-safe parameters; reuse across tools |
| Named Procedure | Multi-query workflows with transaction management; parallel execution |
| Named Migration | Versioned schema changes with dependency tracking; up/down support |

### named-expression

Execute named expressions (parameterized SQL defined in Python modules):

```bash
rhosocial-activerecord-sqlite named-expression \
    myapp.queries.orders_by_status \
    --db-file mydb.sqlite \
    --param status=pending
```

### named-procedure

Execute named procedures:

```bash
rhosocial-activerecord-sqlite named-procedure \
    myapp.procedures.sync_users \
    --db-file mydb.sqlite
```

### named-migration

Execute named migrations:

```bash
# Run migration up
rhosocial-activerecord-sqlite named-migration up add_users_table \
    --db-file mydb.sqlite

# Run migration down
rhosocial-activerecord-sqlite named-migration down add_users_table \
    --db-file mydb.sqlite
```

### named-connection

Manage and test named connection configurations:

```bash
rhosocial-activerecord-sqlite named-connection my_connection \
    --params database=mydb.sqlite
```

## Connection Arguments

SQLite uses file-based connections, so the connection arguments differ from client-server databases:

| Argument | Description |
|----------|-------------|
| `--db-file` | Path to SQLite database file |
| `--file` | SQL file to execute |
| `--named-connection` | Use a named connection configuration |
| `--conn-param` | Additional connection parameters |
| `--async` | Use async backend |
| `--log-level` | Set logging level (DEBUG, INFO, WARNING, ERROR) |

## Global Options

| Option | Description |
|--------|-------------|
| `-h`, `--help` | Show help message and exit |
| `--log-level` | Set logging level (DEBUG, INFO, WARNING, ERROR) |

## Architecture

The CLI follows a consistent architecture:

```
backend/impl/sqlite/
├── __main__.py          # Entry point, builds parser, dispatches to handlers
└── cli/
    ├── __init__.py      # COMMAND_NAMES list, register_commands()
    ├── connection.py    # Connection argument parsing and backend creation
    ├── output.py        # Output format providers (Rich/JSON/CSV/TSV)
    │
    │   # SQLite-specific commands
    ├── info.py          # 'info' command handler
    ├── query.py         # 'query' command handler
    ├── introspect.py    # 'introspect' command handler
    │
    │   # Core inherited commands (thin adapters)
    ├── named_expression.py      # Delegates to core named_expression.cli
    ├── named_procedure.py       # Delegates to core named_expression.procedure.cli
    ├── named_migration.py       # Delegates to core migration.cli
    └── named_connection.py      # Delegates to core named_connection.cli
```

## See Also

- [Installation & Configuration](../installation_and_configuration/README.md) — setup instructions
- [Pragma System](../backend_specific_features/README.md) — PRAGMA configuration
- [Core Named Features](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US) — named connection, expression, procedure, migration documentation

💡 *AI Prompt:* "How do I list all tables in my SQLite database from the command line?"

# Command-Line Interface

## Overview

Every {backend} backend includes a command-line interface (CLI) for database operations. The CLI provides commands for querying, introspecting, and managing your {database} database without writing Python code.

The CLI commands fall into two categories:

1. **Backend-specific commands** — `{database}`-unique operations (query, introspect, info, status)
2. **Core inherited commands** — shared across all backends (named-expression, named-procedure, named-migration, named-connection)

## Invocation

The CLI is installed as `rhosocial-activerecord-{backend}` when you install the package:

```bash
pip install rhosocial-activerecord-{backend}
```

Then invoke commands directly:

```bash
rhosocial-activerecord-{backend} <command> [options]
```

This command is registered in `pyproject.toml` and is equivalent to `python -m rhosocial.activerecord.backend.impl.{backend}`.

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
rhosocial-activerecord-{backend} query ... "SELECT * FROM users;"

# ASCII borders (for terminals without Unicode support)
rhosocial-activerecord-{backend} query ... --rich-ascii "SELECT * FROM users;"

# Force JSON output
rhosocial-activerecord-{backend} query ... -o json "SELECT * FROM users;"
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

## Backend-Specific Commands

These commands are implemented by the {backend} backend and interact directly with `{database}`:

| Command | Description | Connection Required |
|---------|-------------|-------------------|
| `info` | Display environment and protocol information | No |
| `query` | Execute SQL queries | Yes |
| `introspect` | Database introspection (tables, columns, indexes, etc.) | Yes |
| `status` | Display server status and configuration | Yes |

### info

Display environment information without requiring a database connection:

```bash
rhosocial-activerecord-{backend} info
```

### query

Execute SQL queries directly:

```bash
rhosocial-activerecord-{backend} query \
    --host localhost --port {port} --database mydb \
    --user root --password secret \
    "SELECT * FROM users LIMIT 10"
```

### introspect

Inspect database metadata:

```bash
# List all tables
rhosocial-activerecord-{backend} introspect tables \
    --host localhost --port {port} --database mydb

# Describe a specific table
rhosocial-activerecord-{backend} introspect table users \
    --host localhost --port {port} --database mydb

# List columns
rhosocial-activerecord-{backend} introspect columns users \
    --host localhost --port {port} --database mydb
```

#### Introspection Types

Each backend supports different introspection types:

| Type | Description |
|------|-------------|
| `tables` | List all tables |
| `views` | List all views |
| `table` | Describe a specific table |
| `columns` | List columns for a table |
| `indexes` | List indexes for a table |
| `foreign-keys` | List foreign keys for a table |
| `triggers` | List triggers |
| `database` | Database information |

Backend-specific types:

| Backend | Extra Types |
|---------|------------|
| PostgreSQL | `extensions` |
| Oracle | `sequences` |

### status

Display server status:

```bash
rhosocial-activerecord-{backend} status \
    --host localhost --port {port} --database mydb
```

## Core Inherited Commands

These commands are **inherited from the core `python-activerecord` library** and work identically across all backends. The backend CLI simply delegates to shared core infrastructure:

```
Backend CLI adapter (thin wrapper)
    └── Core CLI helper (shared logic)
        ├── Resolver — loads Python callables by fully-qualified name
        ├── Runner — executes with transaction management
        └── CLI adapter — argument parsing and output
```

### Why Named Features?

Named features let you **encode complex configurations as a single name**, avoiding verbose command-line arguments and enabling parameter combinations that cannot be expressed through CLI flags alone.

**Named Connection** — encapsulates all connection parameters:

```bash
# Without named connection: long argument list
rhosocial-activerecord-{backend} query \
    --host prod-db.example.com --port 3306 --database myapp \
    --user readonly --password secret --charset utf8mb4 \
    --conn-param ssl-ca=/path/to/ca.pem \
    --conn-param ssl-cert=/path/to/client-cert.pem \
    --conn-param ssl-key=/path/to/client-key.pem \
    "SELECT * FROM users"

# With named connection: one name holds everything
rhosocial-activerecord-{backend} query \
    --named-connection myapp.connections.prod_readonly \
    "SELECT * FROM users"
```

**Named Expression** — encapsulates complex query logic:

```bash
# Without named expression: complex SQL that's hard to shell-escape
rhosocial-activerecord-{backend} query \
    "SELECT u.name, COUNT(o.id) as order_count FROM users u LEFT JOIN orders o ON u.id = o.user_id WHERE o.created_at >= '2026-01-01' GROUP BY u.id HAVING COUNT(o.id) > 5 ORDER BY order_count DESC LIMIT 20"

# With named expression: one name, typed parameters
rhosocial-activerecord-{backend} named-expression \
    myapp.queries.high_value_customers \
    --param since=2026-01-01 --param min_orders=5
```

**Named Procedure** — encapsulates multi-step workflows:

```bash
# Without named procedure: multiple sequential commands
rhosocial-activerecord-{backend} query "BEGIN TRANSACTION; ..."
rhosocial-activerecord-{backend} query "UPDATE inventory ..."
rhosocial-activerecord-{backend} query "INSERT INTO orders ..."
rhosocial-activerecord-{backend} query "COMMIT;"

# With named procedure: one command, transaction managed
rhosocial-activerecord-{backend} named-procedure \
    myapp.workflows.place_order \
    --param user_id=42 --param product_id=100 --param quantity=3
```

**Named Migration** — encapsulates versioned schema changes with dependencies:

```bash
rhosocial-activerecord-{backend} named-migration up add_users_table
rhosocial-activerecord-{backend} named-migration down add_users_table
```

| Feature | Benefit |
|---------|---------|
| Named Connection | Store connection config in versionable Python code; share across scripts |
| Named Expression | Encapsulate complex SQL; type-safe parameters; reuse across tools |
| Named Procedure | Multi-query workflows with transaction management; parallel execution |
| Named Migration | Versioned schema changes with dependency tracking; up/down support |

### Command Reference

| Command | Source Module | Description |
|---------|--------------|-------------|
| `named-expression` | `backend.named_expression` | Execute type-safe parameterized SQL defined in Python |
| `named-procedure` | `backend.named_expression.procedure` | Execute multi-query orchestration with transaction support |
| `named-procedure-graph` | `backend.named_expression.procedure` | Execute procedure graphs (DAG workflows) |
| `named-migration` | `backend.migration` | Execute versioned schema changes with dependency tracking |
| `named-connection` | `backend.named_connection` | Manage and test named connection configurations |

### named-expression

Execute named expressions (parameterized SQL defined in Python modules):

```bash
rhosocial-activerecord-{backend} named-expression <expression_name> \
    --host localhost --port {port} --database mydb
```

### named-procedure

Execute named procedures:

```bash
rhosocial-activerecord-{backend} named-procedure <procedure_name> \
    --host localhost --port {port} --database mydb
```

### named-migration

Execute named migrations:

```bash
# Run migration up
rhosocial-activerecord-{backend} named-migration up <migration_name> \
    --host localhost --port {port} --database mydb

# Run migration down
rhosocial-activerecord-{backend} named-migration down <migration_name> \
    --host localhost --port {port} --database mydb
```

### named-connection

Manage and test named connection configurations:

```bash
rhosocial-activerecord-{backend} named-connection <connection_name> \
    --params key=value
```

## Connection Arguments

All commands that require a database connection accept these common arguments:

| Argument | Description |
|----------|-------------|
| `--host` | Database server hostname |
| `--port` | Database server port |
| `--database` | Database name |
| `--user` | Authentication username |
| `--password` | Authentication password |
| `--async` | Use async backend |
| `--named-connection` | Use a named connection configuration |
| `--conn-param` | Additional connection parameters |
| `--log-level` | Set logging level (DEBUG, INFO, WARNING, ERROR) |

### Backend-Specific Connection Arguments

Some backends have additional connection arguments:

| Backend | Extra Arguments |
|---------|----------------|
| MySQL | `--charset` |
| PostgreSQL | (none extra) |
| SQL Server | `--trusted-connection`, `--driver`, `--encrypt`/`--no-encrypt`, `--trust-server-certificate` |
| Oracle | `--service` (alias `--database`), `--mode` (thin/thick) |
| Firebird | `--charset`, `--role` |

## Global Options

| Option | Description |
|--------|-------------|
| `-h`, `--help` | Show help message and exit |
| `--log-level` | Set logging level (DEBUG, INFO, WARNING, ERROR) |

## Architecture

The CLI follows a consistent architecture across all backends:

```
backend/impl/<backend>/
├── __main__.py          # Entry point, builds parser, dispatches to handlers
└── cli/
    ├── __init__.py      # COMMAND_NAMES list, register_commands()
    ├── connection.py    # Connection argument parsing and backend creation
    ├── output.py        # Output format providers (Rich/JSON/CSV/TSV)
    │
    │   # Backend-specific commands
    ├── info.py          # 'info' command handler
    ├── query.py         # 'query' command handler
    ├── introspect.py    # 'introspect' command handler
    ├── status.py        # 'status' command handler
    │
    │   # Core inherited commands (thin adapters)
    ├── named_expression.py      # Delegates to core named_expression.cli
    ├── named_procedure.py       # Delegates to core named_expression.procedure.cli
    ├── named_procedure_graph.py # Delegates to core named_expression.procedure.cli
    ├── named_migration.py       # Delegates to core migration.cli
    └── named_connection.py      # Delegates to core named_connection.cli
```

## See Also

- [Installation Guide](../installation_and_configuration/installation.md) — setup instructions
- [Connection Management](../installation_and_configuration/pool.md) — connection configuration
- [Core Named Features](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US) — named connection, expression, procedure, migration documentation

💡 *AI Prompt:* "How do I list all tables in my {database} database from the command line?"

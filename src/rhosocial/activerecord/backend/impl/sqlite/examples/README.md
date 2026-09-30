# SQLite Backend Examples

This directory contains example code demonstrating how to use the rhosocial-activerecord expressions with the SQLite backend.

## Directory Structure

```
examples/
├── cli/
│   ├── __init__.py
│   ├── named_connection_demo.py  # Named Connection CLI demo script.
│   ├── named_procedure_demo.py  # Named Procedure CLI demo script.
│   └── named_query_demo.py  # Named Query CLI demo script.
├── connection/
│   ├── __init__.py
│   └── quickstart.py  # Quick Start: Connect to SQLite and execute queries.
├── ddl/
│   ├── __init__.py
│   ├── alter_table.py  # Alter table: add column, rename column, drop column.
│   ├── create_index.py  # Create an index on an existing table.
│   ├── create_table.py  # Create a table with primary key, auto-increment, and index.
│   ├── drop_table.py  # DROP TABLE - SQLite.
│   ├── unique_index.py  # CREATE UNIQUE INDEX - SQLite.
│   └── view.py  # CREATE VIEW - SQLite.
├── delete/
│   ├── __init__.py
│   └── basic.py  # Delete records and return affected row count.
├── extensions/
│   ├── fts3_4_basic.py  # FTS3/FTS4 full-text search operations.
│   ├── fts5_basic.py  # FTS5 Full-Text Search advanced features demonstration.
│   └── version_353_features.py  # SQLite 3.53.0 new features detection example.
├── insert/
│   ├── __init__.py
│   ├── batch.py  # Batch insert with multiple rows.
│   ├── single.py  # Single Row INSERT - SQLite.
│   ├── upsert.py  # UPSERT (INSERT OR REPLACE / INSERT OR IGNORE) - SQLite.
│   └── with_returning.py  # Insert a record and return the auto-generated ID using RETURNING c
├── named_connections/
│   ├── __init__.py
│   ├── file.py  # File-based database connection examples.
│   └── memory.py  # In-memory database connection examples.
├── named_expressions/
│   ├── __init__.py
│   ├── order_clauses.py  # Clause named expression examples — WHERE / JOIN / GROUP BY / ORDER
│   ├── order_ddl.py  # DDL named expression examples — CREATE / ALTER / DROP.
│   ├── order_dml.py  # DML named expression examples — INSERT / UPDATE / DELETE.
│   ├── order_expressions.py  # Order-related named query examples.
│   ├── order_version_compare.py  # Version-dependent expression — demonstrates ``json_array_insert`` 
│   └── run_order_queries.sh  # Driver — runs order_queries
├── named_migrations/
│   ├── __init__.py
│   ├── demo_all.sh  # Driver — all demo
│   ├── demo_async.sh  # Driver — async demo
│   ├── demo_basic.sh  # Driver — basic demo
│   ├── demo_chain.sh  # Driver — chain demo
│   ├── demo_incompatible.sh  # Driver — incompatible demo
│   ├── demo_params.sh  # Driver — params demo
│   ├── expressions.py  # DDL named expression functions for migration examples.
│   ├── migrations.py  # NamedMigration subclasses for migration examples.
│   ├── run_basic.py  # Driver — runs basic
│   └── run_chain.py  # Driver — runs chain
├── named_procedure_graph/
│   ├── __init__.py
│   ├── monthly_report.py  # Monthly sales report procedure graph.
│   ├── q.py  # Named queries supporting monthly_report_graph.
│   ├── run_examples.sh  # Driver — runs examples
│   └── run_monthly_report.sh  # Driver — runs monthly_report
├── named_procedures/
│   ├── __init__.py
│   ├── diagram_demo.py  # Demo script: Generate static and instance diagrams for order proce
│   ├── order_workflow.py  # Order processing workflow example - demonstrates Named Procedure f
│   └── run_order_workflow.sh  # Driver — runs order_workflow
├── query/
│   ├── __init__.py
│   ├── aggregate.py  # Aggregate query with GROUP BY and HAVING clauses.
│   ├── basic.py  # Basic SELECT query with WHERE, ORDER BY, and LIMIT clauses.
│   ├── cte.py  # CTE (Common Table Expressions): basic and recursive.
│   ├── distinct.py  # SELECT DISTINCT - SQLite.
│   ├── explain.py  # EXPLAIN and Query Plan analysis - SQLite.
│   ├── fulltext.py  # Full-Text Search (FTS5): create virtual table, insert documents, a
│   ├── join.py  # JOIN query with multiple tables.
│   ├── pagination.py  # Pagination using LIMIT/OFFSET - SQLite.
│   ├── predicate.py  # Complex predicates: LIKE, IN, BETWEEN, IS NULL.
│   ├── subquery.py  # Subquery in WHERE clause and FROM clause.
│   ├── union.py  # UNION using SetOperationExpression - SQLite.
│   └── window.py  # Window functions: ROW_NUMBER, LAG, LEAD.
├── schema_diff/
│   ├── __init__.py
│   ├── add_column.py  # Schema diff: detect a column added to an existing table.
│   ├── add_table.py  # Schema diff: detect a newly added table.
│   ├── index_change.py  # Schema diff: detect removed and added indexes between two snapshot
│   └── serialization_roundtrip.py  # Schema diff: roundtrip snapshot to JSON, then diff after deseriali
├── transaction/
│   ├── __init__.py
│   ├── basic.py  # Basic transaction control using transaction manager.
│   ├── exclusive.py  # SQLite transaction modes.
│   └── for_update.py  # FOR UPDATE row locking with SQLite limitations.
├── types/
│   ├── __init__.py
│   └── json_basic.py  # JSON operations using JSON functions.
├── update/
│   ├── __init__.py
│   └── basic.py  # Update records and return the updated IDs using RETURNING clause.
├── README.md  # This file
├── cli_commands.sh  # Runner: CLI subcommand demos
├── concurrency.py  # ConcurrencyAware protocol usage
├── conftest.py  # Example metadata (title / dialect_protocols / priority)
├── run_all_examples.sh         # Runner: executes every example, for CI
└── run_executable_examples.sh  # Runner: executes example groups by name
```

## Example File Format

Each example file follows this structure:

```python
"""
[Title and description of what this example demonstrates.]
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
# Database connection setup code
# Don't copy this when learning the pattern

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
# Core code demonstrating the expression usage
# Copy this part when applying to your project

# ============================================================
# SECTION: Execution (run the expression)
# ============================================================
# Execute the expression against the backend
# This can be included or omitted depending on needs

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
# Cleanup code
# Don't copy this when learning the pattern
```

## Key Principles

1. **Self-contained**: Each example file can be executed independently
2. **Clear sections**: Setup/Teardown are clearly marked as reference only
3. **Pure business logic**: The core expression usage is clean and copyable
4. **No external dependencies**: All setup is within the file itself

## Running Examples

```bash
# Run a specific example (from the repository root)
PYTHONPATH=src python -m rhosocial.activerecord.backend.impl.sqlite.examples.ddl.create_table
```

Prefer the `-m` form. This directory contains a package called `types/`, which
shadows the standard library module of the same name as soon as the working
directory lands on `sys.path` — and running a script by path puts *its own
directory* there. `concurrency.py` sits in this directory, so it has to be run
as a module:

```bash
# Works
PYTHONPATH=src python -m rhosocial.activerecord.backend.impl.sqlite.examples.concurrency

# Fails inside runpy with: module 'types' has no attribute 'ModuleType'
PYTHONPATH=src python .../examples/concurrency.py
```

The error names neither the cause nor the file responsible, so prefer `-m`
throughout. Scripts in subdirectories are unaffected, since only their own
directory is added — but `-m` is the habit worth keeping.

### Batch runner

`run_executable_examples.sh` runs the CLI-facing groups. It finds the repository
root by walking up, honours `DEMO_VENV_PYTHON` (default `python3`), and removes
its temporary databases on exit:

```bash
bash src/rhosocial/activerecord/backend/impl/sqlite/examples/run_executable_examples.sh

# Or a single group
bash .../run_executable_examples.sh named-migration
```

Modes: `all`, `query`, `introspect`, `status`, `named-expression`,
`named-procedure`, `named-procedure-graph`, `named-migration`,
`named-connection`. The `cli/*_demo.py` scripts each spawn several CLI
subprocesses and take roughly 25-30 seconds, so budget for that if you run them.

### Checking every example

`run_all_examples.sh` executes all 55 example modules and reports which ones
failed. Nothing in the test suite runs them, so this is the only thing that
notices an example drifting out of step with the API:

```bash
bash src/rhosocial/activerecord/backend/impl/sqlite/examples/run_all_examples.sh

# Skip the slow cli/*_demo.py scripts, or filter to a subtree
bash .../run_all_examples.sh --fast
bash .../run_all_examples.sh query/
```

It exits non-zero if anything failed and prints the cause. CI runs it on every
push, which is what keeps this directory honest.

## For LLM Context

When using these examples as reference:
- Focus on the **SECTION: Business Logic** portion
- The Setup and Teardown sections are boilerplate for execution only
- Copy the business logic pattern to your own project

## Ruff Static Analysis Exclusions

These example files intentionally use a 4-section format that causes certain ruff warnings.
The following rules are **ignored** for all files in this directory:

- **E402** - Module level import not at top of file
  - Reason: The 4-section format requires imports to be placed in SECTION: Setup
    (after backend/dialect initialization) rather than at the top of the file.
  - This is intentional to make the code more readable in the context of learning.

- **E501** - Line too long (default 120 chars)
  - Reason: Long lines are allowed for SQL examples and demonstration purposes.
  - Core library code should still follow line width limits.

To verify this directory passes ruff with these exclusions, run:

```bash
ruff check src/rhosocial/activerecord/backend/impl/sqlite/examples/ \
  --ignore E402,E501
```

Note: These exclusions only apply to example files. Core library code must pass
all ruff checks including E402 and E501.

# SQLite Backend Examples

This directory contains example code demonstrating how to use the rhosocial-activerecord expressions with the SQLite backend.

## Directory Structure

```
examples/
├── README.md               # This file
├── conftest.py             # Example metadata configuration
├── connection/             # Connection examples
│   ├── __init__.py
│   └── quickstart.py       # Quick start guide - connect, query, result handling
├── ddl/                    # Data Definition Language examples
│   ├── __init__.py
│   ├── create_table.py     # Create table with columns and constraints
│   ├── create_index.py     # Create index on existing table
│   └── alter_table.py      # Alter table structure
├── insert/                 # INSERT operation examples
│   ├── __init__.py
│   ├── with_returning.py   # Insert with RETURNING clause
│   └── batch.py            # Batch insert multiple rows
├── update/                 # UPDATE operation examples
│   ├── __init__.py
│   └── basic.py            # Update with WHERE clause
├── delete/                 # DELETE operation examples
│   ├── __init__.py
│   └── basic.py            # Delete with WHERE clause
├── query/                  # Query (SELECT) examples
│   ├── __init__.py
│   ├── basic.py            # Basic SELECT with WHERE, ORDER BY, LIMIT
│   ├── join.py             # JOIN multiple tables
│   ├── aggregate.py        # GROUP BY and HAVING
│   ├── subquery.py        # Subquery in WHERE clause
│   ├── window.py           # Window functions (ROW_NUMBER, etc.)
│   └── predicate.py        # Complex predicates (LIKE, IN, BETWEEN)
├── transaction/            # Transaction control examples
│   ├── __init__.py
│   └── basic.py            # Basic transaction with context manager
└── types/                  # Type-related examples
    ├── __init__.py
    └── json_basic.py       # JSON operations
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
# Run a specific example
python -m rhosocial.activerecord.backend.impl.sqlite.examples.ddl.create_table

# Run from the examples directory
cd examples
python -m ddl.create_table
```

## For LLM Context

When using these examples as reference:
- Focus on the **SECTION: Business Logic** portion
- The Setup and Teardown sections are boilerplate for execution only
- Copy the business logic pattern to your own project

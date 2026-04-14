# SQLite Backend Examples

This directory contains example code demonstrating how to use the rhosocial-activerecord expressions with the SQLite backend.

## Directory Structure

```
examples/
├── README.md          # This file
├── ddl/               # Data Definition Language examples
│   └── create_table.py
├── insert/            # INSERT operation examples
│   └── with_returning.py
├── update/            # UPDATE operation examples
│   └── basic.py
├── delete/            # DELETE operation examples
│   └── basic.py
├── transaction/       # Transaction control examples
│   └── basic.py
└── types/             # Type-related examples (placeholder)
    └── __init__.py
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
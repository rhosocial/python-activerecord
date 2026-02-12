---
name: expression-dialect
description: Architecture guide for Expression-Dialect separation pattern used in query building
license: MIT
compatibility: opencode
metadata:
  category: architecture
  level: advanced
---

## What I do

Explain the Expression-Dialect separation architecture:
- Expression classes define query structure
- Dialect classes generate backend-specific SQL
- Separation of concerns for multi-backend support
- Type-safe query building

## When to use me

Use this skill when:
- Implementing new query expressions
- Adding new SQL dialect features
- Understanding query architecture
- Debugging SQL generation issues
- Creating custom expressions

## Core Principle

**Expression defines structure. Dialect generates SQL.**

```
Query (ActiveQuery)
  ↓
Expression (SQLColumn)
  ↓ (calls dialect.format_*())
Dialect (SQLiteDialect)
  ↓ (generates SQL)
Backend (StorageBackend)
```

## Golden Rule

**NEVER** concatenate SQL strings in Expression classes:
```python
# WRONG
return f'"{table}"."{column}"'

# CORRECT
return self.dialect.format_column_reference(table, column)
```

## Expression System

Expressions in `backend/expression/` define structure:
```python
class SQLColumn(SQLValueExpression):
    def to_sql(self):
        # Delegate to dialect
        return self.dialect.format_column_reference(self.table, self.name), ()
```

## Dialect System

Dialects in `backend/dialect.py` or `backend/impl/{name}/dialect.py`:
```python
class PostgreSQLDialect(SQLDialectBase):
    def format_identifier(self, identifier):
        return f'"{identifier}"'
    
    def format_column_reference(self, table, column):
        return f'{self.format_identifier(table)}.{self.format_identifier(column)}'
```

## Why This Matters

1. **Backend Agnostic**: Same expressions work with any database
2. **SQL Injection Safe**: Centralized escaping
3. **Extensible**: New backend = new dialect only
4. **Testable**: Structure and SQL tested separately

## Testing
- Test expressions: Verify structure, not SQL
- Test dialects: Verify correct SQL generation

---
name: dev-expression-dialect
description: Architecture guide for the Expression-Dialect separation system in rhosocial-activerecord - expression modules, dialect protocols/mixins, SQL generation rules, and how to add new protocols
license: MIT
compatibility: opencode
metadata:
  category: architecture
  level: advanced
  audience: developers
---

# Expression-Dialect System

Explains the architecture that separates SQL **query construction** (expressions) from SQL
**generation** (dialects), enabling database-agnostic building with per-database formatting.

## Core Principle

**Expression defines structure. Dialect generates SQL.**

```
Query (ActiveQuery)
  ↓
Expression (SQLColumn)      ← calls dialect.format_*()
  ↓
Dialect (SQLiteDialect)     ← generates SQL
  ↓
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

## Advantages Over Other Approaches

- No complex state management — expressions are stateless and pure
- Only 2 steps from expression to SQL; no multi-layer compilation
- Dummy backend is a complete SQL-standard reference; other dialects only override differences
- Test-friendly — SQL generation testable without a database connection
- Fragment generation — any expression can generate SQL independently
- Explicit control — full visibility into when database operations occur

## Relationship Model

```
Expression.to_sql() -> Dialect.format_*() -> SQL string and parameters
```

## Key Components

1. **Expression formatting**: `BaseExpression` subclasses build query structure and delegate
   formatting to dialect methods.
2. **Type adaptation**: plain Python values passed as parameters (e.g. `datetime` in WHERE) are
   converted by the **backend** via `SQLTypeAdapter` (see `dev-backend-development`).

## Expression System Modules

Located under `backend/expression/`:
- `bases.py` — abstract base classes and protocol definitions
- `core.py` — core components (columns, literals, function calls, subqueries)
- `literals.py` — literal value expressions
- `executable.py` — executable statement expressions
- `mixins.py` — operator-overloading capabilities (incl. `AliasableMixin.as_`)
- `operators.py` — binary/unary/arithmetic expressions
- `predicates.py` — WHERE-clause predicates
- `query_parts.py` — query clauses (WHERE, GROUP BY, HAVING, ORDER BY, ...)
- `statements/` — DML/DQL/DDL statements (directory package: `ddl_*`, `dml`, `dql`, `explain`)
- `functions/` — standalone factory functions (directory package)
- `aggregates.py` — aggregation expressions/functions
- `advanced_functions.py` — CASE, CAST, EXISTS, window functions
- `query_sources.py` — VALUES, table functions, CTEs
- `graph.py` — Graph Query (MATCH)
- Additional: `collation.py`, `datetime.py`, `serialization.py`, `transaction.py`,
  `introspection.py`, `xml.py`, `types/`

**Limitation**: the system builds SQL per user intent but does **not** validate standard
compliance or executability — that is the database engine's responsibility.

## Dialect Protocol-Mixin Architecture

- **Protocols** (`protocols.py`): interface contract — what a dialect must implement.
- **Mixins** (`mixins.py`): default SQL-standard implementations dialects can override.
- Every dialect inherits: `SQLDialectBase` + relevant Mixins + relevant Protocols.

### Current Protocols and Mixins (main package)

| Protocol | Mixin | Feature |
|----------|-------|---------|
| `WindowFunctionSupport` | `WindowFunctionMixin` | Window functions (OVER, PARTITION BY) |
| `CTESupport` | `CTEMixin` | CTEs (WITH clause) |
| `AdvancedGroupingSupport` | `AdvancedGroupingMixin` | ROLLUP, CUBE, GROUPING SETS |
| `ReturningSupport` | `ReturningMixin` | RETURNING clause |
| `UpsertSupport` | `UpsertMixin` | UPSERT (ON CONFLICT) |
| `LateralJoinSupport` | `LateralJoinMixin` | LATERAL joins |
| `ArraySupport` | `ArrayMixin` | Array types/operations |
| `JSONSupport` | `JSONMixin` | JSON types/operations |
| `ExplainSupport` | `ExplainMixin` | EXPLAIN |
| `FilterClauseSupport` | `FilterClauseMixin` | FILTER clause |
| `OrderedSetAggregationSupport` | `OrderedSetAggregationMixin` | WITHIN GROUP (ORDER BY) |
| `MergeSupport` | `MergeMixin` | MERGE |
| `TemporalTableSupport` | `TemporalTableMixin` | FOR SYSTEM_TIME |
| `QualifyClauseSupport` | `QualifyClauseMixin` | QUALIFY |
| `LockingSupport` | `LockingMixin` | FOR UPDATE, SKIP LOCKED |
| `GraphSupport` | `GraphMixin` | Graph queries (MATCH) |
| `JoinSupport` | `JoinMixin` | JOIN operations |
| `SetOperationSupport` | `SetOperationMixin` | UNION, INTERSECT, EXCEPT |
| `ILIKESupport` | `ILIKEMixin` | Case-insensitive LIKE |
| `TableSupport` | `TableMixin` | CREATE/DROP/ALTER TABLE |
| `ViewSupport` | `ViewMixin` | CREATE/DROP VIEW |
| `TruncateSupport` | `TruncateMixin` | TRUNCATE TABLE |
| `SchemaSupport` | `SchemaMixin` | CREATE/DROP SCHEMA |
| `IndexSupport` | `IndexMixin` | CREATE/DROP INDEX |
| `SequenceSupport` | `SequenceMixin` | CREATE/DROP/ALTER SEQUENCE |
| `TriggerSupport` | `TriggerMixin` | CREATE/DROP TRIGGER (SQL:1999) |
| `FunctionSupport` | `FunctionMixin` | CREATE/DROP FUNCTION (SQL/PSM) |

### Where to Add Features

**Main package** when: defined in SQL standard (SQL:1999–2016); widely supported across DBs; a
DDL or DML construct. **Dialect extension** when: dialect-specific; differs across databases;
vendor-proprietary.

Examples: `CREATE TRIGGER`/`CREATE FUNCTION` → main package; `COMMENT ON`, `CREATE TYPE ...
AS ENUM`, `BIGSERIAL` → PostgreSQL; `AUTO_INCREMENT` → MySQL.

### Adding a New Protocol

```python
# 1. main package protocols.py
@runtime_checkable
class NewFeatureSupport(Protocol):
    def supports_new_feature(self) -> bool: ...
    def format_new_feature_statement(self, expr): ...

# 2. main package mixins.py (SQL-standard default)
class NewFeatureMixin:
    def supports_new_feature(self): return False
    def format_new_feature_statement(self, expr): ...

# 3. dialect extension: override in {backend}/dialect.py

# 4. dummy dialect: add NewFeatureMixin/NewFeatureSupport, support returns True

# 5. tests: tests/.../dummy2/test_new_feature.py (expression),
#    tests/.../dummy/test_dummy_protocol_support.py (protocol support)
```

## Why This Matters

1. Backend agnostic — same expressions work with any database
2. SQL injection safe — centralized escaping
3. Extensible — new backend = new dialect only
4. Testable — structure and SQL tested separately

## Testing

- Expressions: verify structure, not SQL
- Dialects: verify correct SQL generation
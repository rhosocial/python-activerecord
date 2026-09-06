# Type Adapters

## Overview

Type adapters handle the conversion between {database} data types and Python types. rhosocial-activerecord provides built-in adapters for common types and allows you to create custom adapters for specialized use cases.

## Architecture: How Type Conversion Works

rhosocial-activerecord uses a **two-layer type system** for converting between Python types and SQL types:

### Layer 1: Core DataType Hierarchy

The core library defines generic `DataType` classes in `rhosocial.activerecord.backend.expression.types`:

```python
from rhosocial.activerecord.backend.expression.types import (
    IntegerType,
    VarCharType,
    BooleanType,
    TimestampType,
    JsonType,
)
```

These core types are **backend-agnostic** — they define the logical type without specifying exact SQL syntax. When you declare a field as `str`, `int`, or `bool` on a model, the framework maps it to the appropriate core DataType.

### Layer 2: Backend-Specific DataType Subclasses

Each backend extends core types with database-specific behavior:

| Backend | Core Type | Backend Type | Behavior |
|---------|-----------|-------------|----------|
| MySQL | `IntegerType` | `MySQLIntType` | Adds `AUTO_INCREMENT` |
| PostgreSQL | `IntegerType` | `PostgresSerialType` | Maps to `SERIAL` |
| PostgreSQL | `UUIDType` | `PostgresUUIDType` | Native UUID type |
| PostgreSQL | `JsonBType` | `PostgresJSONBType` | Binary JSON |

### The Conversion Flow

```
Python field declaration
    ↓
Core DataType (e.g., IntegerType)
    ↓
Dialect.suggest_column_type() → maps to backend-specific type
    ↓
Backend DataType (e.g., MySQLIntType)
    ↓
Dialect.format_data_type() → generates SQL type string
```

### Type Adapter Registration

Type adapters register conversion functions between Python types and SQL types:

```python
# Built-in adapters are registered automatically
# Custom adapters extend the mapping for specialized types
```

## Contents

- [Type Mapping](mapping.md): {database} to Python type conversion table
- [Custom Adapters](custom.md): Extending type support with custom adapters
- [Timezone Handling](timezone.md): Timestamp and timezone configuration

## Checking Type Support

You can check if the backend supports a specific type at runtime:

```python
from rhosocial.activerecord.backend.dialect.protocols import JSONSupport, ArraySupport

dialect = backend.dialect

# Check JSON support
if isinstance(dialect, JSONSupport) and dialect.supports_json_type():
    # JSON type is available
    ...

# Check array support
if isinstance(dialect, ArraySupport) and dialect.supports_array_type():
    # Array type is available
    ...
```

## See Also

- [Backend Specific Features: Field Types](../backend_specific_features/field_types.md) — DataType hierarchy and backend-specific types
- [Dialect Expressions](../backend_specific_features/dialect.md) — feature detection and protocol system
- [Core: Custom Types](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/modeling/custom_types)

💡 *AI Prompt:* "How does the type system convert between Python types and {database} types?"

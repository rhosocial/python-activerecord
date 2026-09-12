# Field Types

## Two-Layer Type System

rhosocial-activerecord's type system has two layers:

1. **Core DataType hierarchy** — Generic type classes (`IntegerType`, `VarCharType`, `BooleanType`, etc.) in `rhosocial.activerecord.backend.expression.types` define common behavior. When you declare a field as `str`, `int`, or `bool` on a model, the framework maps it to the appropriate core DataType.

2. **Backend-specific DataType subclasses** — Each backend extends core types with database-specific behavior. For example, `MySQLIntType` adds AUTO_INCREMENT support, and `PostgresUUIDType` maps to PostgreSQL's native UUID type. Backend types are in `rhosocial.activerecord.backend.impl.{backend}.expression.types`.

## Core DataType Hierarchy

The following core types are available across all backends:

### Numeric Types

| Core Type | Python Type | Parameters | Description |
|-----------|-------------|------------|-------------|
| `IntegerType` | `int` | — | Standard integer |
| `BigIntType` | `int` | — | Large integer |
| `SmallIntType` | `int` | — | Small integer |
| `TinyIntType` | `int` | — | Tiny integer |
| `FloatType` | `float` | `precision: Optional[int]` | Floating point with optional binary precision |
| `RealType` | `float` | — | Single precision (4 bytes) |
| `DoubleType` | `float` | — | Double precision (8 bytes) |
| `DecimalType` | `Decimal` | `precision: Optional[int]`, `scale: Optional[int]` | Exact fixed-point numeric |

The `precision` and `scale` parameters on numeric types control the exact representation:

- `DecimalType(precision=10, scale=2)` — up to 10 digits total, 2 after decimal point (e.g., `99999999.99`)
- `DecimalType(precision=5)` — up to 5 digits total, no decimal point
- `FloatType(precision=24)` — single-precision (24-bit mantissa)
- `FloatType(precision=53)` — double-precision (53-bit mantissa)

```python
from rhosocial.activerecord.backend.expression.types.numeric import DecimalType

# DECIMAL(10, 2) — price with 2 decimal places
price_type = DecimalType(precision=10, scale=2)

# DECIMAL(5) — quantity, no decimals
quantity_type = DecimalType(precision=5)
```

### String Types

| Core Type | Python Type | Parameters | Description |
|-----------|-------------|------------|-------------|
| `CharType` | `str` | `length: Optional[int]` | Fixed-length string |
| `VarCharType` | `str` | `length: Optional[int]` | Variable-length string |
| `TextType` | `str` | — | Unlimited text |

The `length` parameter controls the maximum string length:

- `VarCharType(length=255)` — VARCHAR(255)
- `CharType(length=10)` — CHAR(10)
- `VarCharType()` — VARCHAR (no explicit limit, database default)

```python
from rhosocial.activerecord.backend.expression.types.string import VarCharType

# VARCHAR(100) — username
username_type = VarCharType(length=100)

# VARCHAR — no explicit limit
email_type = VarCharType()
```

### Enum Types

| Core Type | Python Type | Parameters | Description |
|-----------|-------------|------------|-------------|
| `EnumType` | `str` | `values: List[str]` (required) | Enumerated string values |

`EnumType(values=['S', 'M', 'L'])` — native ENUM on MySQL/MariaDB; backends without a native ENUM type suggest a replacement via `suggested_data_types()` (e.g. SQLite suggests text).

### Boolean Type

| Core Type | Python Type | Description |
|-----------|-------------|-------------|
| `BooleanType` | `bool` | Boolean |

### Date/Time Types

| Core Type | Python Type | Parameters | Description |
|-----------|-------------|------------|-------------|
| `DateType` | `date` | — | Date only (year-month-day) |
| `TimeType` | `time` | `precision: Optional[int]` | Time only, second-fraction precision |
| `TimeTzType` | `time` | `precision: Optional[int]` | Time with timezone |
| `DateTimeType` | `datetime` | `precision: Optional[int]` | Date + time (MySQL/SQLite) |
| `TimestampType` | `datetime` | `precision: Optional[int]` | Timestamp (SQL standard) |
| `TimestampTzType` | `datetime` | `precision: Optional[int]` | Timestamp with timezone |
| `IntervalType` | — | `fields: Optional[str]` | Time span (e.g., `'YEAR'`, `'DAY TO SECOND'`) |

The `precision` parameter on time types controls sub-second precision (0-9 digits):

- `TimestampType(precision=0)` — TIMESTAMP (no fractional seconds)
- `TimestampType(precision=6)` — TIMESTAMP(6) (microsecond precision, default)
- `TimestampType(precision=3)` — TIMESTAMP(3) (millisecond precision)

```python
from rhosocial.activerecord.backend.expression.types.datetime_ import TimestampType

# TIMESTAMP — no fractional seconds
ts_type = TimestampType(precision=0)

# TIMESTAMP(6) — microsecond precision
ts_micro_type = TimestampType(precision=6)
```

### Binary Types

| Core Type | Python Type | Parameters | Description |
|-----------|-------------|------------|-------------|
| `BinaryType` | `bytes` | `length: Optional[int]` | Fixed-length binary |
| `VarBinaryType` | `bytes` | `length: Optional[int]` | Variable-length binary |
| `BlobType` | `bytes` | — | Binary large object |

### JSON Types

| Core Type | Python Type | Description |
|-----------|-------------|-------------|
| `JsonType` | `dict` | JSON |
| `JsonBType` | `dict` | Binary JSON (PostgreSQL-specific) |

### Other Types

| Core Type | Python Type | Description |
|-----------|-------------|-------------|
| `UUIDType` | `UUID` | UUID |
| `ArrayType` | `list` | Array |

### Automatic Mapping

When you define a model, Python types are automatically mapped to core DataTypes:

```python
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from typing import ClassVar


class User(ActiveRecord):
    id: int | None = None        # maps to IntegerType
    name: str                     # maps to VarCharType
    email: str                    # maps to VarCharType
    age: int                      # maps to IntegerType
    balance: float                # maps to FloatType
    is_active: bool               # maps to BooleanType
    metadata: dict                # maps to JsonType

    c: ClassVar[FieldProxy] = FieldProxy()

    @classmethod
    def table_name(cls) -> str:
        return 'users'
```

## {database}-Specific DataType Subclasses

The {backend} backend extends core types with {database}-specific behavior and adds types that have no core equivalent.

### MySQL-Specific Types

| Type | Extends | Description |
|------|---------|-------------|
| `MySQLIntType` | `IntegerType` | AUTO_INCREMENT support |
| `MySQLEnumType` | — | ENUM column with integer storage optimization |
| `MySQLSetType` | — | SET type |
| `MySQLVectorType` | — | MySQL 9.0+ vector operations |
| `MySQLGeometryType` | — | Spatial data |

### PostgreSQL-Specific Types

| Type | Extends | Description |
|------|---------|-------------|
| `PostgresSerialType` | `IntegerType` | SERIAL auto-increment |
| `PostgresBigSerialType` | `BigIntType` | BIGSERIAL auto-increment |
| `PostgresUUIDType` | `UUIDType` | Native UUID |
| `PostgresByteaType` | `BlobType` | Binary data |
| `PostgresInetType` | — | IP address |
| `PostgresJSONBType` | `JsonBType` | Binary JSON |
| `PostgresTSVectorType` | — | Full-text search vector |
| `PostgresHstoreType` | — | Key-value store |
| `PostgresArrayType` | `ArrayType` | Native array |

### Which Backends Support JSON?

| Backend | JSON Support | Notes |
|---------|-------------|-------|
| MySQL | Yes (5.7.8+) | JSON type, `->`, `->>` operators |
| PostgreSQL | Yes | JSON and JSONB types, rich operator set |
| SQLite | Yes (3.38.0+ or JSON1 ext) | JSON type, `->`, `->>` operators |
| SQL Server | Yes (2016+) | JSON functions, `OPENJSON` |

### Which Backends Support Arrays?

| Backend | Array Support | Notes |
|---------|-------------|-------|
| MySQL | No | — |
| PostgreSQL | Yes | Native array type with `ARRAY[]` syntax |
| SQLite | No | — |
| SQL Server | No | — |

## Type Constants

{database} provides type constants for DDL operations. These are available in `rhosocial.activerecord.backend.impl.{backend}.types`:

```python
from rhosocial.activerecord.backend.impl.{backend}.types import (
    {DB}_INTEGER,
    {DB}_BIGINT,
    {DB}_VARCHAR,
    {DB}_TEXT,
    {DB}_BOOLEAN,
    {DB}_JSON,
    # ... more types
)
```

## Using Backend-Specific Types

To use a {database}-specific type, import it from the backend's type module:

<!-- Document how to use backend-specific types in models. Example:

```python
from rhosocial.activerecord.backend.impl.{backend}.types import {DB}_ENUM

class Order(ActiveRecord):
    status: str = Field(..., enum=['pending', 'shipped', 'delivered'])
```

-->

## Checking Type Support

You can check if a backend supports a specific type at runtime:

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

- [Type Adapters](../type_adapters/README.md) — type mapping between {database} and Python
- [Dialect Expressions](dialect.md) — feature detection and protocol system
- [Core: Custom Types](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/modeling/custom_types)

💡 *AI Prompt:* "What {database}-specific types are available in rhosocial-activerecord?"

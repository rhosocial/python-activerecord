# Type Mapping

## Overview

This document shows how {database} data types map to Python types. The mapping is handled automatically by the type adapter system — you typically do not need to configure it manually.

## Standard Mappings

| {database} Type | Python Type | Notes |
|----------------|-------------|-------|
| INTEGER | int | |
| BIGINT | int | |
| SMALLINT | int | |
| DECIMAL | Decimal | |
| FLOAT | float | |
| DOUBLE | float | |
| VARCHAR | str | |
| TEXT | str | |
| DATE | date | |
| TIME | time | |
| DATETIME | datetime | |
| TIMESTAMP | datetime | |
| BOOLEAN | bool | |
| BLOB | bytes | |
| JSON | dict | |

<!-- Document backend-specific type mappings. Examples:

## {database}-Specific Mappings

### ENUM

| {database} Type | Python Type | Notes |
|----------------|-------------|-------|
| ENUM | str | With validation against allowed values |

### SET

| {database} Type | Python Type | Notes |
|----------------|-------------|-------|
| SET | set | |

### JSON (MySQL)

| {database} Type | Python Type | Notes |
|----------------|-------------|-------|
| JSON | dict | Native JSON storage |

### ARRAY (PostgreSQL)

| {database} Type | Python Type | Notes |
|----------------|-------------|-------|
| INTEGER[] | list[int] | |
| TEXT[] | list[str] | |
| UUID[] | list[UUID] | |

### JSONB (PostgreSQL)

| {database} Type | Python Type | Notes |
|----------------|-------------|-------|
| JSONB | dict | Binary JSON with indexing |

### UUID (PostgreSQL)

| {database} Type | Python Type | Notes |
|----------------|-------------|-------|
| UUID | UUID | Native UUID type |

-->

## Usage Example

```python
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from typing import ClassVar


class User(ActiveRecord):
    name: str            # maps to VARCHAR
    age: int             # maps to INTEGER
    balance: float       # maps to FLOAT
    is_active: bool      # maps to BOOLEAN

    c: ClassVar[FieldProxy] = FieldProxy()

    @classmethod
    def table_name(cls) -> str:
        return 'users'
```

💡 *AI Prompt:* "What {database} type should I use for storing UUIDs?"

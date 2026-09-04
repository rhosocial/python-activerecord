# src/rhosocial/activerecord/examples/ddl_types.py
"""Shared example: an ActiveRecord with explicitly declared SQL column types.

This model is a cross-backend demonstration of ``UseSqlType`` after the
"generic / backend-specific type vocabulary" refactor. Every field carries a
core **generic** ``DataType``, which each backend renders to its own native SQL:

- SQLite:  ``VARCHAR(100)`` → ``TEXT``, ``BOOLEAN`` → ``NUMERIC``, ...
- MySQL:   ``VARCHAR(100)`` → ``VARCHAR(100)``, ``BOOLEAN`` → ``BOOLEAN``, ...
- PostgreSQL: ``VARCHAR(100)`` → ``VARCHAR(100)``, ``JSON`` → ``JSON``, ...

The model needs no backend configured to generate DDL — pass a dialect
explicitly to ``generate_create_table(dialect=...)`` (or configure the model's
backend). Backends without a connection can render DDL from a standalone
dialect instance.

Example::

    from rhosocial.activerecord.examples.ddl_types import TypedUser
    from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

    # (1) Explicit dialect — no backend/connection required.
    sql, params = TypedUser.generate_create_table(dialect=SQLiteDialect()).to_sql()

    # (2) Reuse the model's configured backend dialect (dialect=None default).
    from rhosocial.activerecord.backend.config import ConnectionConfig
    from rhosocial.activerecord.backend.impl.sqlite.backend.sync import SQLiteBackend
    TypedUser.configure(ConnectionConfig(database=":memory:"), SQLiteBackend)
    sql, params = TypedUser.generate_create_table().to_sql()
"""

import sys

if sys.version_info >= (3, 9):
    from typing import Annotated, Optional
else:  # pragma: no cover - Python 3.8
    from typing import Optional

    from typing_extensions import Annotated

from rhosocial.activerecord.base.fields import UseSqlType
from rhosocial.activerecord.backend.expression.types import (
    BigIntType,
    BlobType,
    BooleanType,
    DateType,
    DateTimeType,
    DecimalType,
    IntegerType,
    JsonType,
    TextType,
    TimeType,
    VarCharType,
)
from rhosocial.activerecord.model import ActiveRecord


class TypedUser(ActiveRecord):
    """User account with explicitly declared SQL column types."""

    __table_name__ = "typed_users"

    # 32-bit auto-increment primary key (portable).
    id: Annotated[int, UseSqlType(IntegerType())]
    # Variable-length strings.
    username: Annotated[str, UseSqlType(VarCharType(length=100))]
    email: Annotated[str, UseSqlType(VarCharType(length=255))]
    # Boolean flag.
    is_active: Annotated[bool, UseSqlType(BooleanType())]
    # Exact fixed-point money.
    balance: Annotated[Optional[float], UseSqlType(DecimalType(precision=10, scale=2))]
    # Calendar date (no time component).
    birthday: Annotated[Optional[str], UseSqlType(DateType())]
    # Date + time of creation.
    created_at: Annotated[str, UseSqlType(DateTimeType())]
    # Unbounded text.
    bio: Annotated[Optional[str], UseSqlType(TextType())]
    # Structured JSON document.
    metadata: Annotated[Optional[dict], UseSqlType(JsonType())]
    # 64-bit counter.
    big_counter: Annotated[Optional[int], UseSqlType(BigIntType())]
    # Raw binary payload.
    avatar: Annotated[Optional[bytes], UseSqlType(BlobType())]
    # Time-of-day.
    wake_up_time: Annotated[Optional[str], UseSqlType(TimeType())]
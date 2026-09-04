# src/rhosocial/activerecord/examples/ddl_default_types.py
"""Shared example: an ActiveRecord with NO explicit SQL column types.

This is the contrast to :mod:`.ddl_types`: fields carry plain Python types
and no ``UseSqlType`` annotation, so each backend derives the column type via
``dialect.suggest_column_type(python_type)``. The result differs per backend
— that is the point: with no explicit declaration, each backend picks its own
native/default representation::

    SQLite:     ``str`` → TEXT, ``bool`` → NUMERIC, ``dict`` → TEXT, ...
    MySQL:      ``str`` → VARCHAR(255), ``dict`` → JSON (5.7+), ...
    PostgreSQL: ``str`` → TEXT, ``dict`` → JSONB, ...

Use ``UseSqlType`` (see :mod:`.ddl_types`) when a column must be pinned to a
specific SQL type regardless of backend.
"""

import sys
from datetime import date, datetime

if sys.version_info >= (3, 9):
    from typing import Optional
else:  # pragma: no cover - Python 3.8
    from typing import Optional

from rhosocial.activerecord.model import ActiveRecord


class DefaultUser(ActiveRecord):
    """User account relying on per-backend type suggestion."""

    __table_name__ = "default_users"

    # 32-bit auto-increment primary key (portable).
    id: int
    # Variable-length strings — each backend picks its own default.
    username: str
    email: str
    # Boolean flag.
    is_active: bool
    # Approximate double-precision value.
    balance: float
    # Date + time of creation.
    created_at: datetime
    # Structured document — backend-specific default (e.g. JSONB on Postgres).
    metadata: dict
    # Raw binary payload.
    avatar: bytes
    # Calendar date (no time component).
    birthday: Optional[date] = None
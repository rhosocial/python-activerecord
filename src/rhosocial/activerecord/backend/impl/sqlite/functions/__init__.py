# src/rhosocial/activerecord/backend/impl/sqlite/functions/__init__.py
"""
SQLite-specific SQL function factories.

This module provides factory functions for SQLite-specific SQL functions
that may have different names or behavior compared to standard SQL functions.

Submodules:
- string: String manipulation functions (substr, instr, printf, etc.)
- datetime: Date and time functions (date, time, datetime, etc.)
- math: Mathematical functions (random, abs, sign, total)
- blob: BLOB manipulation functions (zeroblob, randomblob)
- system: System and type functions (typeof, quote, last_insert_rowid, changes)
- conditional: Conditional expressions (iif)
"""

from .string import (
    substr,
    instr,
    printf,
    unicode,
    hex,
    unhex,
    soundex,
    group_concat,
    trim_sqlite,
    ltrim,
    rtrim,
)

from .datetime import (
    date_func,
    time_func,
    datetime_func,
    julianday,
    strftime_func,
)

from .math import (
    random_func,
    abs_sql,
    sign,
    total,
)

from .blob import (
    zeroblob,
    randomblob,
)

from .system import (
    typeof,
    quote,
    last_insert_rowid,
    changes,
)

from .conditional import (
    iif,
)

__all__ = [
    # String functions
    "substr",
    "instr",
    "printf",
    "unicode",
    "hex",
    "unhex",
    "soundex",
    "group_concat",
    "trim_sqlite",
    "ltrim",
    "rtrim",
    # Date/Time functions
    "date_func",
    "time_func",
    "datetime_func",
    "julianday",
    "strftime_func",
    # Math functions
    "random_func",
    "abs_sql",
    "sign",
    "total",
    # Blob functions
    "zeroblob",
    "randomblob",
    # System functions
    "typeof",
    "quote",
    "last_insert_rowid",
    "changes",
    # Conditional functions
    "iif",
]

# src/rhosocial/activerecord/backend/impl/sqlite/functions/__init__.py
"""
SQLite-specific SQL function factories.

This module provides factory functions for SQLite-specific SQL functions
that may have different names or behavior compared to standard SQL functions.

Submodules:
- string: String manipulation functions (substr, instr, printf, etc.)
- datetime: Date and time functions (date, time, datetime, etc.)
- math: Mathematical functions (random, abs, sign, total)
- math_enhanced: Enhanced math functions (round, pow, sqrt, mod, etc.)
- blob: BLOB manipulation functions (zeroblob, randomblob)
- system: System and type functions (typeof, quote, last_insert_rowid, changes)
- conditional: Conditional expressions (iif)
- json: JSON functions (json, json_extract, json_object, etc.)
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

from .json import (
    json,
    json_array,
    json_object,
    json_extract,
    json_type,
    json_valid,
    json_quote,
    json_remove,
    json_set,
    json_insert,
    json_replace,
    json_patch,
    json_array_length,
    json_array_unpack,
    json_object_pack,
    json_object_retrieve,
    json_object_length,
    json_object_keys,
    json_tree,
    json_each,
)

from .math_enhanced import (
    round_sql,
    pow,
    power,
    sqrt,
    mod,
    ceil,
    floor,
    trunc,
    max_sql,
    min_sql,
    avg,
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
    # Math enhanced functions
    "round_sql",
    "pow",
    "power",
    "sqrt",
    "mod",
    "ceil",
    "floor",
    "trunc",
    "max_sql",
    "min_sql",
    "avg",
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
    # JSON functions
    "json",
    "json_array",
    "json_object",
    "json_extract",
    "json_type",
    "json_valid",
    "json_quote",
    "json_remove",
    "json_set",
    "json_insert",
    "json_replace",
    "json_patch",
    "json_array_length",
    "json_array_unpack",
    "json_object_pack",
    "json_object_retrieve",
    "json_object_length",
    "json_object_keys",
    "json_tree",
    "json_each",
]

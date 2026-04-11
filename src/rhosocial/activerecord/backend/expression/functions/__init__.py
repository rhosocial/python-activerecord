# src/rhosocial/activerecord/backend/expression/functions/__init__.py
"""
Standalone factory functions for creating SQL expression objects.

Usage Rules:
- For COUNT(*), pass "*" as a string: count(dialect, "*")
- For column references (e.g., COUNT(column), SUM(column)), pass Column objects:
  count(dialect, Column(dialect, "column_name"))
- For literal values (e.g., COUNT(?), SUM(?)), pass literal values as strings:
  count(dialect, "literal_value")
- For scalar functions (e.g., lower, upper), string arguments are treated as literal values by default
- For functions that operate on columns, wrap column names in Column objects
"""

# Aggregate function factories
from .aggregate import count, sum_, avg, min_, max_

# String function factories
from .string import (
    concat,
    coalesce,
    length,
    substring,
    trim,
    replace,
    upper,
    lower,
    initcap,
    left,
    right,
    lpad,
    rpad,
    reverse,
    strpos,
    # SQL standard string functions
    concat_op,
    chr_,
    ascii,
    octet_length,
    bit_length,
    position,
    overlay,
    translate,
    repeat,
    space,
)

# Math function factories
from .math import (
    abs_,
    round_,
    ceil,
    floor,
    sqrt,
    power,
    exp,
    log,
    sin,
    cos,
    tan,
    # SQL standard math functions
    mod,
    sign,
    truncate,
)

# Date/Time function factories
from .datetime import (
    now,
    current_date,
    current_time,
    year,
    month,
    day,
    hour,
    minute,
    second,
    date_part,
    date_trunc,
    # SQL standard datetime functions
    current_timestamp,
    localtimestamp,
    extract,
)

# Conditional function factories
from .conditional import case, nullif, greatest, least

# Window function factories
from .window import row_number, rank, dense_rank, lag, lead, first_value, last_value, nth_value

# JSON function factories
from .json import json_extract, json_extract_text, json_build_object, json_array_elements, json_objectagg, json_arrayagg

# Array function factories
from .array import array_agg, unnest, array_length

# Type conversion function factories
from .type_conversion import cast, to_char, to_number, to_date

# Grouping function factories
from .grouping import grouping_sets, rollup, cube

# System information function factories
from .system import current_user, session_user, system_user

__all__ = [
    # Aggregate
    "count",
    "sum_",
    "avg",
    "min_",
    "max_",
    # String
    "concat",
    "coalesce",
    "length",
    "substring",
    "trim",
    "replace",
    "upper",
    "lower",
    "initcap",
    "left",
    "right",
    "lpad",
    "rpad",
    "reverse",
    "strpos",
    "concat_op",
    "chr_",
    "ascii",
    "octet_length",
    "bit_length",
    "position",
    "overlay",
    "translate",
    "repeat",
    "space",
    # Math
    "abs_",
    "round_",
    "ceil",
    "floor",
    "sqrt",
    "power",
    "exp",
    "log",
    "sin",
    "cos",
    "tan",
    "mod",
    "sign",
    "truncate",
    # Date/Time
    "now",
    "current_date",
    "current_time",
    "year",
    "month",
    "day",
    "hour",
    "minute",
    "second",
    "date_part",
    "date_trunc",
    "current_timestamp",
    "localtimestamp",
    "extract",
    # Conditional
    "case",
    "nullif",
    "greatest",
    "least",
    # Window
    "row_number",
    "rank",
    "dense_rank",
    "lag",
    "lead",
    "first_value",
    "last_value",
    "nth_value",
    # JSON
    "json_extract",
    "json_extract_text",
    "json_build_object",
    "json_array_elements",
    "json_objectagg",
    "json_arrayagg",
    # Array
    "array_agg",
    "unnest",
    "array_length",
    # Type conversion
    "cast",
    "to_char",
    "to_number",
    "to_date",
    # Grouping
    "grouping_sets",
    "rollup",
    "cube",
    # System
    "current_user",
    "session_user",
    "system_user",
]

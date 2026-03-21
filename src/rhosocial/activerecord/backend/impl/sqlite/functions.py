# src/rhosocial/activerecord/backend/impl/sqlite/functions.py
"""
SQLite-specific function factories.

This module provides factory functions for SQLite-specific SQL functions
that may have different names or behavior compared to standard SQL functions.

SQLite Function Categories:
1. String Functions: substr, instr, printf, unicode, hex, group_concat
2. Date/Time Functions: date, time, datetime, julianday, strftime
3. Math Functions: random, sign, mod (via % operator)
4. Type Functions: typeof, quote
5. Aggregate Functions: group_concat, total
6. Other Functions: changes, last_insert_rowid, soundex
"""

from typing import Union, Optional, TYPE_CHECKING

from rhosocial.activerecord.backend.expression import bases, core

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


def substr(
    dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], start: int, length: Optional[int] = None
) -> "core.FunctionCall":
    """
    Creates a SUBSTR function call (SQLite's substring function).

    SQLite's SUBSTR uses 1-based indexing.

    Usage:
        - substr(dialect, Column("name"), 1, 5) -> SUBSTR("name", 1, 5)
        - substr(dialect, "text", 2) -> SUBSTR('text', 2)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to extract from
        start: Starting position (1-based)
        length: Optional length of substring

    Returns:
        A FunctionCall instance representing the SUBSTR function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    start_expr = core.Literal(dialect, start)
    if length is not None:
        length_expr = core.Literal(dialect, length)
        return core.FunctionCall(dialect, "SUBSTR", target_expr, start_expr, length_expr)
    return core.FunctionCall(dialect, "SUBSTR", target_expr, start_expr)


def instr(
    dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], substring: Union[str, "bases.BaseExpression"]
) -> "core.FunctionCall":
    """
    Creates an INSTR function call (SQLite's string position function).

    Returns the position of the first occurrence of substring (1-based),
    or 0 if not found.

    Usage:
        - instr(dialect, Column("name"), "abc") -> INSTR("name", 'abc')

    Args:
        dialect: The SQL dialect instance
        expr: The expression to search in
        substring: The substring to find

    Returns:
        A FunctionCall instance representing the INSTR function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    substr_expr = substring if isinstance(substring, bases.BaseExpression) else core.Literal(dialect, substring)
    return core.FunctionCall(dialect, "INSTR", target_expr, substr_expr)


def printf(dialect: "SQLDialectBase", format_str: str, *args) -> "core.FunctionCall":
    """
    Creates a PRINTF function call for string formatting.

    Usage:
        - printf(dialect, "Hello %s!", name) -> PRINTF('Hello %s!', "name")

    Args:
        dialect: The SQL dialect instance
        format_str: Format string with SQLite printf format specifiers
        *args: Values to format

    Returns:
        A FunctionCall instance representing the PRINTF function
    """
    format_expr = core.Literal(dialect, format_str)
    arg_exprs = [arg if isinstance(arg, bases.BaseExpression) else core.Literal(dialect, arg) for arg in args]
    return core.FunctionCall(dialect, "PRINTF", format_expr, *arg_exprs)


def unicode(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """
    Creates a UNICODE function call.

    Returns the Unicode code point of the first character.

    Usage:
        - unicode(dialect, Column("char")) -> UNICODE("char")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to get Unicode value from

    Returns:
        A FunctionCall instance representing the UNICODE function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    return core.FunctionCall(dialect, "UNICODE", target_expr)


def hex(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """
    Creates a HEX function call.

    Returns the hexadecimal representation of the expression.

    Usage:
        - hex(dialect, Column("data")) -> HEX("data")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to convert to hex

    Returns:
        A FunctionCall instance representing the HEX function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    return core.FunctionCall(dialect, "HEX", target_expr)


def unhex(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """
    Creates an UNHEX function call (SQLite 3.45.0+).

    Converts hexadecimal string back to binary.

    Usage:
        - unhex(dialect, Column("hex_data")) -> UNHEX("hex_data")

    Args:
        dialect: The SQL dialect instance
        expr: The hexadecimal expression to convert

    Returns:
        A FunctionCall instance representing the UNHEX function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    return core.FunctionCall(dialect, "UNHEX", target_expr)


def zeroblob(dialect: "SQLDialectBase", length: int) -> "core.FunctionCall":
    """
    Creates a ZEROBLOB function call.

    Returns a BLOB of the specified length filled with zeros.

    Usage:
        - zeroblob(dialect, 100) -> ZEROBLOB(100)

    Args:
        dialect: The SQL dialect instance
        length: Length of the BLOB in bytes

    Returns:
        A FunctionCall instance representing the ZEROBLOB function
    """
    return core.FunctionCall(dialect, "ZEROBLOB", core.Literal(dialect, length))


def randomblob(dialect: "SQLDialectBase", length: int) -> "core.FunctionCall":
    """
    Creates a RANDOMBLOB function call.

    Returns a BLOB of the specified length filled with random bytes.

    Usage:
        - randomblob(dialect, 16) -> RANDOMBLOB(16)

    Args:
        dialect: The SQL dialect instance
        length: Length of the BLOB in bytes

    Returns:
        A FunctionCall instance representing the RANDOMBLOB function
    """
    return core.FunctionCall(dialect, "RANDOMBLOB", core.Literal(dialect, length))


def group_concat(
    dialect: "SQLDialectBase",
    expr: Union[str, "bases.BaseExpression"],
    separator: Optional[str] = None,
    is_distinct: bool = False,
) -> "core.FunctionCall":
    """
    Creates a GROUP_CONCAT aggregate function call.

    SQLite's string aggregation function (similar to STRING_AGG in other DBs).

    Usage:
        - group_concat(dialect, Column("name")) -> GROUP_CONCAT("name")
        - group_concat(dialect, Column("name"), ", ") -> GROUP_CONCAT("name", ', ')
        - group_concat(dialect, Column("name"), is_distinct=True) -> GROUP_CONCAT(DISTINCT "name")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to concatenate
        separator: Optional separator string (defaults to ',')
        is_distinct: Whether to use DISTINCT

    Returns:
        A FunctionCall instance representing the GROUP_CONCAT function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Column(dialect, expr)
    args = [target_expr]
    if separator is not None:
        args.append(core.Literal(dialect, separator))
    return core.FunctionCall(dialect, "GROUP_CONCAT", *args, is_distinct=is_distinct)


def total(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """
    Creates a TOTAL aggregate function call.

    SQLite-specific function that returns the sum of all non-NULL values,
    or 0.0 if there are no non-NULL values (unlike SUM which returns NULL).

    Usage:
        - total(dialect, Column("amount")) -> TOTAL("amount")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to total

    Returns:
        A FunctionCall instance representing the TOTAL function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Column(dialect, expr)
    return core.FunctionCall(dialect, "TOTAL", target_expr)


def date_func(
    dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], *modifiers: str
) -> "core.FunctionCall":
    """
    Creates a DATE function call.

    SQLite's date function with optional modifiers.

    Usage:
        - date_func(dialect, "now") -> DATE('now')
        - date_func(dialect, "now", "+1 day") -> DATE('now', '+1 day')

    Args:
        dialect: The SQL dialect instance
        expr: The date expression or 'now'
        *modifiers: Optional date modifiers

    Returns:
        A FunctionCall instance representing the DATE function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    modifier_exprs = [core.Literal(dialect, m) for m in modifiers]
    return core.FunctionCall(dialect, "DATE", target_expr, *modifier_exprs)


def time_func(
    dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], *modifiers: str
) -> "core.FunctionCall":
    """
    Creates a TIME function call.

    SQLite's time function with optional modifiers.

    Usage:
        - time_func(dialect, "now") -> TIME('now')
        - time_func(dialect, "now", "localtime") -> TIME('now', 'localtime')

    Args:
        dialect: The SQL dialect instance
        expr: The time expression or 'now'
        *modifiers: Optional time modifiers

    Returns:
        A FunctionCall instance representing the TIME function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    modifier_exprs = [core.Literal(dialect, m) for m in modifiers]
    return core.FunctionCall(dialect, "TIME", target_expr, *modifier_exprs)


def datetime_func(
    dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], *modifiers: str
) -> "core.FunctionCall":
    """
    Creates a DATETIME function call.

    SQLite's datetime function with optional modifiers.

    Usage:
        - datetime_func(dialect, "now") -> DATETIME('now')
        - datetime_func(dialect, "now", "localtime") -> DATETIME('now', 'localtime')

    Args:
        dialect: The SQL dialect instance
        expr: The datetime expression or 'now'
        *modifiers: Optional datetime modifiers

    Returns:
        A FunctionCall instance representing the DATETIME function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    modifier_exprs = [core.Literal(dialect, m) for m in modifiers]
    return core.FunctionCall(dialect, "DATETIME", target_expr, *modifier_exprs)


def julianday(
    dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], *modifiers: str
) -> "core.FunctionCall":
    """
    Creates a JULIANDAY function call.

    Returns the Julian day number for a date/time expression.

    Usage:
        - julianday(dialect, "now") -> JULIANDAY('now')
        - julianday(dialect, Column("created_at")) -> JULIANDAY("created_at")

    Args:
        dialect: The SQL dialect instance
        expr: The date expression
        *modifiers: Optional date modifiers

    Returns:
        A FunctionCall instance representing the JULIANDAY function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    modifier_exprs = [core.Literal(dialect, m) for m in modifiers]
    return core.FunctionCall(dialect, "JULIANDAY", target_expr, *modifier_exprs)


def strftime_func(
    dialect: "SQLDialectBase", format_str: str, expr: Union[str, "bases.BaseExpression"], *modifiers: str
) -> "core.FunctionCall":
    """
    Creates a STRFTIME function call.

    SQLite's date/time formatting function.

    Usage:
        - strftime_func(dialect, "%Y-%m-%d", "now") -> STRFTIME('%Y-%m-%d', 'now')
        - strftime_func(dialect, "%H:%M", Column("timestamp")) -> STRFTIME('%H:%M', "timestamp")

    Args:
        dialect: The SQL dialect instance
        format_str: Format string (SQLite strftime format)
        expr: The date/time expression
        *modifiers: Optional date modifiers

    Returns:
        A FunctionCall instance representing the STRFTIME function
    """
    format_expr = core.Literal(dialect, format_str)
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    modifier_exprs = [core.Literal(dialect, m) for m in modifiers]
    return core.FunctionCall(dialect, "STRFTIME", format_expr, target_expr, *modifier_exprs)


def typeof(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """
    Creates a TYPEOF function call.

    Returns the storage type of the expression.

    Usage:
        - typeof(dialect, Column("data")) -> TYPEOF("data")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to check type of

    Returns:
        A FunctionCall instance representing the TYPEOF function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    return core.FunctionCall(dialect, "TYPEOF", target_expr)


def quote(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """
    Creates a QUOTE function call.

    Returns the SQL literal representation of the expression.

    Usage:
        - quote(dialect, Column("value")) -> QUOTE("value")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to quote

    Returns:
        A FunctionCall instance representing the QUOTE function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    return core.FunctionCall(dialect, "QUOTE", target_expr)


def random_func(dialect: "SQLDialectBase") -> "core.FunctionCall":
    """
    Creates a RANDOM function call.

    Returns a random integer between -9223372036854775808 and +9223372036854775807.

    Usage:
        - random_func(dialect) -> RANDOM()

    Args:
        dialect: The SQL dialect instance

    Returns:
        A FunctionCall instance representing the RANDOM function
    """
    return core.FunctionCall(dialect, "RANDOM")


def abs_sql(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """
    Creates an ABS function call.

    Note: This is named abs_sql to avoid conflict with Python's abs.
    Common functions module uses abs_ for the same purpose.

    Usage:
        - abs_sql(dialect, Column("value")) -> ABS("value")

    Args:
        dialect: The SQL dialect instance
        expr: The numeric expression

    Returns:
        A FunctionCall instance representing the ABS function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    return core.FunctionCall(dialect, "ABS", target_expr)


def sign(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """
    Creates a SIGN function call (SQLite 3.44.0+).

    Returns -1, 0, or 1 depending on whether the argument is negative, zero, or positive.

    Usage:
        - sign(dialect, Column("value")) -> SIGN("value")

    Args:
        dialect: The SQL dialect instance
        expr: The numeric expression

    Returns:
        A FunctionCall instance representing the SIGN function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    return core.FunctionCall(dialect, "SIGN", target_expr)


def soundex(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """
    Creates a SOUNDEX function call.

    Returns the Soundex encoding of a string (requires Soundex extension).

    Usage:
        - soundex(dialect, Column("name")) -> SOUNDEX("name")

    Args:
        dialect: The SQL dialect instance
        expr: The string expression

    Returns:
        A FunctionCall instance representing the SOUNDEX function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    return core.FunctionCall(dialect, "SOUNDEX", target_expr)


def last_insert_rowid(dialect: "SQLDialectBase") -> "core.FunctionCall":
    """
    Creates a LAST_INSERT_ROWID function call.

    Returns the ROWID of the most recent successful INSERT.

    Usage:
        - last_insert_rowid(dialect) -> LAST_INSERT_ROWID()

    Args:
        dialect: The SQL dialect instance

    Returns:
        A FunctionCall instance representing the LAST_INSERT_ROWID function
    """
    return core.FunctionCall(dialect, "LAST_INSERT_ROWID")


def changes(dialect: "SQLDialectBase") -> "core.FunctionCall":
    """
    Creates a CHANGES function call.

    Returns the number of rows modified by the most recent INSERT, UPDATE, or DELETE.

    Usage:
        - changes(dialect) -> CHANGES()

    Args:
        dialect: The SQL dialect instance

    Returns:
        A FunctionCall instance representing the CHANGES function
    """
    return core.FunctionCall(dialect, "CHANGES")


def trim_sqlite(
    dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], characters: Optional[str] = None
) -> "core.FunctionCall":
    """
    Creates a TRIM function call with SQLite-specific behavior.

    SQLite's TRIM can remove specific characters from both ends.

    Usage:
        - trim_sqlite(dialect, Column("name")) -> TRIM("name")
        - trim_sqlite(dialect, Column("name"), "xyz") -> TRIM("name", 'xyz')

    Args:
        dialect: The SQL dialect instance
        expr: The expression to trim
        characters: Optional characters to remove (defaults to whitespace)

    Returns:
        A FunctionCall instance representing the TRIM function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    if characters is not None:
        char_expr = core.Literal(dialect, characters)
        return core.FunctionCall(dialect, "TRIM", target_expr, char_expr)
    return core.FunctionCall(dialect, "TRIM", target_expr)


def ltrim(
    dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], characters: Optional[str] = None
) -> "core.FunctionCall":
    """
    Creates an LTRIM function call.

    Removes characters from the left side of a string.

    Usage:
        - ltrim(dialect, Column("name")) -> LTRIM("name")
        - ltrim(dialect, Column("name"), "xyz") -> LTRIM("name", 'xyz')

    Args:
        dialect: The SQL dialect instance
        expr: The expression to trim
        characters: Optional characters to remove

    Returns:
        A FunctionCall instance representing the LTRIM function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    if characters is not None:
        char_expr = core.Literal(dialect, characters)
        return core.FunctionCall(dialect, "LTRIM", target_expr, char_expr)
    return core.FunctionCall(dialect, "LTRIM", target_expr)


def rtrim(
    dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], characters: Optional[str] = None
) -> "core.FunctionCall":
    """
    Creates an RTRIM function call.

    Removes characters from the right side of a string.

    Usage:
        - rtrim(dialect, Column("name")) -> RTRIM("name")
        - rtrim(dialect, Column("name"), "xyz") -> RTRIM("name", 'xyz')

    Args:
        dialect: The SQL dialect instance
        expr: The expression to trim
        characters: Optional characters to remove

    Returns:
        A FunctionCall instance representing the RTRIM function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    if characters is not None:
        char_expr = core.Literal(dialect, characters)
        return core.FunctionCall(dialect, "RTRIM", target_expr, char_expr)
    return core.FunctionCall(dialect, "RTRIM", target_expr)


def iif(
    dialect: "SQLDialectBase",
    condition: "bases.BaseExpression",
    true_value: Union[str, "bases.BaseExpression"],
    false_value: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """
    Creates an IIF function call (SQLite's inline IF).

    SQLite-specific shorthand for CASE WHEN ... THEN ... ELSE ... END.

    Usage:
        - iif(dialect, Column("active") > 0, "yes", "no") -> IIF("active" > 0, 'yes', 'no')

    Args:
        dialect: The SQL dialect instance
        condition: The condition expression
        true_value: Value if condition is true
        false_value: Value if condition is false

    Returns:
        A FunctionCall instance representing the IIF function
    """
    true_expr = true_value if isinstance(true_value, bases.BaseExpression) else core.Literal(dialect, true_value)
    false_expr = false_value if isinstance(false_value, bases.BaseExpression) else core.Literal(dialect, false_value)
    return core.FunctionCall(dialect, "IIF", condition, true_expr, false_expr)


__all__ = [
    # String functions
    "substr",
    "instr",
    "printf",
    "unicode",
    "hex",
    "unhex",
    "zeroblob",
    "randomblob",
    "soundex",
    # Aggregate functions
    "group_concat",
    "total",
    # Date/Time functions
    "date_func",
    "time_func",
    "datetime_func",
    "julianday",
    "strftime_func",
    # Type functions
    "typeof",
    "quote",
    # Math functions
    "random_func",
    "abs_sql",
    "sign",
    # System functions
    "last_insert_rowid",
    "changes",
    # Trim functions
    "trim_sqlite",
    "ltrim",
    "rtrim",
    # Conditional functions
    "iif",
]

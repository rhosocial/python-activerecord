# src/rhosocial/activerecord/backend/impl/sqlite/functions/string.py
"""
SQLite string function factories.

Functions: substr, instr, printf, unicode, hex, unhex, soundex,
           trim_sqlite, ltrim, rtrim
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


__all__ = [
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
]
